"""A3 servis orkestrasyonu: tur gözlemi → damıtma → mühürleme → devir seçimi.

Sahiplik sınırı (§27): A3 yalnız KENDİ üç tablosunu yazar
(`agent_session_episode`, `agent_session_episode_turn`, `agent_session_episode_item`).
A1/A2 tabloları yalnız OKUNUR. Kanonik operasyonel durum (Entity, Event, Link,
Todo, Project, H7 yürütme, H2, Vault) bu modülden HİÇBİR koşulda değişmez.

Fail-open sözleşmesi: damıtma ve mühürleme hataları Hermes konuşmasını veya A1
yaşam döngüsünü ASLA düşürmez. Her hata sınırlı bir gerekçe koduna indirgenir.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, not_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent_continuity.models import AgentSessionSource
from app.modules.agent_episode.distill import (
    MAX_DELIVERED_REFS,
    compute_turn_digest,
    delivered_ref_from_source,
    distill_turn,
)
from app.modules.agent_episode.models import (
    AgentSessionEpisode,
    AgentSessionEpisodeItem,
    AgentSessionEpisodeTurn,
)
from app.modules.agent_episode.renderer import render_handoff
from app.modules.agent_episode.schemas import (
    DRAFT_STALE_HOURS,
    EPISODE_RETENTION_DAYS,
    MAX_EPISODE_TURNS,
    MAX_OPEN_THREADS,
    MAX_SEALED_EPISODES,
    MAX_SUPPORT_REFS_PER_ITEM,
    EpisodeFinalizeIn,
    EpisodeFinalizeOut,
    EpisodeStatusOut,
    EpisodeSupportRef,
    EpisodeTurnIn,
    EpisodeTurnOut,
    SessionHandoffItem,
    SessionHandoffV1,
    bound_handoff_items,
    bounded_indices,
    dedupe_indices,
)
from app.modules.agent_lifecycle.models import AgentSession
from app.modules.agent_lifecycle.service import session_key, turn_key

LOGGER = logging.getLogger("forkos.agent_episode")

#: Devir okunurken en fazla bu kadar destek referansı canlı kanonik veriye karşı
#: yeniden doğrulanır. Sınır, ilk turun sıcak yolunu korumak içindir (§22).
MAX_STALE_CHECKS = 6

#: Mühürlenmiş devirde saklanabilecek en fazla tür-içi ifade (şema tavanıyla aynı).
_SEALED_STATUSES = ("sealed", "sealed_degraded")


class EpisodeSessionNotFound(Exception):
    """A1 oturumu bilinmiyor: A3 kendi başına oturum yaratmaz."""


def _now() -> datetime:
    return datetime.now(UTC)


def _episode_expiry(anchor: datetime) -> datetime:
    return anchor + timedelta(days=EPISODE_RETENTION_DAYS)


async def _session_row(session: AsyncSession, harness: str, raw_session_id: str) -> AgentSession | None:
    key = session_key(harness, raw_session_id)
    return (
        await session.execute(select(AgentSession).where(AgentSession.session_key == key))
    ).scalar_one_or_none()


async def _get_or_create_episode(session: AsyncSession, session_row: AgentSession) -> AgentSessionEpisode:
    """Oturumun taslak devrini döner, yoksa oluşturur.

    Eşzamanlı ilk dokunuş (ör. `/turn` ile `/episode/turn` aynı anda) iki
    çağrının da INSERT denemesine yol açabilir. Kaybeden taraf savepoint'ini
    geri alıp kazananı OKUR: defter yazımı kaybolmaz, dış işlem bozulmaz.
    """
    stmt = (
        select(AgentSessionEpisode)
        .where(AgentSessionEpisode.session_id == session_row.id)
        .with_for_update()
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is not None:
        return row

    started = session_row.start_seen_at or session_row.first_seen_at
    row = AgentSessionEpisode(
        session_id=session_row.id,
        schema_version=1,
        status="draft",
        scope_project=None,
        started_at=started,
        sealed_at=None,
        turn_count=0,
        item_count=0,
        degraded_reasons=[],
        expires_at=_episode_expiry(started),
    )
    try:
        async with session.begin_nested():
            session.add(row)
            await session.flush()
    except IntegrityError:
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:  # pragma: no cover - yarış dışı bir ihlal
            raise
    return row


@dataclass(frozen=True)
class ScopeResolution:
    """Kapsam çözümleme sonucu (§19 / A3.1)."""

    scope_project: str | None
    ambiguous: bool

    @property
    def is_exact(self) -> bool:
        return self.scope_project is not None and not self.ambiguous

    @property
    def is_unscoped(self) -> bool:
        return self.scope_project is None and not self.ambiguous


def resolve_scope(
    refs: list[dict[str, Any]],
    explicit_scope: str | None = None,
) -> ScopeResolution:
    """Oturum/tur kapsamını teslim edilen kaynaklardan ve isteğe bağlı açık kapsamdan çözer.

    Kurallar (A3.1):
    - Teslim edilen kaynaklarda birden fazla farklı proje varsa: AMBIGUOUS (scope_project=None, ambiguous=True)
    - Teslim edilen kaynaklarda tek proje varsa (örn. A):
        - explicit_scope yoksa veya A ise: EXACT (scope_project=A, ambiguous=False)
        - explicit_scope farklı bir proje ise: CONFLICT -> fail-closed (scope_project=None, ambiguous=True)
    - Teslim edilen kaynaklarda hiç proje yoksa:
        - explicit_scope varsa: EXACT (scope_project=explicit_scope, ambiguous=False)
        - explicit_scope yoksa: UNSCOPED (scope_project=None, ambiguous=False)
    """
    scopes = {
        ref["scope_project"]
        for ref in refs
        if isinstance(ref.get("scope_project"), str) and ref.get("scope_project")
    }
    if len(scopes) > 1:
        return ScopeResolution(scope_project=None, ambiguous=True)

    if len(scopes) == 1:
        delivered_scope = next(iter(scopes))
        if explicit_scope and explicit_scope != delivered_scope:
            return ScopeResolution(scope_project=None, ambiguous=True)
        return ScopeResolution(scope_project=delivered_scope, ambiguous=False)

    # len(scopes) == 0
    if explicit_scope:
        return ScopeResolution(scope_project=explicit_scope, ambiguous=False)
    return ScopeResolution(scope_project=None, ambiguous=False)


def derive_scope(refs: list[dict[str, Any]], explicit_scope: str | None = None) -> str | None:
    """Oturum kapsamını TESLİM EDİLEN kaynaklardan türetir (geriye uyumluluk)."""
    res = resolve_scope(refs, explicit_scope=explicit_scope)
    return res.scope_project if not res.ambiguous else None


async def _episode_turn(
    session: AsyncSession, episode: AgentSessionEpisode, key: str
) -> AgentSessionEpisodeTurn | None:
    return (
        await session.execute(
            select(AgentSessionEpisodeTurn).where(
                AgentSessionEpisodeTurn.episode_id == episode.id,
                AgentSessionEpisodeTurn.turn_key == key,
            )
        )
    ).scalar_one_or_none()


async def _all_delivered_refs(
    session: AsyncSession, episode_id: int
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(AgentSessionEpisodeTurn.delivered_refs).where(
                AgentSessionEpisodeTurn.episode_id == episode_id
            )
        )
    ).scalars().all()
    out: list[dict[str, Any]] = []
    for group in rows:
        out.extend(group or [])
    return out


async def record_delivered(
    session: AsyncSession,
    *,
    session_row: AgentSession,
    raw_turn_id: str,
    turn_db_id: int | None,
    sources: list[Any],
    delivered_at: datetime | None = None,
) -> None:
    """A2'nin BU turda teslim ettiği kaynak kümesini A3 defterine yazar (§9).

    A2'nin `agent_session_source` tablosu yeniden teslimatta `turn_id`'yi ezdiği
    ve devamlılık yolunda hiç yazmadığı için turn bazlı kesin teslim oradan
    çözülemez. Defter A3'ün kendi tablosudur ve yalnız kanonik metadata taşır.

    Mühürlenmiş bir devir BU fonksiyonla değiştirilmez: kapanmış kayıt geri
    açılmaz.
    """
    now = delivered_at or _now()
    episode = await _get_or_create_episode(session, session_row)
    if episode.status != "draft":
        return

    key = turn_key(session_row.session_key, raw_turn_id)
    refs = [ref for ref in (delivered_ref_from_source(source) for source in sources) if ref]
    refs = refs[:MAX_DELIVERED_REFS]

    row = await _episode_turn(session, episode, key)
    if row is None:
        row = AgentSessionEpisodeTurn(
            episode_id=episode.id,
            turn_id=turn_db_id,
            turn_key=key,
            status="pending",
            turn_digest=None,
            item_count=0,
            delivered_refs=refs,
            degraded_reasons=[],
            delivered_at=now,
            observed_at=None,
        )
        session.add(row)
    else:
        row.delivered_refs = refs
        if row.turn_id is None:
            row.turn_id = turn_db_id

    await _prune_turns(session, episode)
    await session.commit()


async def _prune_turns(session: AsyncSession, episode: AgentSessionEpisode) -> None:
    """Eski tur defterlerini fırsatçı olarak budar; mühürlü kayda dokunmaz."""
    if episode.status != "draft":
        return
    old_ids = (
        await session.scalars(
            select(AgentSessionEpisodeTurn.id)
            .where(AgentSessionEpisodeTurn.episode_id == episode.id)
            .order_by(AgentSessionEpisodeTurn.delivered_at.desc(), AgentSessionEpisodeTurn.id.desc())
            .offset(MAX_EPISODE_TURNS)
        )
    ).all()
    if old_ids:
        await session.execute(
            delete(AgentSessionEpisodeTurn).where(AgentSessionEpisodeTurn.id.in_(old_ids))
        )


async def ingest_turn(session: AsyncSession, body: EpisodeTurnIn) -> EpisodeTurnOut:
    """`post_llm_call` gözlemini işler; yalnız TÜRETİLMİŞ ifadeleri kalıcılaştırır.

    Ham `user_message`/`assistant_response` bu fonksiyondan çıkarken yalnız
    digest ve türetilmiş ifadeler kalır (§5).
    """
    started = datetime.now(UTC)
    session_row = await _session_row(session, body.harness, body.session_id)
    if session_row is None:
        raise EpisodeSessionNotFound(body.session_id)

    episode = await _get_or_create_episode(session, session_row)
    if episode.status != "draft":
        await session.rollback()
        return EpisodeTurnOut(
            accepted=False,
            duplicate=True,
            derived_item_count=0,
            degraded_reasons=["EPISODE_SEALED"],
            latency_ms=0.0,
        )

    key = turn_key(session_row.session_key, body.turn_id)
    row = await _episode_turn(session, episode, key)

    if row is not None and row.observed_at is not None:
        # Aynı (oturum, tur) ikinci kez geldi: güvenli no-op, yeni ifade üretilmez.
        await session.rollback()
        return EpisodeTurnOut(
            accepted=True, duplicate=True, derived_item_count=0, degraded_reasons=[], latency_ms=0.0
        )

    if row is None:
        row = AgentSessionEpisodeTurn(
            episode_id=episode.id,
            turn_id=None,
            turn_key=key,
            status="pending",
            turn_digest=None,
            item_count=0,
            delivered_refs=[],
            degraded_reasons=["SOURCE_BINDING_UNAVAILABLE"],
            delivered_at=started,
            observed_at=None,
        )
        session.add(row)
        await session.flush()

    delivered_refs = list(row.delivered_refs or [])
    all_refs = await _all_delivered_refs(session, episode.id)
    scope_res = resolve_scope(all_refs)
    episode_scope = scope_res.scope_project

    outcome = await distill_turn(
        user_text=body.user_message,
        assistant_text=body.assistant_response,
        delivered_refs=delivered_refs,
        scope_project=episode_scope,
    )

    digest = compute_turn_digest(
        session_key=session_row.session_key,
        turn_key=key,
        user_text=body.user_message or "",
        assistant_text=body.assistant_response or "",
    )

    degraded = list(row.degraded_reasons or [])
    # Kırpılmış tur sessizce yutulmaz: sınırlı kodla görünür kalır.
    if body.truncated and "EPISODE_INPUT_TRUNCATED" not in degraded:
        degraded.append("EPISODE_INPUT_TRUNCATED")
    if scope_res.ambiguous and "SCOPE_AMBIGUOUS" not in degraded:
        degraded.append("SCOPE_AMBIGUOUS")
    for reason in outcome.degraded_reasons:
        if reason not in degraded:
            degraded.append(reason)

    base_ordinal = int(
        (
            await session.execute(
                select(func.coalesce(func.max(AgentSessionEpisodeItem.ordinal), -1)).where(
                    AgentSessionEpisodeItem.episode_id == episode.id
                )
            )
        ).scalar_one()
    ) + 1

    for index, item in enumerate(outcome.items):
        session.add(
            AgentSessionEpisodeItem(
                episode_id=episode.id,
                episode_turn_id=row.id,
                ordinal=base_ordinal + index,
                kind=item.kind,
                text=item.text,
                evidence_class=item.evidence_class,
                support_refs=item.support_refs,
            )
        )

    row.turn_digest = digest
    row.item_count = len(outcome.items)
    row.observed_at = started
    row.degraded_reasons = degraded
    row.status = "extracted" if outcome.items else "degraded"

    episode.turn_count = int(
        (
            await session.execute(
                select(func.count()).select_from(AgentSessionEpisodeTurn).where(
                    AgentSessionEpisodeTurn.episode_id == episode.id,
                    AgentSessionEpisodeTurn.observed_at.is_not(None),
                )
            )
        ).scalar_one()
    )
    episode.scope_project = episode_scope
    await session.commit()

    return EpisodeTurnOut(
        accepted=True,
        duplicate=False,
        derived_item_count=len(outcome.items),
        degraded_reasons=degraded,
        latency_ms=outcome.latency_ms,
    )


async def _collect_session_observations(
    session: AsyncSession,
    *,
    episode: AgentSessionEpisode,
    sealed_at: datetime,
) -> tuple[list[tuple[str, str, list[dict[str, Any]]]], list[str]]:
    """Oturum penceresinde kanonik olarak GERÇEKLEŞMİŞ gözlemleri toplar (§10).

    Bu gözlemler `observed_during_session` sınıfındadır: oturum aralığında
    gerçekleştikleri kanoniktir, ama "bu Hermes oturumu yaptı" İDDİA EDİLMEZ —
    arka plan worker'ı veya başka bir kullanıcı eylemi olabilir. Nedensellik
    kurulmaz.

    Yalnız oturumda GERÇEKTEN teslim edilmiş kaynaklara dayanan gözlemler
    alınır; bu deterministik filtre olmadan gözlem uydurma olurdu.
    """
    delivered = {
        ref["source_id"]: ref
        for ref in await _all_delivered_refs(session, episode.id)
        if isinstance(ref.get("source_id"), str)
    }
    if not delivered:
        return [], []

    try:
        from app.integrations.review_intelligence.continuity import build_continuity
        from app.integrations.review_intelligence.models import Collector

        collector = Collector()
        bundle, _ = await build_continuity(
            session,
            collector,
            since=episode.started_at,
            until=sealed_at,
            focus_entity_id=None,
            include_knowledge=False,
            now=sealed_at,
        )
    except Exception as exc:  # noqa: BLE001 - H5 yoksa devir yine mühürlenir
        LOGGER.warning("A3 H5 session-period grounding degraded: %s", type(exc).__name__)
        return [], ["H5_UNAVAILABLE"]

    observations: list[tuple[str, str, list[dict[str, Any]]]] = []

    def add(kind: str, text: str, refs: list[str]) -> None:
        kept = [ref for ref in refs if ref in delivered]
        if not kept:
            return
        observations.append(
            (
                kind,
                text,
                [
                    {
                        "source_id": ref[:128],
                        # Tür ve sürüm DEFTERDEN gelir: ref ön ekini kırpmak
                        # `entity:`/`vault:` gibi ham aile adları üretir ve
                        # `check_source_freshness` hiçbir kanonik dala girmez
                        # (tazelik denetimi sessizce devre dışı kalırdı).
                        "source_type": str(delivered[ref].get("source_type") or "canonical")[:32],
                        "source_version": delivered[ref].get("source_version"),
                        "scope_project": episode.scope_project,
                    }
                    for ref in kept[:MAX_SUPPORT_REFS_PER_ITEM]
                ],
            )
        )

    # Yalnız A2'nin GERÇEKTEN teslim ettiği referans aileleriyle kesişebilen
    # alanlar okunur: `entity:` (proje/todo/son tarih). `recent_completed` ve
    # `state_changes` `event:<id>` taşır, `passed_plans` ise `plan_slot:<id>`;
    # bunlar A2'nin teslim ettiği kümeyle yapısal olarak kesişemez, bu yüzden
    # okunmazlar — erişilemeyen bir yol yazmak ölü sözleşme olurdu.
    for loop in list(bundle.open_loops)[:MAX_OPEN_THREADS]:
        add("open_thread", str(loop.title), list(loop.support_refs or []))
    for loop in list(bundle.newly_overdue)[:MAX_OPEN_THREADS]:
        add("open_thread", str(loop.title), list(loop.support_refs or []))
    for thread in list(bundle.active_threads)[:MAX_OPEN_THREADS]:
        add("open_thread", str(thread.title), list(thread.support_refs or []))

    return observations, []


async def finalize(session: AsyncSession, body: EpisodeFinalizeIn) -> EpisodeFinalizeOut:
    """Oturumu mühürler. İdempotenttir: ikinci çağrı aynı kaydı döndürür."""
    now = _now()
    session_row = await _session_row(session, body.harness, body.session_id)
    if session_row is None:
        raise EpisodeSessionNotFound(body.session_id)

    episode = await _get_or_create_episode(session, session_row)
    if episode.status != "draft":
        # Mühürlü kayıt geri açılmaz. Yanıt alanları rollback'ten ÖNCE
        # okunur: rollback ORM nesnesini expire eder ve sonraki nitelik
        # erişimi async bağlamda lazy-load denemesi olurdu.
        settled = EpisodeFinalizeOut(
            sealed=True,
            duplicate=True,
            status=episode.status,
            episode_id=episode.id,
            item_count=episode.item_count,
            turn_count=episode.turn_count,
            scope_project=episode.scope_project,
            sealed_at=episode.sealed_at or now,
            degraded_reasons=list(episode.degraded_reasons or []),
        )
        await session.rollback()
        return settled

    turn_rows = (
        await session.execute(
            select(AgentSessionEpisodeTurn)
            .where(AgentSessionEpisodeTurn.episode_id == episode.id)
            .order_by(AgentSessionEpisodeTurn.delivered_at, AgentSessionEpisodeTurn.id)
        )
    ).scalars().all()

    degraded: list[str] = []
    for row in turn_rows:
        for reason in row.degraded_reasons or []:
            if reason not in degraded:
                degraded.append(reason)

    all_refs = await _all_delivered_refs(session, episode.id)
    scope_res = resolve_scope(all_refs)
    if scope_res.ambiguous:
        episode.scope_project = None
        if "SCOPE_AMBIGUOUS" not in degraded:
            degraded.append("SCOPE_AMBIGUOUS")
    else:
        episode.scope_project = scope_res.scope_project

    observed_turns = [row for row in turn_rows if row.observed_at is not None]

    item_rows = (
        await session.execute(
            select(AgentSessionEpisodeItem, AgentSessionEpisodeTurn)
            .join(
                AgentSessionEpisodeTurn,
                AgentSessionEpisodeTurn.id == AgentSessionEpisodeItem.episode_turn_id,
            )
            .where(AgentSessionEpisodeItem.episode_id == episode.id)
            .order_by(AgentSessionEpisodeTurn.delivered_at, AgentSessionEpisodeItem.ordinal)
        )
    ).all()

    # Aday listesi: ifade + bağlı olduğu tur satırı. Eşleşme ORDINAL ile taşınır;
    # digest ile geri arama yapılmaz, çünkü aynı metni işleyen iki tur aynı
    # digest'i üretir ve ifade yanlış tura bağlanırdı.
    candidates: list[tuple[SessionHandoffItem, int | None]] = [
        (
            SessionHandoffItem(
                ordinal=index,
                kind=item.kind,
                text=item.text,
                evidence_class=item.evidence_class,
                support_refs=[EpisodeSupportRef(**ref) for ref in (item.support_refs or [])],
                turn_digest=turn.turn_digest,
            ),
            turn.id,
        )
        for index, (item, turn) in enumerate(item_rows)
    ]

    observations, h5_degraded = await _collect_session_observations(
        session, episode=episode, sealed_at=now
    )
    for reason in h5_degraded:
        if reason not in degraded:
            degraded.append(reason)

    candidates.extend(
        (
            SessionHandoffItem(
                ordinal=len(candidates) + index,
                kind=kind,
                text=text[:300],
                evidence_class="observed_during_session",
                support_refs=[EpisodeSupportRef(**ref) for ref in refs],
                turn_digest=None,
            ),
            None,
        )
        for index, (kind, text, refs) in enumerate(observations)
    )

    # Yeni mühürleme: eski türetilmiş ifadeler tazelenir (yeniden mühürleme YOK).
    await session.execute(
        delete(AgentSessionEpisodeItem).where(AgentSessionEpisodeItem.episode_id == episode.id)
    )
    await session.flush()

    items_only = [item for item, _ in candidates]
    deduped = dedupe_indices(items_only)
    selected = [deduped[position] for position in bounded_indices([items_only[i] for i in deduped])]

    for ordinal, index in enumerate(selected):
        item, turn_row_id = candidates[index]
        session.add(
            AgentSessionEpisodeItem(
                episode_id=episode.id,
                episode_turn_id=turn_row_id,
                ordinal=ordinal,
                kind=item.kind,
                text=item.text,
                evidence_class=item.evidence_class,
                support_refs=[
                    ref.model_dump() for ref in item.support_refs[:MAX_SUPPORT_REFS_PER_ITEM]
                ],
            )
        )

    if not selected:
        status = "sealed_empty"
        if "EPISODE_EMPTY" not in degraded:
            degraded.append("EPISODE_EMPTY")
    elif degraded:
        status = "sealed_degraded"
    else:
        status = "sealed"

    episode.status = status
    episode.sealed_at = now
    episode.turn_count = len(observed_turns)
    episode.item_count = len(selected)
    episode.degraded_reasons = degraded
    episode.expires_at = _episode_expiry(now)

    await prune(session, now)
    await session.commit()

    return EpisodeFinalizeOut(
        sealed=True,
        duplicate=False,
        status=status,
        episode_id=episode.id,
        item_count=len(selected),
        turn_count=len(observed_turns),
        scope_project=episode.scope_project,
        sealed_at=now,
        degraded_reasons=degraded,
    )


async def _stale_refs(
    session: AsyncSession, handoff: SessionHandoffV1
) -> set[tuple[str, str | None]]:
    """Destek referanslarını canlı kanonik veriye karşı yeniden doğrular (§22).

    Tarihsel ifade SİLİNMEZ: yalnız "kanıtı artık taze değil" işareti konur.
    Böylece devir güncel durum gibi sunulmaz ama tarihsel kayıt korunur.
    """
    from app.modules.agent_continuity.service import check_source_freshness

    seen: set[tuple[str, str]] = set()
    stale: set[tuple[str, str | None]] = set()
    checked = 0
    for item in handoff.items:
        for ref in item.support_refs:
            if checked >= MAX_STALE_CHECKS:
                return stale
            identity = (ref.source_id, ref.source_type)
            if identity in seen:
                continue
            seen.add(identity)
            checked += 1
            probe = AgentSessionSource(
                session_id=0,
                source_id=ref.source_id,
                source_type=ref.source_type,
                source_version=ref.source_version,
                scope_project=ref.scope_project,
                delivered_at=handoff.sealed_at,
                expires_at=handoff.sealed_at,
            )
            try:
                fresh, _title = await check_source_freshness(session, probe)
            except Exception as exc:  # noqa: BLE001 - tazelik probu devri düşürmez
                LOGGER.warning("A3 support freshness probe degraded: %s", type(exc).__name__)
                continue
            if not fresh:
                stale.add((ref.source_id, ref.source_version))
    return stale


async def select_recent_handoff(
    session: AsyncSession,
    *,
    current_session_id: int,
    current_scope: str | None,
    current_scope_ambiguous: bool = False,
    now: datetime | None = None,
) -> SessionHandoffV1 | None:
    """Yeni oturumun ilk turu için EN FAZLA bir ilgili devir seçer (§19 / A3.1).

    Kapsam uyumu önceliklidir. Kapsamı belirsiz bir eşleşme kurulacaksa hiç
    devir verilmez: yanlış devir, devirsizlikten kötüdür.
    """
    if current_scope_ambiguous:
        return None

    moment = now or _now()
    base = (
        select(AgentSessionEpisode)
        .where(
            AgentSessionEpisode.session_id != current_session_id,
            AgentSessionEpisode.status.in_(_SEALED_STATUSES),
            AgentSessionEpisode.expires_at > moment,
            AgentSessionEpisode.item_count > 0,
            not_(AgentSessionEpisode.degraded_reasons.contains(["SCOPE_AMBIGUOUS"])),
        )
        .order_by(AgentSessionEpisode.sealed_at.desc(), AgentSessionEpisode.id.desc())
        .limit(1)
    )

    row = None
    if current_scope:
        row = (
            await session.execute(
                base.where(AgentSessionEpisode.scope_project == current_scope)
            )
        ).scalar_one_or_none()
        if row is None:
            row = (
                await session.execute(
                    base.where(AgentSessionEpisode.scope_project.is_(None))
                )
            ).scalar_one_or_none()
    else:
        row = (
            await session.execute(base.where(AgentSessionEpisode.scope_project.is_(None)))
        ).scalar_one_or_none()

    if row is None:
        return None

    item_rows = (
        await session.execute(
            select(AgentSessionEpisodeItem, AgentSessionEpisodeTurn.turn_digest)
            .outerjoin(
                AgentSessionEpisodeTurn,
                AgentSessionEpisodeTurn.id == AgentSessionEpisodeItem.episode_turn_id,
            )
            .where(AgentSessionEpisodeItem.episode_id == row.id)
            .order_by(AgentSessionEpisodeItem.ordinal)
        )
    ).all()

    handoff = bound_handoff_items(
        SessionHandoffV1(
            episode_id=row.id,
            source_session_key=(await _session_key_of(session, row.session_id)),
            sealed_at=row.sealed_at or moment,
            scope_project=row.scope_project,
            items=[
                SessionHandoffItem(
                    ordinal=item.ordinal,
                    kind=item.kind,
                    text=item.text,
                    evidence_class=item.evidence_class,
                    support_refs=[EpisodeSupportRef(**ref) for ref in (item.support_refs or [])],
                    turn_digest=digest,
                )
                for item, digest in item_rows
            ],
            degraded_reasons=list(row.degraded_reasons or []),
        )
    )

    stale = await _stale_refs(session, handoff)
    if stale:
        handoff = handoff.model_copy(
            update={
                "items": [
                    item.model_copy(
                        update={
                            "historical_support_stale": any(
                                (ref.source_id, ref.source_version) in stale
                                for ref in item.support_refs
                            )
                        }
                    )
                    for item in handoff.items
                ],
                "degraded_reasons": sorted(set(list(handoff.degraded_reasons) + ["SOURCE_STALE"])),
            }
        )
    return handoff


async def observe_turn_delivery(
    session: AsyncSession,
    *,
    session_row: AgentSession,
    raw_turn_id: str | None,
    turn_db_id: int | None,
    sources: list[Any],
    is_first_turn: bool,
    explicit_scope: str | None = None,
    now: datetime | None = None,
) -> tuple[SessionHandoffV1 | None, str | None, list[str]]:
    """`/turn` orkestrasyon ucunun A3 tarafı: defter yazımı + (ilk turda) devir.

    Tek çağrıda iki iş yapılır çünkü ikisi de AYNI turda teslim edilen kaynak
    kümesini kullanır:

    1. Bu turda teslim edilen kaynakları A3 defterine yaz (her turda).
    2. Yalnız YENİ oturumun İLK turunda, ilgili ve mühürlenmiş bir önceki
       oturum devrini seç ve render et (§19/§20).

    A3 hiçbir koşulda A2/A1 akışını düşürmez: her hata sınırlı bir gerekçe
    koduna indirgenir ve `(None, None, [kod])` döner.
    """
    moment = now or _now()
    degraded: list[str] = []
    # Tur kimliği yoksa defter satırı YAZILMAZ: kimliksiz bir "tur" uydurmak
    # kaynak bağını yanlış bir tur anahtarına bağlardı.
    if raw_turn_id:
        try:
            await record_delivered(
                session,
                session_row=session_row,
                raw_turn_id=raw_turn_id,
                turn_db_id=turn_db_id,
                sources=sources,
                delivered_at=moment,
            )
        except Exception as exc:  # noqa: BLE001 - defter yazımı hot path'i düşürmez
            await session.rollback()
            LOGGER.warning("A3 delivery ledger degraded: %s", type(exc).__name__)
            degraded.append("SOURCE_BINDING_UNAVAILABLE")

    if not is_first_turn:
        return None, None, degraded

    try:
        refs = [
            ref for ref in (delivered_ref_from_source(source) for source in sources) if ref
        ]
        scope_res = resolve_scope(refs, explicit_scope=explicit_scope)
        handoff = await select_recent_handoff(
            session,
            current_session_id=session_row.id,
            current_scope=scope_res.scope_project,
            current_scope_ambiguous=scope_res.ambiguous,
            now=moment,
        )
    except Exception as exc:  # noqa: BLE001 - devir seçimi hot path'i düşürmez
        await session.rollback()
        LOGGER.warning("A3 handoff selection degraded: %s", type(exc).__name__)
        degraded.append("EPISODE_HANDOFF_UNAVAILABLE")
        return None, None, degraded

    if handoff is None:
        return None, None, degraded

    rendered = render_handoff(handoff)
    if rendered.truncated:
        degraded.append("EPISODE_FINALIZE_DEGRADED")
    return handoff, rendered.text, degraded


async def _session_key_of(session: AsyncSession, session_id: int) -> str:
    key = (
        await session.execute(select(AgentSession.session_key).where(AgentSession.id == session_id))
    ).scalar_one_or_none()
    return key or ""


async def status(session: AsyncSession) -> EpisodeStatusOut:
    """Metadata-only tanılama (§30): ham konuşma içeriği DÖNMEZ."""
    now = _now()
    try:
        last = (
            await session.execute(
                select(AgentSessionEpisode)
                .where(AgentSessionEpisode.status.in_(_SEALED_STATUSES))
                .order_by(AgentSessionEpisode.sealed_at.desc(), AgentSessionEpisode.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        drafts = int(
            (
                await session.execute(
                    select(func.count()).select_from(AgentSessionEpisode).where(
                        AgentSessionEpisode.status == "draft",
                        AgentSessionEpisode.updated_at
                        > now - timedelta(hours=DRAFT_STALE_HOURS),
                    )
                )
            ).scalar_one()
        )
        # `select_recent_handoff` kapsamı ÇAĞRI ANINDA karşılaştırır; durum ucu
        # ise yalnız "teslim edilebilir mühürlü bir devir var mı" sorusunu
        # cevaplar. Ancak SCOPE_AMBIGUOUS işaretli devirler hiçbir koşulda
        # teslim edilemeyeceğinden (A3.1 §19), uygunluk filtresi bunları hariç tutar.
        available = (
            await session.execute(
                select(AgentSessionEpisode.id)
                .where(
                    AgentSessionEpisode.status.in_(_SEALED_STATUSES),
                    AgentSessionEpisode.expires_at > now,
                    AgentSessionEpisode.item_count > 0,
                    not_(AgentSessionEpisode.degraded_reasons.contains(["SCOPE_AMBIGUOUS"])),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return EpisodeStatusOut(
            available=True,
            last_sealed_at=last.sealed_at if last else None,
            last_episode_item_count=last.item_count if last else 0,
            last_scope_project=last.scope_project if last else None,
            recent_handoff_available=available is not None,
            draft_episode_count=drafts,
            degraded_reasons=list(last.degraded_reasons or []) if last else [],
        )
    except Exception as exc:  # noqa: BLE001 - tanılama ucu 500 vermez
        LOGGER.warning("A3 episode status degraded: %s", type(exc).__name__)
        return EpisodeStatusOut(available=False)


async def prune(session: AsyncSession, now: datetime | None = None) -> None:
    """Sınırlı saklama (§18). Çağıran commit eder.

    - Süresi geçmiş devirler silinir.
    - Son `MAX_SEALED_EPISODES` dışında kalan mühürlü devirler silinir.
    - `DRAFT_STALE_HOURS`'tan uzun süre dokunulmamış taslaklar silinir.
      Eksik finalize OTOMATİK OLARAK "başarıyla tamamlandı" diye mühürlenmez.
    """
    moment = now or _now()
    await session.execute(
        delete(AgentSessionEpisode).where(AgentSessionEpisode.expires_at < moment)
    )
    await session.execute(
        delete(AgentSessionEpisode).where(
            AgentSessionEpisode.status == "draft",
            AgentSessionEpisode.updated_at < moment - timedelta(hours=DRAFT_STALE_HOURS),
        )
    )
    keep_ids = (
        await session.scalars(
            select(AgentSessionEpisode.id)
            .where(AgentSessionEpisode.status.in_(_SEALED_STATUSES))
            .order_by(AgentSessionEpisode.sealed_at.desc(), AgentSessionEpisode.id.desc())
            .limit(MAX_SEALED_EPISODES)
        )
    ).all()
    if keep_ids:
        await session.execute(
            delete(AgentSessionEpisode).where(
                AgentSessionEpisode.status.in_(_SEALED_STATUSES),
                AgentSessionEpisode.id.not_in(keep_ids),
            )
        )


__all__ = [
    "EpisodeSessionNotFound",
    "ScopeResolution",
    "derive_scope",
    "finalize",
    "ingest_turn",
    "observe_turn_delivery",
    "prune",
    "record_delivered",
    "resolve_scope",
    "select_recent_handoff",
    "status",
]
