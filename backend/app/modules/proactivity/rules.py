"""H6 kural aileleri — KAPALI semantik kumeler, genel bir DSL YOK.

Her kural bir "tetik adayi" uretir; hicbiri kullaniciya dogrudan dokunmaz.
Karar `policy.py`'dedir, teslim `delivery.py`'de. Bu dosya yalnizca
"degerlendirilecek bir kosul var mi?" sorusunu yanitlar.

Kurallar H5'i YENIDEN YAZMAZ: sureklilik, gun kapanisi ve haftalik ozet
H5 servisinden gelir (§51). Burada yalnizca H6'nin kendi esikleri (son tarih
basamaklari, hareketsizlik suresi, proje esigi) ve aday kimligi uretilir.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.contributions import COUNTED_VERBS
from app.core.models import Entity, Event
from app.core.time import local_zone
from app.modules.proactivity.models import ProactivityRule

log = logging.getLogger("proactivity.rules")

#: Bir turda degerlendirilecek en fazla aday (patlama korumasi, §178).
MAX_TICK_CANDIDATES = 100
#: Tarama tavanlari: N+1 ile "kirpildi mi" bilgisi korunur (§180).
MAX_DEADLINE_ROWS = 200
MAX_STALLED_PROJECTS = 50

#: Son tarih basamaklari (gun). Kucukten buyuge; EN YAKIN esik kazanir.
#: Kabul edilmis eski merdiven (1,3,7,14,30) korunur ve T-0 eklenir: "bugun
#: bitiyor" ayri bir mantiksal kosudur (§45 uzlasi, tek tanim burada).
DEADLINE_RUNGS: tuple[int, ...] = (0, 1, 3, 7, 14, 30)
#: Takip tarihi merdiveni: 30 gun takip icin cok genistir.
FOLLOW_UP_RUNGS: tuple[int, ...] = (0, 1, 3, 7, 14)

#: Basamak -> kategori (teslim politikasi `policy.CATEGORY_OUTCOMES`).
_RUNG_CATEGORY: dict[int, str] = {
    0: "deadline_today",
    1: "deadline_tomorrow",
    3: "deadline_soon",
    7: "deadline_near",
    14: "deadline_far",
    30: "deadline_far",
}
#: Basamak -> gerekce kodu.
_RUNG_REASON: dict[int, str] = {
    0: "DEADLINE_TODAY",
    1: "DEADLINE_1D",
    3: "DEADLINE_3D",
    7: "DEADLINE_7D",
    14: "DEADLINE_14D",
    30: "DEADLINE_30D",
}


@dataclass(frozen=True)
class Candidate:
    """Degerlendirilecek kosul — kullaniciya dokunma karari HENUZ verilmedi."""

    rule_kind: str
    logical_trigger_key: str
    category: str
    why_now: str
    reason_codes: list[str] = field(default_factory=list)
    subject_type: str | None = None
    subject_id: uuid.UUID | None = None
    entity_id: uuid.UUID | None = None
    #: Son tarih kosulunun TEKIL kimligi (yalniz deadline_staircase icin).
    condition_identity: str | None = None
    #: Tek seferlik kosul mu (basamak/ritüel) yoksa tekrarlanabilir mi (proje)?
    one_shot: bool = True
    #: Tekrarlanabilir kosulda yeniden yuzeye cikma beklemesi (saat).
    cooldown_hours: int | None = None
    #: Teslim aninda kurulacak H5 baglami (varsa).
    h5_mode: str | None = None


#: Kimlik cozumlemesinin uc hali. `indeterminate`, "tarama siniri yuzunden
#: goremedim" demektir ve ASLA "yok" olarak yorumlanmaz.
IdentityStatus = Literal["found", "not_found", "indeterminate"]


@dataclass(frozen=True)
class RuleFailure:
    """Kural degerlendirmesi basarisiz — digerleri ETKILENMEZ (§152)."""

    rule_kind: str
    failure_code: str


# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------


def _rung(days: int, rungs: tuple[int, ...]) -> int | None:
    """Kalan sureye EN YAKIN esik. Artan sirada ilk uyan basamak kazanir."""
    return next((step for step in rungs if days <= step), None)


def local_now(moment: datetime) -> datetime:
    return moment.astimezone(local_zone())


async def last_meaningful_activity_at(session: AsyncSession) -> datetime | None:
    """Sayilan SON insan hareketi — arka plan gurultusu SAYILMAZ (§55).

    `COUNTED_VERBS` tek kaynaktir: worker senkronu, kaynak sagligi, bildirim
    ve proaktivite kosulari bu listede OLMADIGI icin hareketsizlik saatini
    sifirlayamaz.
    """
    return (
        await session.execute(
            select(func.max(Event.occurred_at)).where(Event.verb.in_(COUNTED_VERBS))
        )
    ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Kural degerlendiricileri
# ---------------------------------------------------------------------------


async def _deadline_candidates(
    session: AsyncSession, rule: ProactivityRule, *, now: datetime
) -> list[Candidate]:
    """Son tarih merdiveni: TEK mantiksal uretici (eski merdiven emekli)."""
    from app.core.deadlines import collect_deadlines
    from app.modules.opportunity.service import pending_follow_up_rows

    candidates: list[Candidate] = []
    for row, kind in (
        *((row, "deadline") for row in await collect_deadlines(session, limit=MAX_DEADLINE_ROWS)),
        *((row, "follow_up") for row in await pending_follow_up_rows(session)),
    ):
        due = row.get("due_at")
        if due is None or due < now:
            continue
        # Basamak disi (or. T-31 normal / T-15 takip) satir ADAY DEGILDIR.
        # Sozlesme: bu fonksiyon YALNIZCA gercek Candidate dondurur; `None`
        # listeye giremez, aksi halde kuralin tamami duserdi.
        candidate = _deadline_candidate(row, due=due, now=now, kind=kind)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


#: Kosul kimligi bilesen ayirici. Anahtar sozdiziminde ":" ayiricidir; bu
#: yuzden kimlik ve revizyon ":" ICERMEZ.
IDENTITY_SEPARATOR = "."


def condition_identity(row: dict) -> str | None:
    """Bir son tarih satirinin TEKIL kosul kimligi (H6.1).

    Ayni entity uzerinde birden fazla bagimsiz temporal kosul olabilir
    (ilan son tarihi, takip tarihi, N gorusme). Kimlik:

        <module>.<sub_kind|due>.<condition_id|entity_id>

    - deterministiktir (gosterim metnine, liste sirasina bagli DEGIL),
    - kanonik verilere dayanir (alt kaydin kararli PK'si varsa o kullanilir),
    - restart sonrasi AYNIdir (process-local durum yok).
    """
    entity_id = as_uuid(row.get("entity_id"))
    if entity_id is None:
        return None
    module = str(row.get("module") or "unknown").replace(":", "").replace(".", "_")
    sub_kind = str(row.get("sub_kind") or "due").replace(":", "").replace(".", "_")
    child = row.get("condition_id")
    tail = str(child).replace(":", "").replace(".", "_") if child else str(entity_id)
    return IDENTITY_SEPARATOR.join((module, sub_kind, tail))


def temporal_revision(due: datetime | date) -> str:
    """Anlamli son tarih degisimini temsil eden NORMALIZE revizyon.

    - date-only son tarih → `YYYY-MM-DD` (gun degisimi revizyonu degistirir)
    - datetime son tarih  → UTC'ye normalize `YYYYMMDDTHHMMSSZ` (ayni gun
      icindeki saat degisikligi de revizyonu degistirir)

    Sozdiziminde ":" YOKTUR: anahtar ayiricisiyla cakismaz.
    """
    if isinstance(due, datetime):
        moment = due if due.tzinfo is not None else due.replace(tzinfo=UTC)
        return moment.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return due.isoformat()


def identity_of_key(logical_trigger_key: str) -> str | None:
    """`deadline:v2:<kimlik>:<revizyon>:<rung>d` anahtarindan kimligi cozer."""
    parts = logical_trigger_key.split(":")
    if len(parts) != 5 or parts[0] != "deadline" or parts[1] != "v2":
        return None
    return parts[2]


def revision_of_key(logical_trigger_key: str) -> str | None:
    parts = logical_trigger_key.split(":")
    if len(parts) != 5 or parts[0] != "deadline" or parts[1] != "v2":
        return None
    return parts[3]


def as_uuid(value: object) -> uuid.UUID | None:
    """Kimlik normalizasyonu: son tarih satirlari id'yi metin de verebilir."""
    if isinstance(value, uuid.UUID):
        return value
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _deadline_candidate(row: dict, *, due: datetime, now: datetime, kind: str) -> Candidate | None:
    days = max((due - now).days, 0)
    rungs = FOLLOW_UP_RUNGS if kind == "follow_up" else DEADLINE_RUNGS
    rung = _rung(days, rungs)
    entity_id = as_uuid(row.get("entity_id"))
    identity = condition_identity(row)
    if rung is None or entity_id is None or identity is None:
        return None
    # Revizyon = kosulun ANLAMLI son tarihi: gun (ve datetime icin saat)
    # degisirse eski kosu bayatlar, yeni revizyon bagimsiz basamaklar uretir.
    revision = temporal_revision(due)
    title = str(row.get("title") or "Kayıt")
    return Candidate(
        rule_kind="deadline_staircase",
        # v2: kosul kimligi entity'den AYRI taşinir; ayni entity'nin farkli
        # kosullari (ilan/takip/gorusme) birbirini ezemez.
        logical_trigger_key=f"deadline:v2:{identity}:{revision}:{rung}d",
        category=_RUNG_CATEGORY[rung],
        why_now=f"{title} için son tarih {days} gün içinde",
        reason_codes=[_RUNG_REASON[rung]],
        subject_type=str(row.get("type") or kind),
        subject_id=entity_id,
        entity_id=entity_id,
        condition_identity=identity,
    )


async def _continuity_gap_candidates(
    session: AsyncSession, rule: ProactivityRule, *, now: datetime
) -> list[Candidate]:
    """Sessizlik + ANLAMLI degisim: yalnizca hareketsizlik YETMEZ (§54/§58)."""
    threshold = int(rule.config.get("threshold_hours") or 48)
    last = await last_meaningful_activity_at(session)
    if last is None:
        return []
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    gap_hours = (now - last).total_seconds() / 3600.0
    if gap_hours < threshold:
        return []

    facts = await _continuity_facts(session, now=now)
    if not facts:
        # Sessizlik tek basina bildirim sebebi DEGILDIR.
        return []
    day = local_now(now).date().isoformat()
    return [
        Candidate(
            rule_kind="continuity_gap",
            logical_trigger_key=f"continuity_gap:v1:{day}",
            category="continuity_comeback",
            why_now=f"{int(gap_hours)} saattir sayılan kullanıcı hareketi yok; {len(facts)} dikkat sinyali var",
            reason_codes=["CONTINUITY_GAP", "MEANINGFUL_STATE_CHANGED"],
            h5_mode="continuity",
        )
    ]


async def _morning_candidates(
    session: AsyncSession, rule: ProactivityRule, *, now: datetime
) -> list[Candidate]:
    """Sabah süreklilik ritüeli — anlamli bir sey yoksa SESSIZ (§42)."""
    if not _ritual_due(rule, now=now, default_time="08:05"):
        return []
    facts = await _continuity_facts(session, now=now)
    if not facts:
        return []
    day = local_now(now).date().isoformat()
    return [
        Candidate(
            rule_kind="morning_continuity",
            logical_trigger_key=f"morning_continuity:v1:{day}",
            category="ritual",
            why_now=f"sabah ritüeli {len(facts)} dikkat sinyali buldu",
            reason_codes=["RITUAL_DUE", "MEANINGFUL_STATE_CHANGED"],
            h5_mode="continuity",
        )
    ]


async def _daily_close_candidates(
    session: AsyncSession, rule: ProactivityRule, *, now: datetime
) -> list[Candidate]:
    """Gun kapanisi — temiz gun SESSIZ gecer (§61)."""
    if not _ritual_due(rule, now=now, default_time="21:00"):
        return []
    from app.integrations.review_intelligence import service as h5_svc

    response = await h5_svc.review_intelligence(session, mode="daily_close", now=now)
    payload = response.payload
    facts = [
        *payload.newly_overdue,
        *payload.upcoming,
        *payload.carry_forward_candidates,
    ]
    if not facts:
        return []
    day = local_now(now).date().isoformat()
    return [
        Candidate(
            rule_kind="daily_close",
            logical_trigger_key=f"daily_close:v1:{day}",
            category="ritual",
            why_now=f"gün kapanışı {len(facts)} açık uç buldu",
            reason_codes=["RITUAL_DUE", "MEANINGFUL_STATE_CHANGED"],
            h5_mode="daily_close",
        )
    ]


async def _weekly_candidates(
    session: AsyncSession, rule: ProactivityRule, *, now: datetime
) -> list[Candidate]:
    """Haftalik gozden gecirme — anlamli delta yoksa SESSIZ (§62)."""
    if not _weekly_due(rule, now=now):
        return []
    from app.integrations.review_intelligence import service as h5_svc

    response = await h5_svc.review_intelligence(session, mode="weekly_review", now=now)
    payload = response.payload
    facts = [
        *payload.time_sensitive_changes,
        *payload.stalled_projects,
        *payload.open_loops,
    ]
    if not facts:
        return []
    week = local_now(now).date().isocalendar()
    return [
        Candidate(
            rule_kind="weekly_review",
            logical_trigger_key=f"weekly_review:v1:{week.year}-W{week.week:02d}",
            category="ritual",
            why_now=f"haftalık gözden geçirme {len(facts)} çözülmemiş madde buldu",
            reason_codes=["RITUAL_DUE", "MEANINGFUL_STATE_CHANGED"],
            h5_mode="weekly_review",
        )
    ]


async def _project_stalled_candidates(
    session: AsyncSession, rule: ProactivityRule, *, now: datetime
) -> list[Candidate]:
    """Aktif ama kayitli hareketi olmayan projeler (§63).

    "Ihmal ediyorsun" DEGIL: "kayitli aktivite yok". Esik kullanici ayaridir;
    kaynak H5 ile aynidir (sayilan insan hareketi).
    """
    from app.modules.project.models import Project

    days_threshold = int(rule.config.get("days") or 14)
    cooldown_days = int(rule.config.get("cooldown_days") or 7)
    rows = (
        await session.execute(
            select(Project.id)
            .join(Entity, Entity.id == Project.id)
            .where(Project.status == "active")
            .order_by(Project.id.asc())
            .limit(MAX_STALLED_PROJECTS + 1)
        )
    ).all()
    project_ids = [project_id for (project_id,) in rows[:MAX_STALLED_PROJECTS]]
    if not project_ids:
        return []

    # "Proje hareketi" tanimi TEK yerde: H5'in kanonik okuyucusu (projeye
    # bagli gorevlerin hareketi de projenin hareketidir). Ikinci bir tanim
    # yazmak, ayni proje icin iki farkli "duragan" cevabi uretirdi.
    from app.integrations.review_intelligence.sources import project_last_activity

    activity = await project_last_activity(session, project_ids=project_ids)

    candidates: list[Candidate] = []
    for project_id in project_ids:
        last_at = activity.get(str(project_id))
        if last_at is None:
            # Hic kayitli hareket yok: yasi bilmiyoruz, "16 gundur" DEMEYIZ.
            continue
        if last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=UTC)
        inactive_days = (now - last_at).days
        if inactive_days < days_threshold:
            continue
        candidates.append(
            Candidate(
                rule_kind="project_stalled",
                logical_trigger_key=f"project_stalled:v1:{project_id}",
                category="project_stalled",
                why_now=f"projede {inactive_days} gündür kayıtlı anlamlı aktivite yok",
                reason_codes=["PROJECT_STALLED"],
                subject_type="project",
                subject_id=project_id,
                entity_id=project_id,
                one_shot=False,
                cooldown_hours=cooldown_days * 24,
                h5_mode="continuity",
            )
        )
    return candidates


# ---------------------------------------------------------------------------
# Ritüel penceresi
# ---------------------------------------------------------------------------


def _ritual_due(rule: ProactivityRule, *, now: datetime, default_time: str) -> bool:
    """Ritüel bugun icin geldi mi — ve hala makul pencerede miyiz?

    Misfire politikasi `run_once_if_still_relevant`: kacirilan tur, pencere
    icinde BIR KEZ telafi edilir; gun disina tasan tur tekrar oynatilmaz.
    """
    moment = local_now(now)
    configured = str(rule.config.get("time") or default_time)
    hour, minute = _parse_hhmm(configured, default_time)
    grace_hours = int(rule.config.get("grace_hours") or 4)
    scheduled = moment.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if moment < scheduled:
        return False
    return moment < scheduled + timedelta(hours=grace_hours)


def _weekly_due(rule: ProactivityRule, *, now: datetime) -> bool:
    """Haftalik ritüel: yapilandirilmis gun + saat + sinirli telafi penceresi."""
    moment = local_now(now)
    weekday = int(rule.config.get("weekday") or 6)  # 0=Pazartesi .. 6=Pazar
    if moment.weekday() != weekday:
        return False
    return _ritual_due(rule, now=now, default_time="18:00")


def _parse_hhmm(value: str, fallback: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = value.split(":", 1)
        hour, minute = int(hour_text), int(minute_text)
    except (ValueError, AttributeError):
        hour_text, minute_text = fallback.split(":", 1)
        hour, minute = int(hour_text), int(minute_text)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        hour_text, minute_text = fallback.split(":", 1)
        hour, minute = int(hour_text), int(minute_text)
    return hour, minute


# ---------------------------------------------------------------------------
# Degerlendirme dongusu
# ---------------------------------------------------------------------------


async def _strategy_candidates(session, rule, *, now):
    from app.modules.goal.strategy import overview

    read = await overview(session, days=30, now=now)
    candidates = []
    if read.warnings or read.alignment.warnings:
        return candidates
    for finding in read.findings:
        if finding.code not in {"OBJECTIVE_INACTIVE", "DEADLINE_WITHOUT_PROGRESS"}:
            continue
        subject = uuid.UUID(finding.entity_refs[0].split(":", 1)[1])
        if rule.scope_entity_id and rule.scope_entity_id != subject:
            continue
        candidates.append(
            Candidate(
                rule_kind="strategy_attention",
                logical_trigger_key=f"strategy_attention:v1:{subject}:{finding.code}",
                category="strategy_attention",
                why_now=finding.observed_facts,
                reason_codes=[finding.code],
                subject_type="goal",
                subject_id=subject,
                entity_id=subject,
                one_shot=False,
                cooldown_hours=int(rule.config.get("cooldown_days") or 30) * 24,
            )
        )
    return candidates[:MAX_TICK_CANDIDATES]


_EVALUATORS = {
    "deadline_staircase": _deadline_candidates,
    "continuity_gap": _continuity_gap_candidates,
    "morning_continuity": _morning_candidates,
    "daily_close": _daily_close_candidates,
    "weekly_review": _weekly_candidates,
    "project_stalled": _project_stalled_candidates,
    "strategy_attention": _strategy_candidates,
}


async def evaluate_rule(
    session: AsyncSession, rule: ProactivityRule, *, now: datetime
) -> list[Candidate]:
    evaluator = _EVALUATORS.get(rule.kind)
    if evaluator is None:
        return []
    return await evaluator(session, rule, now=now)


async def evaluate_all(
    session: AsyncSession, rules: list[ProactivityRule], *, now: datetime
) -> tuple[list[Candidate], list[RuleFailure]]:
    """Tum etkin kurallari IZOLE degerlendirir (§152).

    Bir kural cokse bile digerleri calisir; hata sinirli kodla raporlanir.
    """
    candidates: list[Candidate] = []
    failures: list[RuleFailure] = []
    for rule in rules:
        if not rule.enabled:
            continue
        try:
            produced = await evaluate_rule(session, rule, now=now)
        except Exception:  # noqa: BLE001 — kural izolasyonu bilinçli
            log.exception("proaktivite kurali coktu: %s", rule.kind)
            failures.append(RuleFailure(rule.kind, "RULE_EVALUATION_FAILED"))
            continue
        # Sozlesme kilidi: `None` ya da yanlis tip listeye GIREMEZ. Bir kural
        # bunu ihlal ederse sessizce yutulmaz; sinirli kodla raporlanir.
        invalid = [item for item in produced if not isinstance(item, Candidate)]
        if invalid:
            log.error("kural gecersiz aday uretti: %s (%d)", rule.kind, len(invalid))
            failures.append(RuleFailure(rule.kind, "INVALID_CANDIDATE"))
            produced = [item for item in produced if isinstance(item, Candidate)]
        candidates.extend(produced)
        if len(candidates) >= MAX_TICK_CANDIDATES:
            return candidates[:MAX_TICK_CANDIDATES], failures
    return candidates, failures


# ---------------------------------------------------------------------------
# Yeniden dogrulama (§131): teslim ONCESI guncel durum
# ---------------------------------------------------------------------------


async def revalidate(
    session: AsyncSession,
    *,
    rule: ProactivityRule,
    logical_trigger_key: str,
    now: datetime,
) -> IdentityStatus:
    """Kosul HALA gecerli mi? Uclu sonuc: found / not_found / indeterminate.

    Tetikleyici payload'una ASLA guvenilmez: ertelenen bir teslim, kosul
    ortadan kalktiysa iptal edilir (§48/§49). Kapsam belirsizse (`indeterminate`)
    ne teslim edilir ne cozulur: "goremedim" != "yok".
    """
    try:
        if rule.kind == "deadline_staircase":
            return await _revalidate_deadline(session, logical_trigger_key, now=now)
        if rule.kind == "strategy_attention":
            from app.modules.goal.strategy import overview

            read = await overview(session, days=30, now=now)
            if read.warnings or read.alignment.warnings:
                return "indeterminate"
            candidates = await _strategy_candidates(session, rule, now=now)
            return (
                "found"
                if any(c.logical_trigger_key == logical_trigger_key for c in candidates)
                else "not_found"
            )
        if rule.kind == "project_stalled":
            found = await _revalidate_project(session, logical_trigger_key, rule, now=now)
            return "found" if found else "not_found"
        if rule.kind == "continuity_gap":
            threshold = int(rule.config.get("threshold_hours") or 48)
            last = await last_meaningful_activity_at(session)
            if last is None:
                return "not_found"
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            gap = (now - last).total_seconds() / 3600.0
            alive = gap >= threshold and bool(await _continuity_facts(session, now=now))
            return "found" if alive else "not_found"
        if rule.kind in {"morning_continuity", "daily_close", "weekly_review"}:
            facts = await _ritual_facts(session, rule.kind, now=now)
            return "found" if facts else "not_found"
    except Exception:  # noqa: BLE001 — yeniden dogrulama basarisizsa teslim ETME
        log.exception("proaktivite yeniden dogrulamasi coktu: %s", rule.kind)
        return "indeterminate"
    return "found"


async def current_condition_row(session: AsyncSession, identity: str) -> dict | None:
    """Kosul kimligini GUNCEL kanonik satira cozer (H6.1) — bulunamazsa None.

    `first row where entity_id == subject` yaklasimi KULLANILMAZ: ayni entity
    uzerinde birden fazla bagimsiz son tarih oldugunda yanlis satiri secer.
    """
    status, row = await resolve_identity(session, identity)
    return row if status == "found" else None


async def _all_deadline_rows(session: AsyncSession) -> tuple[list[dict], bool]:
    """(satirlar, kirpildi_mi). Kirpilma bilgisi kimlik cozumlemesi icin SARTTIR.

    Kesif bounded kalir; ama "listedeye girmedi" != "artik yok".
    """
    from app.core.deadlines import collect_deadlines
    from app.modules.opportunity.service import pending_follow_up_rows

    rows = [*await collect_deadlines(session, limit=MAX_DEADLINE_ROWS + 1)]
    truncated = len(rows) > MAX_DEADLINE_ROWS
    rows = rows[:MAX_DEADLINE_ROWS]
    rows.extend(await pending_follow_up_rows(session))
    return rows, truncated


async def resolve_identity(
    session: AsyncSession, identity: str
) -> tuple[IdentityStatus, dict | None]:
    """Bilinen bir kosul kimligini TAM olarak cozer.

    Bulunamadiysa ve tarama KIRPILDIYSA `indeterminate` doner: kosul hala
    var olabilir, bu yuzden cagiran "cozuldu" karari VEREMEZ.
    """
    rows, truncated = await _all_deadline_rows(session)
    for row in rows:
        if condition_identity(row) == identity:
            return "found", row
    return ("indeterminate" if truncated else "not_found"), None


async def _revalidate_deadline(
    session: AsyncSession, logical_trigger_key: str, *, now: datetime
) -> IdentityStatus:
    identity = identity_of_key(logical_trigger_key)
    revision = revision_of_key(logical_trigger_key)
    if identity is None or revision is None:
        return "not_found"
    status, row = await resolve_identity(session, identity)
    if status != "found" or row is None:
        return status
    due = row.get("due_at")
    if due is None or due < now:
        return "not_found"
    # Kosul hala ayni revizyonda mi? Tarih (veya saat) degistiyse bu kosu bayat.
    return "found" if temporal_revision(due) == revision else "not_found"


async def _revalidate_project(
    session: AsyncSession, logical_trigger_key: str, rule: ProactivityRule, *, now: datetime
) -> bool:
    candidates = await _project_stalled_candidates(session, rule, now=now)
    return any(item.logical_trigger_key == logical_trigger_key for item in candidates)


async def _ritual_facts(session: AsyncSession, kind: str, *, now: datetime) -> list[object]:
    from app.integrations.review_intelligence import service as h5_svc

    if kind == "morning_continuity":
        return await _continuity_facts(session, now=now)
    if kind == "daily_close":
        response = await h5_svc.review_intelligence(session, mode="daily_close", now=now)
        payload = response.payload
        return [*payload.newly_overdue, *payload.upcoming, *payload.carry_forward_candidates]
    response = await h5_svc.review_intelligence(session, mode="weekly_review", now=now)
    payload = response.payload
    return [*payload.time_sensitive_changes, *payload.stalled_projects, *payload.open_loops]


async def _continuity_facts(session: AsyncSession, *, now: datetime) -> list[object]:
    """H5 süreklilikte ANLAMLI sayilan dikkat sinyalleri (deterministik mod)."""
    from app.integrations.review_intelligence import service as h5_svc

    response = await h5_svc.review_intelligence(session, mode="continuity", now=now)
    payload = response.payload
    return [
        *payload.attention_candidates,
        *payload.newly_overdue,
        *payload.upcoming_deadlines,
        *payload.passed_plans_still_open,
    ]


def utc_today(moment: datetime) -> date:
    return moment.astimezone(UTC).date()
