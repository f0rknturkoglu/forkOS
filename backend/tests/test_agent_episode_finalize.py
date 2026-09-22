"""A3 §15/§17/§18/§35 — mühürleme, idempotans, sıralama, tavanlar ve saklama.

Bu dosya A3'ün KENDİ üç tablosunun davranışını kanıtlar: mühürlenmiş kayıt geri
açılmaz, ikinci finalize güvenli no-op'tur, tür/toplam/ref/metin tavanları
uygulanır ve saklama sınırlıdır.

Gözlemlenen sıralama davranışı (buradaki iddianın dayanağı): DB'deki `ordinal`
sırası tur teslim sırasını ve modelin tur içindeki üretim sırasını izler;
`KIND_ORDER` yalnız OKUMA modelinde (render katmanı) gruplama için kullanılır.
Bu yüzden burada kanıtlanan şey sıralamanın DETERMİNİSTİK ve kesintisiz
olmasıdır, türe göre yeniden sıralanması değil.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.modules.agent_episode import service as a3
from app.modules.agent_episode.models import (
    AgentSessionEpisode,
    AgentSessionEpisodeItem,
    AgentSessionEpisodeTurn,
)
from app.modules.agent_episode.schemas import (
    KIND_ORDER,
    MAX_EPISODE_ITEMS,
    MAX_OUTCOMES,
    MAX_SEALED_EPISODES,
    MAX_SUPPORT_REFS_PER_ITEM,
    MAX_TOPICS,
)
from app.modules.agent_lifecycle.models import AgentSession
from tests.a3_fixtures import (
    NOW,
    Source,
    deliver,
    ingest,
    items_json,
    patch_provider,
    seal,
    start_session,
)
from tests.h4_test_provider import ScriptedProvider

USER_MESSAGE = "Alfa projesi için sınav takvimini kontrol eder misin?"
ASSISTANT_RESPONSE = (
    "Alfa projesinin takvimi güncellendi. Beta modülü için açık bir iş kaldı: "
    "şema doğrulaması yazılacak."
)
TURN_ITEMS = [
    ("topic", "Alfa projesinin sınav takvimi ele alındı.", "Alfa projesinin takvimi güncellendi"),
    (
        "open_thread",
        "Beta modülünde şema doğrulaması yazılacak.",
        "Beta modülü için açık bir iş kaldı",
    ),
]


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def _run_turns(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    key: str,
    turns: list[tuple[str, str, list[tuple[str, str, str]]]],
) -> Any:
    """Her turu kendi betikli model yanıtıyla çalıştırır; A1 oturum satırını döner.

    Tur başına bir üretim çağrısı yapılır (yanıtlar geçerlidir), bu yüzden
    `responses[i]` i. tura karşılık gelir.
    """
    patch_provider(
        monkeypatch, ScriptedProvider(responses=[items_json(entries) for _, _, entries in turns])
    )
    session_row = await start_session(session, key)
    for index, (user, assistant, _entries) in enumerate(turns, start=1):
        turn_id = f"t{index}"
        await deliver(
            session,
            session_row,
            raw_turn_id=turn_id,
            sources=[Source("project:alfa", "project", title="Alfa Projesi")],
            is_first_turn=index == 1,
        )
        await ingest(session, key, turn_id=turn_id, user=user, assistant=assistant)
    return session_row


async def _stored_items(session: AsyncSession, episode_id: int) -> list[AgentSessionEpisodeItem]:
    rows = await session.execute(
        select(AgentSessionEpisodeItem)
        .where(AgentSessionEpisodeItem.episode_id == episode_id)
        .order_by(AgentSessionEpisodeItem.ordinal)
    )
    return list(rows.scalars().all())


async def _seed_episode(
    session: AsyncSession,
    key: str,
    *,
    status: str = "draft",
    sealed_at: Any = None,
    updated_at: Any = None,
    expires_at: Any = None,
    item_count: int = 0,
) -> AgentSessionEpisode:
    """Saklama/budama testleri için doğrudan episode satırı yazar (damıtma yok)."""
    session_row = AgentSession(
        schema_version=1,
        harness="hermes",
        session_key=key,
        platform="cli",
        first_seen_at=NOW,
        start_seen_at=NOW,
        last_seen_at=NOW,
        status="active",
        turn_count=0,
    )
    session.add(session_row)
    await session.flush()
    episode = AgentSessionEpisode(
        session_id=session_row.id,
        schema_version=1,
        status=status,
        started_at=NOW,
        sealed_at=sealed_at,
        turn_count=0,
        item_count=item_count,
        degraded_reasons=[],
        expires_at=expires_at or NOW + timedelta(days=14),
    )
    if updated_at is not None:
        episode.updated_at = updated_at
    session.add(episode)
    await session.flush()
    return episode


# ---------------------------------------------------------------------------
# §15 — mühürleme ve idempotans
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("h4_ready")
async def test_first_finalize_seals_and_counts_items(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """İlk finalize devri mühürler; sayaç DB'deki ifade sayısıyla uyumludur."""
    await _run_turns(
        db_session,
        monkeypatch,
        "a3-finalize-first",
        [(USER_MESSAGE, ASSISTANT_RESPONSE, TURN_ITEMS)],
    )

    out = await seal(db_session, "a3-finalize-first")

    assert out.sealed is True
    assert out.duplicate is False
    assert out.status in {"sealed", "sealed_degraded"}
    assert out.sealed_at is not None

    episode = (
        await db_session.execute(
            select(AgentSessionEpisode).where(AgentSessionEpisode.id == out.episode_id)
        )
    ).scalar_one()
    stored = await _stored_items(db_session, out.episode_id)
    assert episode.status == out.status
    assert episode.sealed_at is not None
    assert out.item_count == len(stored) == len(TURN_ITEMS)
    assert episode.item_count == len(stored)


@pytest.mark.usefixtures("h4_ready")
async def test_second_finalize_is_a_duplicate_noop(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """İkinci finalize aynı mühürlü kaydı döndürür; hiçbir satır çoğalmaz."""
    session_row = await _run_turns(
        db_session,
        monkeypatch,
        "a3-finalize-duplicate",
        [(USER_MESSAGE, ASSISTANT_RESPONSE, TURN_ITEMS)],
    )
    # `seal` ikinci çağrıda rollback yapar ve ORM nesnelerini expire eder; kimliği
    # şimdiden al (sonradan erişim async bağlamda lazy-load denemesi olurdu).
    session_id = session_row.id
    first = await seal(db_session, "a3-finalize-duplicate")

    second = await seal(db_session, "a3-finalize-duplicate")

    assert second.duplicate is True
    assert second.episode_id == first.episode_id
    assert second.sealed_at == first.sealed_at
    assert second.item_count == first.item_count
    episode_count = (
        await db_session.execute(
            select(func.count())
            .select_from(AgentSessionEpisode)
            .where(AgentSessionEpisode.session_id == session_id)
        )
    ).scalar_one()
    assert episode_count == 1
    assert len(await _stored_items(db_session, first.episode_id)) == first.item_count


@pytest.mark.usefixtures("h4_ready")
async def test_sealed_episode_rejects_further_ingest(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mühürlenmiş devir mutate edilmez: sonraki tur `EPISODE_SEALED` ile reddedilir."""
    await _run_turns(
        db_session,
        monkeypatch,
        "a3-finalize-sealed-ingest",
        [(USER_MESSAGE, ASSISTANT_RESPONSE, TURN_ITEMS)],
    )
    sealed = await seal(db_session, "a3-finalize-sealed-ingest")

    out = await ingest(
        db_session,
        "a3-finalize-sealed-ingest",
        turn_id="t2",
        user="Yeni bir tur",
        assistant="Yeni bir yanıt",
    )

    assert out.accepted is False
    assert out.derived_item_count == 0
    assert "EPISODE_SEALED" in out.degraded_reasons
    episode = (
        await db_session.execute(
            select(AgentSessionEpisode).where(AgentSessionEpisode.id == sealed.episode_id)
        )
    ).scalar_one()
    assert episode.status == sealed.status
    assert len(await _stored_items(db_session, sealed.episode_id)) == sealed.item_count


@pytest.mark.usefixtures("h4_ready")
async def test_finalize_without_turns_seals_empty(
    db_session: AsyncSession
) -> None:
    """Sıfır aday dürüst boş durumdur: `sealed_empty`, uydurma ifade yok."""
    await start_session(db_session, "a3-finalize-empty")

    out = await seal(db_session, "a3-finalize-empty")

    assert out.sealed is True
    assert out.status == "sealed_empty"
    assert out.item_count == 0
    assert out.turn_count == 0
    assert "EPISODE_EMPTY" in out.degraded_reasons


# ---------------------------------------------------------------------------
# §17 — sıralama ve tavanlar
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("h4_ready")
async def test_item_order_is_contiguous_and_deterministic(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Aynı girdi iki bağımsız devirde aynı ordinal/tür dizisini üretir.

    Tür dizisi modelin tur içindeki üretim sırasıdır (burada bilinçli olarak
    `KIND_ORDER`'dan farklı): determinizm iddiası bunu sabitler.
    """
    mixed = [
        ("outcome", "Alfa takvimi güncellendi.", "Alfa projesinin takvimi güncellendi"),
        ("topic", "Alfa takvimi konuşuldu.", "sınav takvimini kontrol eder misin"),
        ("open_thread", "Beta işi açık kaldı.", "açık bir iş kaldı"),
    ]
    first_row = await _run_turns(
        db_session,
        monkeypatch,
        "a3-order-first",
        [(USER_MESSAGE, ASSISTANT_RESPONSE, mixed)],
    )
    second_row = await _run_turns(
        db_session,
        monkeypatch,
        "a3-order-second",
        [(USER_MESSAGE, ASSISTANT_RESPONSE, mixed)],
    )
    first_row_id, second_row_id = first_row.id, second_row.id
    first = await seal(db_session, "a3-order-first")
    second = await seal(db_session, "a3-order-second")

    first_items = await _stored_items(db_session, first.episode_id)
    second_items = await _stored_items(db_session, second.episode_id)

    assert [item.ordinal for item in first_items] == list(range(len(first_items)))
    assert [item.ordinal for item in second_items] == list(range(len(second_items)))
    assert [item.kind for item in first_items] == [kind for kind, _, _ in mixed]
    assert [item.kind for item in second_items] == [item.kind for item in first_items]
    assert first_row_id != second_row_id
    assert set(KIND_ORDER).issuperset(item.kind for item in first_items)


@pytest.mark.usefixtures("h4_ready")
async def test_kind_and_total_caps_are_enforced(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """4+ konu ve 5+ sonuç üretilse de tür ve toplam tavanları uygulanır."""
    topics = [
        ("topic", f"Konu {index} ele alındı.", "sınav takvimi konusu") for index in range(4)
    ]
    outcomes = [
        ("outcome", f"Sonuç {index} kaydedildi.", "sonuç kaydedildi") for index in range(5)
    ]
    await _run_turns(
        db_session,
        monkeypatch,
        "a3-caps",
        [
            ("sınav takvimi konusu", "sınav takvimi konusu", topics),
            ("sonuç kaydedildi", "sonuç kaydedildi", outcomes),
        ],
    )

    out = await seal(db_session, "a3-caps")

    stored = await _stored_items(db_session, out.episode_id)
    counts = Counter(item.kind for item in stored)
    assert counts["topic"] == MAX_TOPICS
    assert counts["outcome"] == MAX_OUTCOMES
    assert out.item_count == len(stored)
    assert len(stored) <= MAX_EPISODE_ITEMS


@pytest.mark.usefixtures("h4_ready")
async def test_support_refs_are_capped_per_item(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Teslim edilen 6 kaynak da eşleşse bile ifade başına en fazla 5 ref saklanır."""
    titles = [f"kaynak {char} projesi" for char in "abcdef"]
    excerpt = " ".join(titles)
    patch_provider(
        monkeypatch,
        ScriptedProvider(
            responses=[items_json([("topic", "Altı kaynak birlikte değerlendirildi.", excerpt)])]
        ),
    )
    session_row = await start_session(db_session, "a3-ref-cap")
    await deliver(
        db_session,
        session_row,
        raw_turn_id="t1",
        sources=[Source(f"project:{index}", "project", title=title) for index, title in enumerate(titles)],
    )
    await ingest(db_session, "a3-ref-cap", turn_id="t1", user="merhaba", assistant=excerpt)

    out = await seal(db_session, "a3-ref-cap")

    stored = await _stored_items(db_session, out.episode_id)
    assert len(stored) == 1
    assert len(stored[0].support_refs) == MAX_SUPPORT_REFS_PER_ITEM
    assert stored[0].evidence_class == "canonical_supported"


async def test_item_text_cap_is_enforced_by_the_database(
    db_session: AsyncSession,
) -> None:
    """300 karakter kabul, 301 karakter INSERT reddedilir.

    Şemada iki savunma var: `varchar(300)` kolon sınırı ve aynı tavanı yansıtan
    CHECK kısıtı. Bu ortamda kolon sınırı devreye girer ve asyncpg hatası genel
    `DBAPIError` olarak yüzeye çıkar (CHECK devreye girseydi `IntegrityError`
    olurdu — ikisi de `DBAPIError` alt sınıfıdır); her iki durumda da INSERT
    reddedilmelidir.
    """
    episode = await _seed_episode(db_session, "a3-text-cap")
    episode_id = episode.id
    # `observed_during_session` kanıt taşımak ZORUNDADIR; bu test metin tavanını
    # izole ettiği için ref'i baştan geçerli veriyoruz.
    observed_ref = [
        {
            "source_id": "project:text-cap",
            "source_type": "project",
            "source_version": None,
            "scope_project": None,
        }
    ]
    db_session.add(
        AgentSessionEpisodeItem(
            episode_id=episode_id,
            episode_turn_id=None,
            ordinal=0,
            kind="topic",
            text="x" * 300,
            evidence_class="observed_during_session",
            support_refs=observed_ref,
        )
    )
    await db_session.commit()

    db_session.add(
        AgentSessionEpisodeItem(
            episode_id=episode_id,
            episode_turn_id=None,
            ordinal=1,
            kind="topic",
            text="x" * 301,
            evidence_class="observed_during_session",
            support_refs=observed_ref,
        )
    )
    with pytest.raises(DBAPIError):
        await db_session.commit()
    await db_session.rollback()
    stored = (
        await db_session.execute(
            select(func.count())
            .select_from(AgentSessionEpisodeItem)
            .where(AgentSessionEpisodeItem.episode_id == episode_id)
        )
    ).scalar_one()
    assert stored == 1


# ---------------------------------------------------------------------------
# §18/§35 — budama ve saklama
# ---------------------------------------------------------------------------


async def test_stale_drafts_are_pruned_and_never_auto_sealed(
    db_session: AsyncSession,
) -> None:
    """Eski taslak silinir; taze taslak korunur ve hiçbir taslak mühürlenmez."""
    stale = await _seed_episode(
        db_session,
        "a3-draft-stale",
        updated_at=NOW - timedelta(hours=30),
    )
    turn = AgentSessionEpisodeTurn(
        episode_id=stale.id,
        turn_key="stale-turn",
        status="extracted",
        turn_digest="d" * 64,
        item_count=1,
        delivered_refs=[],
        degraded_reasons=[],
        delivered_at=NOW,
    )
    db_session.add(turn)
    await db_session.flush()
    db_session.add(
        AgentSessionEpisodeItem(
            episode_id=stale.id,
            episode_turn_id=turn.id,
            ordinal=0,
            kind="topic",
            text="Yarım kalmış tur ifadesi.",
            evidence_class="turn_derived",
            support_refs=[],
        )
    )
    fresh = await _seed_episode(
        db_session,
        "a3-draft-fresh",
        updated_at=NOW - timedelta(hours=1),
    )
    await db_session.commit()

    await a3.prune(db_session, now=NOW)
    await db_session.commit()

    remaining = list((await db_session.execute(select(AgentSessionEpisode))).scalars().all())
    ids = {row.id for row in remaining}
    assert stale.id not in ids
    assert fresh.id in ids
    assert fresh.status == "draft"
    assert all(row.status != "sealed" for row in remaining)
    item_count = (
        await db_session.execute(
            select(func.count())
            .select_from(AgentSessionEpisodeItem)
            .where(AgentSessionEpisodeItem.episode_id == stale.id)
        )
    ).scalar_one()
    assert item_count == 0


async def test_retention_keeps_newest_sealed_episodes_and_drops_expired(
    db_session: AsyncSession,
) -> None:
    """Son `MAX_SEALED_EPISODES` mühürlü devir kalır; süresi geçen silinir."""
    total = MAX_SEALED_EPISODES + 2
    created = [
        await _seed_episode(
            db_session,
            f"a3-retention-{index}",
            status="sealed",
            sealed_at=NOW - timedelta(minutes=total - index),
            item_count=1,
        )
        for index in range(total)
    ]
    expired = await _seed_episode(
        db_session,
        "a3-retention-expired",
        status="sealed",
        sealed_at=NOW - timedelta(minutes=1),
        expires_at=NOW - timedelta(days=1),
        item_count=1,
    )
    await db_session.commit()

    await a3.prune(db_session, now=NOW)
    await db_session.commit()

    remaining = {row.id for row in (await db_session.execute(select(AgentSessionEpisode))).scalars()}
    assert expired.id not in remaining
    assert remaining == {episode.id for episode in created[2:]}


async def test_deleting_episode_cascades_to_turns_and_items(
    db_session: AsyncSession,
) -> None:
    """Episode silinince tur defteri ve ifadeler de gider (FK ON DELETE CASCADE)."""
    episode = await _seed_episode(db_session, "a3-cascade")
    turn = AgentSessionEpisodeTurn(
        episode_id=episode.id,
        turn_key="cascade-turn",
        status="extracted",
        turn_digest="c" * 64,
        item_count=1,
        delivered_refs=[],
        degraded_reasons=[],
        delivered_at=NOW,
    )
    db_session.add(turn)
    await db_session.flush()
    db_session.add(
        AgentSessionEpisodeItem(
            episode_id=episode.id,
            episode_turn_id=turn.id,
            ordinal=0,
            kind="topic",
            text="Silinecek ifade.",
            evidence_class="turn_derived",
            support_refs=[],
        )
    )
    await db_session.commit()

    await db_session.delete(episode)
    await db_session.commit()

    turns = (
        await db_session.execute(
            select(func.count())
            .select_from(AgentSessionEpisodeTurn)
            .where(AgentSessionEpisodeTurn.episode_id == episode.id)
        )
    ).scalar_one()
    items = (
        await db_session.execute(
            select(func.count())
            .select_from(AgentSessionEpisodeItem)
            .where(AgentSessionEpisodeItem.episode_id == episode.id)
        )
    ).scalar_one()
    assert turns == 0
    assert items == 0


# ---------------------------------------------------------------------------
# §10 — H5 oturum-penceresi zemini GERÇEKTEN üretim yapıyor mu?
# ---------------------------------------------------------------------------


async def test_h5_session_window_grounding_produces_observed_items(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`observed_during_session` yolu ölü değildir: kanonik bir açık görev,
    oturumda teslim edilen kaynakla eşleşirse mühürlenen devre girer.

    Bu test H5'in gerçek `build_continuity` hattını çalıştırır; yalnız H4
    sağlayıcısı betiklenir (bu turda ifade üretmesin diye boş liste döner).
    """
    from tests.h5_fixtures import make_todo

    patch_provider(monkeypatch, ScriptedProvider(responses=['{"items": []}']))
    monkeypatch.setattr("app.config.settings.h4_enabled", True)

    todo = await make_todo(db_session, title="Şema doğrulamasını yaz")
    await db_session.commit()
    todo_ref = f"entity:{todo.id}"

    session_row = await start_session(db_session, "a3_h5_window")
    # A2 bu turda tam olarak bu kaynağı teslim etmiş gibi defteri yaz.
    await deliver(
        db_session,
        session_row,
        raw_turn_id="t1",
        sources=[Source(todo_ref, "deadline", title="Şema doğrulamasını yaz")],
    )
    await ingest(db_session, "a3_h5_window", turn_id="t1")
    result = await seal(db_session, "a3_h5_window")

    assert result.status in {"sealed", "sealed_degraded"}
    assert result.degraded_reasons.count("H5_UNAVAILABLE") == 0

    observed = (
        await db_session.execute(
            select(AgentSessionEpisodeItem).where(
                AgentSessionEpisodeItem.episode_id == result.episode_id,
                AgentSessionEpisodeItem.evidence_class == "observed_during_session",
            )
        )
    ).scalars().all()

    assert observed, "H5 açık döngüsü oturum penceresinde gözlem üretmedi"
    item = observed[0]
    assert item.kind == "open_thread"
    assert item.text == "Şema doğrulamasını yaz"
    assert item.episode_turn_id is None
    assert item.support_refs and item.support_refs[0]["source_id"] == todo_ref


async def test_h5_observation_requires_a_delivered_match(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kanonik gözlem VAR ama oturumda teslim edilmediyse devre girmez.

    Filtre olmadan bu, oturumun hiç görmediği bir olguyu devre yazardı.
    """
    from tests.h5_fixtures import make_todo

    patch_provider(monkeypatch, ScriptedProvider(responses=['{"items": []}']))
    monkeypatch.setattr("app.config.settings.h4_enabled", True)

    await make_todo(db_session, title="Teslim edilmeyen açık görev")
    await db_session.commit()

    session_row = await start_session(db_session, "a3_h5_nomatch")
    await deliver(
        db_session,
        session_row,
        raw_turn_id="t1",
        sources=[Source("entity:00000000-0000-0000-0000-000000000000", "project", title="Başka")],
    )
    await ingest(db_session, "a3_h5_nomatch", turn_id="t1")
    result = await seal(db_session, "a3_h5_nomatch")

    observed = (
        await db_session.execute(
            select(AgentSessionEpisodeItem).where(
                AgentSessionEpisodeItem.episode_id == result.episode_id,
                AgentSessionEpisodeItem.evidence_class == "observed_during_session",
            )
        )
    ).scalars().all()
    assert observed == []
