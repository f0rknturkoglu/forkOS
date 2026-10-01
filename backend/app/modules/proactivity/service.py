"""H6 orkestrasyon: tur dongusu, kosu yasam dongusu, konfigurasyon.

Tek kapi: `tick()`. Zamanlayici yalnizca onu cagirir; ritüeller, son tarihler
ve proje izleme AYRI APScheduler isleri DEGILDIR (§15/§170).

Akis (§200):

    kural degerlendirmesi -> aday
    -> mantiksal kosu kimligi (idempotent, DB'de tek)
    -> GUNCEL durum yeniden dogrulamasi
    -> saf politika karari
    -> sessiz / ertele / digest / yuzeye cikar / hazirla
    -> (gerekirse) H5 baglami TESLIM ANINDA
    -> yeniden dogrulama
    -> Notification
    -> kullanici override'i (snooze/dismiss)

Yazma disiplini (§17): tur basina yalnizca ANLAMLI gecisler yazilir; her
kural icin "degerlendirildi" satiri uretilmez.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.heartbeat import WORKER_HEARTBEAT_KEY
from app.core.models import Entity
from app.core.time import local_today
from app.modules.proactivity import delivery, policy, rules
from app.modules.proactivity.models import (
    ACTIVE_RUN_STATES,
    RULE_KINDS,
    RULE_VERSION,
    SCOPE_GLOBAL,
    ProactivityRule,
    ProactivityRun,
)
from app.modules.system.models import Setting

log = logging.getLogger("proactivity")

#: Ana anahtar ve genel ayarlar (kucuk global konfigurasyon, §27).
SETTING_ENABLED = "proactivity.enabled"
SETTING_QUIET_START = "proactivity.quiet_hours_start"
SETTING_QUIET_END = "proactivity.quiet_hours_end"
SETTING_FOCUS_DEFERRAL = "proactivity.focus_deferral_enabled"
SETTING_DIGEST_TIME = "proactivity.digest_time"

CONFIG_DEFAULTS: dict[str, object] = {
    SETTING_ENABLED: False,  # opt-in: H6 kullaniciyi KENDILIGINDEN durtmez (§28)
    SETTING_QUIET_START: "23:30",
    SETTING_QUIET_END: "08:30",
    SETTING_FOCUS_DEFERRAL: True,
    SETTING_DIGEST_TIME: "18:30",
}

#: Kural varsayilanlari: ac/kapa + KAPALI semali ayar alanlari.
RULE_DEFAULTS: dict[str, dict[str, object]] = {
    "morning_continuity": {"enabled": False, "time": "08:05", "grace_hours": 4},
    "daily_close": {"enabled": False, "time": "21:00", "grace_hours": 3},
    "weekly_review": {"enabled": False, "weekday": 6, "time": "18:00", "grace_hours": 24},
    "deadline_staircase": {"enabled": True},
    "continuity_gap": {"enabled": False, "threshold_hours": 48},
    "project_stalled": {"enabled": False, "days": 14, "cooldown_days": 7},
    "strategy_attention": {"enabled": False, "cooldown_days": 30},
}

#: Kural turune gore IZIN VERILEN ayar alanlari (serbest anahtar-deger YOK, §106).
RULE_CONFIG_FIELDS: dict[str, tuple[str, ...]] = {
    "morning_continuity": ("time", "grace_hours"),
    "daily_close": ("time", "grace_hours"),
    "weekly_review": ("weekday", "time", "grace_hours"),
    "deadline_staircase": (),
    "continuity_gap": ("threshold_hours",),
    "project_stalled": ("days", "cooldown_days"),
    "strategy_attention": ("cooldown_days",),
}

#: Sinirli tarih listesi: kosu gecmisi bu kadar gun tutulur (§92).
RUN_RETENTION_DAYS = 90
#: `history` en fazla bu kadar satir doner (§110).
MAX_HISTORY_RETURN = 50
#: Durum ciktisinda gosterilen son hata sayisi.
MAX_RECENT_FAILURES = 5


class ProactivityError(Exception):
    """Sinirli, model-okunur H6 hatasi."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass
class TickResult:
    evaluated: int = 0
    candidates: int = 0
    surfaced: int = 0
    digested: int = 0
    deferred: int = 0
    suppressed: int = 0
    cancelled: int = 0
    failed: list[str] = field(default_factory=list)

    @property
    def delivered(self) -> int:
        return self.surfaced + self.digested


# ---------------------------------------------------------------------------
# Konfigurasyon
# ---------------------------------------------------------------------------


async def _get_setting(session: AsyncSession, key: str) -> object:
    row = await session.get(Setting, key)
    if row is not None and row.value is not None:
        return row.value
    return CONFIG_DEFAULTS[key]


async def _set_setting(session: AsyncSession, key: str, value: object) -> None:
    row = await session.get(Setting, key)
    if row is None:
        session.add(Setting(key=key, value=value))
    else:
        row.value = value


def parse_hhmm(value: object, *, field_name: str) -> time:
    """`HH:MM` dogrulamasi — bozuk deger sessizce kirpilmaz (§177)."""
    text = str(value or "")
    parts = text.split(":")
    if len(parts) != 2 or not all(len(part) == 2 and part.isdigit() for part in parts):
        raise ProactivityError("INVALID_CONFIG", f"{field_name} 'HH:MM' olmali")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ProactivityError("INVALID_CONFIG", f"{field_name} gecersiz saat")
    return time(hour=hour, minute=minute)


async def load_config(session: AsyncSession) -> dict[str, object]:
    """Kayitli ayari okur; YAZMA yolu dogrular (§177), okuma yolu asla cokmez.

    Bozuk bir deger (elle DB'ye yazilmis olabilir) worker'i oldurmez: varsayilana
    donulur ve loglanir. Sessiz kirpma YOKTUR -- yazma tarafi hata dondurur.
    """
    defaults = CONFIG_DEFAULTS

    def _safe_hhmm(value: object, key: str) -> time:
        try:
            return parse_hhmm(value, field_name=key)
        except ProactivityError:
            log.warning("proaktivite ayari bozuk, varsayilana donuldu: %s", key)
            return parse_hhmm(defaults[key], field_name=key)

    return {
        "enabled": bool(await _get_setting(session, SETTING_ENABLED)),
        "quiet_hours": (
            _safe_hhmm(await _get_setting(session, SETTING_QUIET_START), SETTING_QUIET_START),
            _safe_hhmm(await _get_setting(session, SETTING_QUIET_END), SETTING_QUIET_END),
        ),
        "focus_deferral_enabled": bool(await _get_setting(session, SETTING_FOCUS_DEFERRAL)),
        "digest_time": _safe_hhmm(
            await _get_setting(session, SETTING_DIGEST_TIME), SETTING_DIGEST_TIME
        ),
    }


async def configure(
    session: AsyncSession,
    *,
    enabled: bool | None = None,
    quiet_hours_start: str | None = None,
    quiet_hours_end: str | None = None,
    focus_deferral_enabled: bool | None = None,
    digest_time: str | None = None,
) -> dict[str, object]:
    """Bilinen alanlari yazar; bilinmeyen anahtar KABUL EDILMEZ (§106)."""
    if enabled is not None:
        await _set_setting(session, SETTING_ENABLED, bool(enabled))
    if quiet_hours_start is not None:
        parse_hhmm(quiet_hours_start, field_name=SETTING_QUIET_START)
        await _set_setting(session, SETTING_QUIET_START, quiet_hours_start)
    if quiet_hours_end is not None:
        parse_hhmm(quiet_hours_end, field_name=SETTING_QUIET_END)
        await _set_setting(session, SETTING_QUIET_END, quiet_hours_end)
    if focus_deferral_enabled is not None:
        await _set_setting(session, SETTING_FOCUS_DEFERRAL, bool(focus_deferral_enabled))
    if digest_time is not None:
        parse_hhmm(digest_time, field_name=SETTING_DIGEST_TIME)
        await _set_setting(session, SETTING_DIGEST_TIME, digest_time)
    await session.flush()
    return await load_config(session)


# ---------------------------------------------------------------------------
# Kurallar
# ---------------------------------------------------------------------------


def rule_logical_key(kind: str, scope: str = SCOPE_GLOBAL) -> str:
    return f"{kind}:v{RULE_VERSION}:{scope}"


async def seed_rules(session: AsyncSession) -> None:
    """Varsayilan kurallari IDEMPOTENT yazar; her acilista cogalmaz (§21)."""
    for kind in RULE_KINDS:
        defaults = RULE_DEFAULTS[kind]
        config = {key: value for key, value in defaults.items() if key != "enabled"}
        statement = (
            pg_insert(ProactivityRule)
            .values(
                kind=kind,
                version=RULE_VERSION,
                logical_key=rule_logical_key(kind),
                enabled=bool(defaults["enabled"]),
                config=config,
            )
            .on_conflict_do_nothing(index_elements=[ProactivityRule.logical_key])
        )
        await session.execute(statement)
    await session.flush()


async def list_rules(session: AsyncSession) -> list[ProactivityRule]:
    return list(
        (
            await session.execute(
                select(ProactivityRule).order_by(
                    ProactivityRule.kind.asc(), ProactivityRule.id.asc()
                )
            )
        ).scalars()
    )


async def rule_set(
    session: AsyncSession,
    *,
    kind: str,
    enabled: bool | None = None,
    config: dict | None = None,
    scope_entity_id: uuid.UUID | None = None,
) -> ProactivityRule:
    """Bilinen bir kuralin ac/kapa ve esik ayarlarini yazar (§107)."""
    if kind not in RULE_KINDS:
        raise ProactivityError("UNKNOWN_RULE_KIND", f"bilinmeyen kural: {kind}")
    scope = str(scope_entity_id) if scope_entity_id is not None else SCOPE_GLOBAL
    key = rule_logical_key(kind, scope)
    rule = (
        await session.execute(select(ProactivityRule).where(ProactivityRule.logical_key == key))
    ).scalar_one_or_none()
    if rule is None:
        if scope_entity_id is not None:
            entity = await session.get(Entity, scope_entity_id)
            if entity is None:
                raise ProactivityError("INVALID_ENTITY_SCOPE", "kapsam entity'si bulunamadi")
        defaults = RULE_DEFAULTS[kind]
        rule = ProactivityRule(
            kind=kind,
            version=RULE_VERSION,
            logical_key=key,
            enabled=bool(defaults["enabled"]),
            scope_entity_id=scope_entity_id,
            config={k: v for k, v in defaults.items() if k != "enabled"},
        )
        session.add(rule)
        await session.flush()
    if enabled is not None:
        rule.enabled = bool(enabled)
        if not enabled:
            await cancel_pending(session, rule=rule, reason="RULE_DISABLED")
    if config:
        rule.config = validate_rule_config(kind, {**rule.config, **config})
    await session.flush()
    return rule


def validate_rule_config(kind: str, config: dict) -> dict:
    """KAPALI sema: bilinmeyen alan ve gecersiz deger reddedilir (§154)."""
    allowed = RULE_CONFIG_FIELDS.get(kind, ())
    unknown = set(config) - set(allowed)
    if unknown:
        raise ProactivityError("UNKNOWN_CONFIG_FIELD", f"bilinmeyen ayar alani: {sorted(unknown)}")
    cleaned: dict[str, object] = {}
    for key, value in config.items():
        if key in {"time", "digest_time"}:
            parse_hhmm(value, field_name=key)
            cleaned[key] = str(value)
        elif key == "weekday":
            weekday = int(value)
            if not 0 <= weekday <= 6:
                raise ProactivityError("INVALID_CONFIG", "weekday 0..6 olmali")
            cleaned[key] = weekday
        elif key == "threshold_hours":
            hours = int(value)
            if not 1 <= hours <= 720:
                raise ProactivityError("INVALID_CONFIG", "threshold_hours 1..720 olmali")
            cleaned[key] = hours
        elif key == "days":
            days = int(value)
            if not 1 <= days <= 365:
                raise ProactivityError("INVALID_CONFIG", "days 1..365 olmali")
            cleaned[key] = days
        elif key == "cooldown_days":
            cooldown = int(value)
            if not 1 <= cooldown <= 90:
                raise ProactivityError("INVALID_CONFIG", "cooldown_days 1..90 olmali")
            cleaned[key] = cooldown
        elif key == "grace_hours":
            grace = int(value)
            if not 1 <= grace <= 72:
                raise ProactivityError("INVALID_CONFIG", "grace_hours 1..72 olmali")
            cleaned[key] = grace
    return cleaned


# ---------------------------------------------------------------------------
# Kosu yasam dongusu
# ---------------------------------------------------------------------------


async def _claim_run(
    session: AsyncSession, *, rule: ProactivityRule, candidate: rules.Candidate, now: datetime
) -> ProactivityRun:
    """Mantiksal kosuyu IDEMPOTENT sahiplenir (§71/§161)."""
    await session.execute(
        pg_insert(ProactivityRun)
        .values(
            rule_id=rule.id,
            logical_trigger_key=candidate.logical_trigger_key,
            state="candidate",
            reason_codes=list(candidate.reason_codes),
            why_now=candidate.why_now,
            subject_type=candidate.subject_type,
            subject_id=candidate.subject_id,
            triggered_at=now,
        )
        .on_conflict_do_nothing(index_elements=[ProactivityRun.logical_trigger_key])
    )
    await session.flush()
    run = (
        await session.execute(
            select(ProactivityRun).where(
                ProactivityRun.logical_trigger_key == candidate.logical_trigger_key
            )
        )
    ).scalar_one()
    if run.state == "candidate":
        run.reason_codes = list(candidate.reason_codes)
        run.why_now = candidate.why_now
    if run.snoozed_until is None:
        inherited = await _inherited_snooze(session, rule=rule, key=run.logical_trigger_key)
        if inherited is not None and inherited > now:
            run.snoozed_until = inherited
    return run


async def _inherited_snooze(
    session: AsyncSession, *, rule: ProactivityRule, key: str
) -> datetime | None:
    """Kullanici override'i KOSUYA degil KOSULA verilir (§25).

    Ayni kosulun yeni basamagi (T-3 → T-1) snooze'u DELMEZ; ama ayni entity'nin
    BASKA bir son tarihi (or. gorusme) bu snooze'u DEVRALMAZ.
    """
    scope = _episode_scope(key)
    if scope is None:
        return None
    rows = (
        await session.execute(
            select(ProactivityRun.logical_trigger_key, ProactivityRun.snoozed_until)
            .where(
                ProactivityRun.rule_id == rule.id,
                ProactivityRun.snoozed_until.is_not(None),
            )
            .order_by(ProactivityRun.snoozed_until.desc())
        )
    ).all()
    for other_key, snoozed_until in rows:
        if other_key == key:
            continue
        if _episode_scope(other_key) != scope:
            continue
        return snoozed_until
    return None


async def cancel_pending(session: AsyncSession, *, rule: ProactivityRule, reason: str) -> int:
    """Kural kapatildi: bekleyen teslimler iptal edilir (§188)."""
    runs = list(
        (
            await session.execute(
                select(ProactivityRun).where(
                    ProactivityRun.rule_id == rule.id,
                    ProactivityRun.state.in_(sorted(ACTIVE_RUN_STATES)),
                )
            )
        ).scalars()
    )
    for run in runs:
        run.state = "cancelled"
        run.cancelled_at = datetime.now(UTC)
        run.reason_codes = [reason]
    return len(runs)


def _episode_scope(logical_trigger_key: str) -> str | None:
    """Bir kosunun ait oldugu KOSUL kimligi (stale/snooze kapsami icin).

    Son tarih kosularinda entity tek basina kapsam DEGILDIR: ayni firsatin
    ilan son tarihi, takip tarihi ve gorusmeleri ayri kosullardir.
    """
    return rules.identity_of_key(logical_trigger_key)


async def cancel_stale_episodes(
    session: AsyncSession, *, rule: ProactivityRule, keep_key: str
) -> int:
    """AYNI kosulun eski revizyonlari iptal edilir (§146).

    Kapsam kosul kimligidir: ayni entity'nin BASKA bir son tarihi (or. ilan
    son tarihi vs gorusme) bu iptalden ETKILENMEZ.
    """
    scope = _episode_scope(keep_key)
    if scope is None:
        return 0
    runs = list(
        (
            await session.execute(
                select(ProactivityRun).where(
                    ProactivityRun.rule_id == rule.id,
                    ProactivityRun.logical_trigger_key != keep_key,
                    ProactivityRun.state.in_(sorted(ACTIVE_RUN_STATES)),
                )
            )
        ).scalars()
    )
    stale = [
        run
        for run in runs
        if _episode_scope(run.logical_trigger_key) == scope
        and rules.revision_of_key(run.logical_trigger_key) != rules.revision_of_key(keep_key)
    ]
    for run in stale:
        run.state = "cancelled"
        run.cancelled_at = datetime.now(UTC)
        run.reason_codes = ["STALE_TRIGGER"]
    return len(stale)


async def resolve_run(session: AsyncSession, run: ProactivityRun, *, now: datetime) -> None:
    """Koşul ORTADAN KALKTI: kosu iptal edilir, gerekce kosu satirinda kalir.

    Bu, "kapatmak" degil "cozuldu" demektir; `resolved_at` yazilir ve bildirim
    URETILMEZ (§48/§140).
    """
    run.state = "resolved"
    run.resolved_at = now
    run.reason_codes = ["CONDITION_RESOLVED"]


# ---------------------------------------------------------------------------
# Tur
# ---------------------------------------------------------------------------


async def tick(
    session: AsyncSession, *, now: datetime | None = None, catch_up: bool = False
) -> TickResult:
    """Tek degerlendirme turu — zamanlayicinin cagirdigi TEK giris noktasi."""
    moment = now or datetime.now(UTC)
    result = TickResult()

    await seed_rules(session)
    config = await load_config(session)
    all_rules = await list_rules(session)
    result.evaluated = len(all_rules)

    if not config["enabled"]:
        # Ana anahtar kapali: hicbir H6 bildirimi cikmaz; bekleyenler tarihsel
        # kalir ve tekrar acildiginda GUNCEL durumla yeniden degerlendirilir.
        await session.commit()
        return result

    candidates, failures = await rules.evaluate_all(session, all_rules, now=moment)
    result.candidates = len(candidates)
    result.failed = [failure.rule_kind for failure in failures]
    for failure in failures:
        await _record_rule_failure(session, failure, now=moment)

    by_kind = {rule.kind: rule for rule in all_rules}
    for candidate in candidates:
        rule = by_kind.get(candidate.rule_kind)
        if rule is None:
            continue
        await _process_candidate(
            session, rule=rule, candidate=candidate, config=config, now=moment, result=result
        )

    await _flush_pending(session, rules_by_kind=by_kind, config=config, now=moment, result=result)
    await _flush_digest(session, rules_by_kind=by_kind, config=config, now=moment, result=result)
    await session.commit()
    return result


async def _process_candidate(
    session: AsyncSession,
    *,
    rule: ProactivityRule,
    candidate: rules.Candidate,
    config: dict[str, object],
    now: datetime,
    result: TickResult,
) -> None:
    run = await _claim_run(session, rule=rule, candidate=candidate, now=now)
    # Ayni KOSULUN eski revizyonlari iptal edilir (§146); kardes kosullar korunur.
    await cancel_stale_episodes(session, rule=rule, keep_key=run.logical_trigger_key)
    if run.state in {"resolved", "cancelled", "failed"}:
        return
    if candidate.one_shot and run.state in {"delivered", "dismissed", "suppressed"}:
        return

    # Kosul hala gecerli mi? Tetikleyici payload'una GUVENILMEZ.
    status = await rules.revalidate(
        session, rule=rule, logical_trigger_key=candidate.logical_trigger_key, now=now
    )
    if status == "not_found":
        if run.state in ACTIVE_RUN_STATES:
            await resolve_run(session, run, now=now)
            result.cancelled += 1
        return
    if status == "indeterminate":
        # Tarama siniri yuzunden goremedik: ne teslim ne cozum (§0.2).
        return

    if run.state == "snoozed" and run.snoozed_until is not None and run.snoozed_until <= now:
        # Snooze doldu: kosul GUNCEL durumla yeniden degerlendirilir (§144).
        run.state = "candidate"
    if not candidate.one_shot and run.state in {"delivered", "suppressed", "dismissed"}:
        # Tekrarlanabilir kosul: cooldown dolduysa yeniden aday olur (§73/§143).
        cooldown_hours = candidate.cooldown_hours or 0
        last = run.last_delivered_at or run.updated_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        if last is not None and last + timedelta(hours=cooldown_hours) > now:
            return
        run.state = "candidate"
        run.reason_codes = list(candidate.reason_codes)
        run.why_now = candidate.why_now

    run.evaluated_at = now
    decision = policy.decide(
        policy.PolicyInput(
            category=candidate.category,
            now=now,
            local_now=rules.local_now(now),
            master_enabled=bool(config["enabled"]),
            rule_enabled=rule.enabled,
            one_shot=candidate.one_shot,
            run_state=run.state,
            delivery_count=run.delivery_count,
            last_delivered_at=run.last_delivered_at,
            snoozed_until=run.snoozed_until or rule.snoozed_until,
            cooldown_hours=candidate.cooldown_hours,
            quiet_hours=config["quiet_hours"],  # type: ignore[arg-type]
            focus_active=await _focus_active(session),
            focus_deferral_enabled=bool(config["focus_deferral_enabled"]),
            immediate_surfaces_today=await _immediate_surfaces_today(session, now=now),
            why_now=candidate.why_now,
        )
    )

    if decision.outcome == "silent":
        if run.state in ACTIVE_RUN_STATES and decision.reason_codes[:1] != ["USER_SNOOZED"]:
            run.state = "suppressed"
            run.reason_codes = list(decision.reason_codes)
        result.suppressed += 1
        return

    if decision.outcome == "defer":
        run.state = "deferred"
        run.deferred_until = decision.earliest_delivery_at or (now + timedelta(minutes=30))
        run.reason_codes = list(decision.reason_codes)
        result.deferred += 1
        return

    if decision.outcome == "digest":
        # Sayim GERCEK digest tesliminde yapilir (`_flush_digest`): kuyruga
        # girmek teslim degildir.
        run.state = "digest_queued"
        run.reason_codes = list(decision.reason_codes)
        return

    # surface / prepare: H5 baglami TESLIM ANINDA kurulur.
    await _deliver_now(
        session, run=run, rule=rule, candidate=candidate, decision=decision, now=now, result=result
    )


#: Teslim edilebilir (henuz terminal olmayan) durumlar.
DELIVERABLE_RUN_STATES: frozenset[str] = frozenset(
    {"candidate", "deferred", "digest_queued", "suppressed", "snoozed"}
)


async def _lock_run(session: AsyncSession, run_id: int) -> ProactivityRun | None:
    """Kosuyu satir kilidiyle yeniden okur (H6 PART-0 concurrency guard).

    Worker turu ile elle/MCP degerlendirmesi AYRI PROCESS'lerde calisabilir;
    bu yuzden koruma process-local olamaz. `SELECT ... FOR UPDATE` ikinci
    transaction'i birincinin commit'ine kadar bekletir ve ardindan GUNCEL
    durumu gosterir. Bildirim dedup'i ikinci savunma hattidir; lifecycle
    dogrulugu yalniz ona bagli DEGILDIR.
    """
    return (
        await session.execute(
            select(ProactivityRun).where(ProactivityRun.id == run_id).with_for_update()
        )
    ).scalar_one_or_none()


async def _deliver_now(
    session: AsyncSession,
    *,
    run: ProactivityRun,
    rule: ProactivityRule,
    candidate: rules.Candidate,
    decision: policy.InterventionDecision,
    now: datetime,
    result: TickResult,
) -> None:
    # Yarisi kaybeden transaction burada bekler ve taze durumu gorur.
    locked = await _lock_run(session, run.id)
    if locked is None or locked.state not in DELIVERABLE_RUN_STATES:
        # Baska bir degerlendirme bu kosuyu zaten ilerletmis: GERIYE DUSURME YOK.
        return
    run = locked
    if run.state == "delivered":
        return
    status = await rules.revalidate(
        session, rule=rule, logical_trigger_key=run.logical_trigger_key, now=now
    )
    if status == "indeterminate":
        # Kapsam belirsiz: ne teslim et ne coz (fail-closed, §60).
        return
    if status == "not_found":
        await resolve_run(session, run, now=now)
        result.cancelled += 1
        return

    title, facts = await _compose(session, run=run, rule=rule, candidate=candidate, now=now)
    if not facts:
        # Anlamli icerik yok: sessizlik dogru cevaptir, bos bildirim degil.
        run.state = "suppressed"
        run.reason_codes = ["NO_MEANINGFUL_CONTENT"]
        result.suppressed += 1
        return

    notification_id = await delivery.deliver_run(
        session,
        run_id=run.id,
        logical_trigger_key=run.logical_trigger_key,
        delivery_count=run.delivery_count,
        title=title,
        facts=facts,
        importance=policy.importance_for(candidate.category),
        entity_id=run.subject_id,
        now=now,
    )
    if notification_id is None:
        # Bildirim zaten var: bu kosuyu BIR BASKASI teslim etti. Kosu durumunu
        # geriye dusurmeyiz; sahibi olan transaction karari vermistir.
        return
    run.state = "delivered"
    run.delivery_count += 1
    run.last_delivered_at = now
    run.notification_id = notification_id
    run.reason_codes = list(decision.reason_codes)
    result.surfaced += 1


# ---------------------------------------------------------------------------
# Bekleyen teslimler
# ---------------------------------------------------------------------------


async def _flush_pending(
    session: AsyncSession,
    *,
    rules_by_kind: dict[str, ProactivityRule],
    config: dict[str, object],
    now: datetime,
    result: TickResult,
) -> None:
    """Ertelenen kosular: pencere acilinca GUNCEL durumla teslim edilir (§83)."""
    pending = list(
        (
            await session.execute(
                select(ProactivityRun).where(
                    ProactivityRun.state.in_(("deferred", "snoozed")),
                    ProactivityRun.deferred_until.is_not(None),
                    ProactivityRun.deferred_until <= now,
                )
            )
        ).scalars()
    )
    for run in pending:
        rule = next((item for item in rules_by_kind.values() if item.id == run.rule_id), None)
        if rule is None:
            continue
        status = await rules.revalidate(
            session, rule=rule, logical_trigger_key=run.logical_trigger_key, now=now
        )
        if status == "indeterminate":
            continue
        if status == "not_found":
            await resolve_run(session, run, now=now)
            result.cancelled += 1
            continue
        decision = policy.decide(
            policy.PolicyInput(
                category=_category_for(rule, run),
                now=now,
                local_now=rules.local_now(now),
                master_enabled=bool(config["enabled"]),
                rule_enabled=rule.enabled,
                one_shot=True,
                run_state=run.state,
                delivery_count=run.delivery_count,
                last_delivered_at=run.last_delivered_at,
                snoozed_until=run.snoozed_until or rule.snoozed_until,
                quiet_hours=config["quiet_hours"],  # type: ignore[arg-type]
                focus_active=await _focus_active(session),
                focus_deferral_enabled=bool(config["focus_deferral_enabled"]),
                immediate_surfaces_today=await _immediate_surfaces_today(session, now=now),
                why_now=run.why_now,
            )
        )
        if decision.outcome in {"silent"}:
            # Snooze bir DURAKLAMADIR, son degil: kosu beklemede kalir ve
            # snooze bitince yeniden degerlendirilir (§25/§144).
            if decision.reason_codes[:1] != ["USER_SNOOZED"]:
                run.state = "suppressed"
            run.reason_codes = list(decision.reason_codes)
            result.suppressed += 1
            continue
        if decision.outcome == "defer":
            run.deferred_until = decision.earliest_delivery_at or (now + timedelta(minutes=30))
            run.reason_codes = list(decision.reason_codes)
            continue
        if decision.outcome == "digest":
            run.state = "digest_queued"
            run.reason_codes = list(decision.reason_codes)
            continue
        candidate = _candidate_for(rule, run)
        await _deliver_now(
            session,
            run=run,
            rule=rule,
            candidate=candidate,
            decision=decision,
            now=now,
            result=result,
        )


async def _flush_digest(
    session: AsyncSession,
    *,
    rules_by_kind: dict[str, ProactivityRule],
    config: dict[str, object],
    now: datetime,
    result: TickResult,
) -> None:
    """Digest: dusuk/orta dikkat adaylari TEK bildirime iner (§75)."""
    digest_time = config["digest_time"]
    local_moment = rules.local_now(now)
    assert isinstance(digest_time, time)
    if local_moment.time() < digest_time:
        return

    queued = list(
        (
            await session.execute(
                select(ProactivityRun)
                .where(ProactivityRun.state == "digest_queued")
                .order_by(ProactivityRun.triggered_at.asc(), ProactivityRun.id.asc())
            )
        ).scalars()
    )
    if not queued:
        return

    entries: list[delivery.DigestEntry] = []
    for run in queued:
        rule = next((item for item in rules_by_kind.values() if item.id == run.rule_id), None)
        if rule is None:
            continue
        # Uye bazli yeniden dogrulama: bayat madde digest'e GIRMEZ (§76).
        status = await rules.revalidate(
            session, rule=rule, logical_trigger_key=run.logical_trigger_key, now=now
        )
        if status == "indeterminate":
            continue
        if status == "not_found":
            await resolve_run(session, run, now=now)
            result.cancelled += 1
            continue
        title, facts = await _compose(
            session, run=run, rule=rule, candidate=_candidate_for(rule, run), now=now
        )
        if not facts:
            # Kanonik karsiligi kalmamis uye: bos madde YAZILMAZ ve "teslim
            # edildi" de DENMEZ; kosul cozulmus sayilir (§C2).
            run.state = "resolved"
            run.resolved_at = now
            run.reason_codes = ["NO_MEANINGFUL_CONTENT"]
            continue
        entries.append(delivery.DigestEntry(run_id=run.id, title=title, facts=facts))

    if not entries:
        return
    notification_id, delivered_ids = await delivery.deliver_digest(
        session, entries=entries, now=now
    )
    if notification_id is None or not delivered_ids:
        return
    # YALNIZCA bildirime gercekten giren uyeler teslim edildi sayilir; kalanlar
    # `digest_queued` kalir ve sonraki digest turunda kullaniciya ulasir.
    for run in queued:
        if run.id not in delivered_ids:
            continue
        run.state = "delivered"
        run.delivery_count += 1
        run.last_delivered_at = now
        run.notification_id = notification_id
    result.digested += 1


# ---------------------------------------------------------------------------
# Icerik kompozisyonu (teslim aninda, guncel veriyle)
# ---------------------------------------------------------------------------


async def _compose(
    session: AsyncSession,
    *,
    run: ProactivityRun,
    rule: ProactivityRule,
    candidate: rules.Candidate,
    now: datetime,
) -> tuple[str, list[str]]:
    """(baslik, olgular) — GUNCEL durumdan, en fazla 3 satir."""
    from app.integrations.review_intelligence import service as h5_svc

    if rule.kind == "deadline_staircase":
        identity = _episode_scope(run.logical_trigger_key)
        row = await rules.current_condition_row(session, identity) if identity is not None else None
        if row is None:
            return "", []
        due = row["due_at"]
        days = max((due - now).days, 0)
        title = str(row.get("title") or "Kayıt")
        return f"{title} — {days} gün kaldı", [f"{title} için son tarih {days} gün içinde"]

    if rule.kind == "strategy_attention":
        candidates = await rules._strategy_candidates(session, rule, now=now)
        matching = next(
            (c for c in candidates if c.logical_trigger_key == run.logical_trigger_key), None
        )
        return ("Stratejik inceleme", [matching.why_now]) if matching else ("", [])

    if rule.kind == "project_stalled":
        entity = await session.get(Entity, run.subject_id) if run.subject_id else None
        title = entity.title if entity else "Proje"
        return f"{title}: kayıtlı hareket yok", [run.why_now or "kayıtlı anlamlı aktivite yok"]

    mode = candidate.h5_mode or "continuity"
    response = await h5_svc.review_intelligence(session, mode=mode, now=now)
    payload = response.payload
    if mode == "continuity":
        facts = delivery.compose_facts(
            [
                *payload.attention_candidates,
                *payload.newly_overdue,
                *payload.upcoming_deadlines,
            ]
        )
        return "Nerede kalmıştın?", facts
    if mode == "daily_close":
        facts = delivery.compose_facts(
            [*payload.newly_overdue, *payload.upcoming, *payload.carry_forward_candidates]
        )
        return "Günü kapat", facts
    facts = delivery.compose_facts(
        [*payload.time_sensitive_changes, *payload.stalled_projects, *payload.open_loops]
    )
    return "Haftalık gözden geçirme", facts


def _category_for(rule: ProactivityRule, run: ProactivityRun) -> str:
    if rule.kind == "deadline_staircase":
        codes = run.reason_codes if isinstance(run.reason_codes, list) else []
        for code in codes:
            mapping = {
                "DEADLINE_TODAY": "deadline_today",
                "DEADLINE_1D": "deadline_tomorrow",
                "DEADLINE_3D": "deadline_soon",
                "DEADLINE_7D": "deadline_near",
                "DEADLINE_14D": "deadline_far",
                "DEADLINE_30D": "deadline_far",
            }
            if code in mapping:
                return mapping[code]
        return "deadline_far"
    if rule.kind == "strategy_attention":
        return "strategy_attention"
    if rule.kind == "project_stalled":
        return "project_stalled"
    if rule.kind == "continuity_gap":
        return "continuity_comeback"
    return "ritual"


def _candidate_for(rule: ProactivityRule, run: ProactivityRun) -> rules.Candidate:
    return rules.Candidate(
        rule_kind=rule.kind,
        logical_trigger_key=run.logical_trigger_key,
        category=_category_for(rule, run),
        why_now=run.why_now or "",
        reason_codes=list(run.reason_codes) if isinstance(run.reason_codes, list) else [],
        subject_type=run.subject_type,
        subject_id=run.subject_id,
        entity_id=run.subject_id,
        one_shot=rule.kind not in {"project_stalled", "strategy_attention"},
        cooldown_hours=int(rule.config.get("cooldown_days") or 7) * 24
        if rule.kind in {"project_stalled", "strategy_attention"}
        else None,
        h5_mode="continuity"
        if rule.kind in {"continuity_gap", "morning_continuity"}
        else rule.kind,
    )


# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------


async def _focus_active(session: AsyncSession) -> bool:
    """Kanonik odak durumu: YALNIZCA gercek `focus` oturumu (§34/§35).

    Mola (`short_break`/`long_break`) odak SAYILMAZ. Kanonik sorgu yoksa
    odak ertlemesi uygulanmaz — uydurma FOCUS_ACTIVE uretilmez.
    """
    from app.modules.pomodoro.models import PomodoroSession

    kind = (
        await session.execute(
            select(PomodoroSession.kind)
            .where(PomodoroSession.ended_at.is_(None))
            .order_by(PomodoroSession.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return kind == "focus"


async def _immediate_surfaces_today(session: AsyncSession, *, now: datetime) -> int:
    """Bugun kac ANLIK yuzey teslim edildi (butce muhasebesi, §120)."""
    from app.modules.proactivity.models import ProactivityRun as Run

    start = rules.local_now(now).replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = start.astimezone(UTC)
    return int(
        (
            await session.execute(
                select(func.count())
                .select_from(Run)
                .where(
                    Run.state == "delivered",
                    Run.last_delivered_at.is_not(None),
                    Run.last_delivered_at >= start_utc,
                    Run.logical_trigger_key.not_like("digest:%"),
                )
            )
        ).scalar_one()
    )


async def _record_rule_failure(
    session: AsyncSession, failure: rules.RuleFailure, *, now: datetime
) -> None:
    """Kural cokmesi KULLANICIYA bildirilmez; kosu gecmisinde gorunur (§152/§153)."""
    rule = (
        await session.execute(
            select(ProactivityRule).where(
                ProactivityRule.logical_key == rule_logical_key(failure.rule_kind)
            )
        )
    ).scalar_one_or_none()
    if rule is None:
        return
    key = f"rule_failure:v1:{failure.rule_kind}:{local_today(now).isoformat()}"
    await session.execute(
        pg_insert(ProactivityRun)
        .values(
            rule_id=rule.id,
            logical_trigger_key=key,
            state="failed",
            reason_codes=[failure.failure_code],
            failure_code=failure.failure_code,
            triggered_at=now,
            evaluated_at=now,
        )
        .on_conflict_do_nothing(index_elements=[ProactivityRun.logical_trigger_key])
    )


# ---------------------------------------------------------------------------
# Kontrol yuzeyi
# ---------------------------------------------------------------------------


async def status(session: AsyncSession, *, now: datetime | None = None) -> dict:
    """Sinirli durum ozeti (§105) — devasa gecmis dokumu DEGIL."""
    moment = now or datetime.now(UTC)
    await seed_rules(session)
    config = await load_config(session)
    all_rules = await list_rules(session)
    pending_deferred = int(
        (
            await session.execute(
                select(func.count())
                .select_from(ProactivityRun)
                .where(ProactivityRun.state == "deferred")
            )
        ).scalar_one()
    )
    pending_digest = int(
        (
            await session.execute(
                select(func.count())
                .select_from(ProactivityRun)
                .where(ProactivityRun.state == "digest_queued")
            )
        ).scalar_one()
    )
    delivered_today = await _immediate_surfaces_today(session, now=moment)
    heartbeat = await session.get(Setting, WORKER_HEARTBEAT_KEY)
    last_run_at = (
        await session.execute(select(func.max(ProactivityRun.updated_at)))
    ).scalar_one_or_none()
    failures = list(
        (
            await session.execute(
                select(ProactivityRun)
                .where(ProactivityRun.state == "failed")
                .order_by(ProactivityRun.triggered_at.desc())
                .limit(MAX_RECENT_FAILURES)
            )
        ).scalars()
    )
    return {
        "enabled": bool(config["enabled"]),
        "quiet_hours_start": config["quiet_hours"][0].strftime("%H:%M"),  # type: ignore[index]
        "quiet_hours_end": config["quiet_hours"][1].strftime("%H:%M"),  # type: ignore[index]
        "focus_deferral_enabled": bool(config["focus_deferral_enabled"]),
        "digest_time": config["digest_time"].strftime("%H:%M"),  # type: ignore[union-attr]
        "immediate_budget": policy.MAX_IMMEDIATE_SURFACES_PER_DAY,
        "immediate_surfaces_today": delivered_today,
        "pending_deferred": pending_deferred,
        "pending_digest": pending_digest,
        "worker_heartbeat": heartbeat.value if heartbeat else None,
        "last_run_at": last_run_at.isoformat() if last_run_at else None,
        "rules": [
            {
                "kind": rule.kind,
                "version": rule.version,
                "logical_key": rule.logical_key,
                "enabled": rule.enabled,
                "config": rule.config,
                "snoozed_until": rule.snoozed_until.isoformat() if rule.snoozed_until else None,
            }
            for rule in all_rules
        ],
        "recent_failures": [
            {
                "rule_kind": _rule_kind_for_id(all_rules, run.rule_id),
                "failure_code": run.failure_code,
                "at": run.triggered_at.isoformat(),
            }
            for run in failures
        ],
    }


def _rule_kind_for_id(all_rules: list[ProactivityRule], rule_id: int) -> str | None:
    return next((rule.kind for rule in all_rules if rule.id == rule_id), None)


async def history(session: AsyncSession, *, limit: int = MAX_HISTORY_RETURN) -> list[dict]:
    """Sinirli kosu gecmisi (§110) — hassas kaynak icerigi YOK."""
    bounded = max(1, min(int(limit), MAX_HISTORY_RETURN))
    all_rules = {rule.id: rule for rule in await list_rules(session)}
    rows = list(
        (
            await session.execute(
                select(ProactivityRun)
                .order_by(ProactivityRun.created_at.desc(), ProactivityRun.id.desc())
                .limit(bounded)
            )
        ).scalars()
    )
    return [
        {
            "id": run.id,
            "rule_kind": all_rules[run.rule_id].kind if run.rule_id in all_rules else None,
            "subject_type": run.subject_type,
            "subject_id": str(run.subject_id) if run.subject_id else None,
            "state": run.state,
            "reason_codes": run.reason_codes,
            "why_now": run.why_now,
            "triggered_at": run.triggered_at.isoformat(),
            "delivered_at": run.last_delivered_at.isoformat() if run.last_delivered_at else None,
            "delivery_count": run.delivery_count,
            "snoozed_until": run.snoozed_until.isoformat() if run.snoozed_until else None,
            "notification_id": run.notification_id,
            "failure_code": run.failure_code,
        }
        for run in rows
    ]


async def snooze(
    session: AsyncSession,
    *,
    until: datetime,
    run_id: int | None = None,
    kind: str | None = None,
    scope_entity_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> int:
    """Acik kullanici override'i: verilen ana kadar sus (§25/§108)."""
    moment = now or datetime.now(UTC)
    if until.tzinfo is None:
        raise ProactivityError("INVALID_SNOOZE", "snooze zamani saat dilimli olmali")
    if until <= moment:
        raise ProactivityError("INVALID_SNOOZE", "snooze gecmis bir zaman olamaz")
    if run_id is None and kind is None:
        raise ProactivityError("INVALID_SNOOZE", "run_id veya kural turu gerekli")

    if run_id is not None:
        run = await session.get(ProactivityRun, run_id)
        if run is None:
            raise ProactivityError("RUN_NOT_FOUND", "kosu bulunamadi")
        run.snoozed_until = until
        # `snoozed` AYRI bir durumdur: "cozuldu" ya da "kapatildi" DEGIL (§23/§25).
        if run.state in {"candidate", "deferred", "digest_queued", "suppressed", "delivered"}:
            run.state = "snoozed"
        await session.flush()
        return 1

    assert kind is not None
    if kind not in RULE_KINDS:
        raise ProactivityError("UNKNOWN_RULE_KIND", f"bilinmeyen kural: {kind}")
    rule = await rule_set(session, kind=kind, scope_entity_id=scope_entity_id)
    rule.snoozed_until = until
    await session.flush()
    return 1


async def unsnooze(
    session: AsyncSession,
    *,
    run_id: int | None = None,
    kind: str | None = None,
    scope_entity_id: uuid.UUID | None = None,
) -> int:
    """Override kaldirilir — bu HEMEN bildirim uretmez; sonraki tur karar verir."""
    if run_id is not None:
        run = await session.get(ProactivityRun, run_id)
        if run is None:
            raise ProactivityError("RUN_NOT_FOUND", "kosu bulunamadi")
        run.snoozed_until = None
        await session.flush()
        return 1
    if kind is None or kind not in RULE_KINDS:
        raise ProactivityError("UNKNOWN_RULE_KIND", "bilinmeyen kural turu")
    scope = str(scope_entity_id) if scope_entity_id is not None else SCOPE_GLOBAL
    rule = (
        await session.execute(
            select(ProactivityRule).where(
                ProactivityRule.logical_key == rule_logical_key(kind, scope)
            )
        )
    ).scalar_one_or_none()
    if rule is None:
        return 0
    rule.snoozed_until = None
    await session.flush()
    return 1


async def dismiss_for_notification(
    session: AsyncSession, *, notification_id: int, now: datetime | None = None
) -> int:
    """Bildirim kapatildi -> bagli kosu da kapandi sayilir (§185/§186).

    Kapatmak COZMEK DEGILDIR: kosul suruyorsa kosu terminal duruma gecer ama
    `resolved_at` YAZILMAZ.
    """
    moment = now or datetime.now(UTC)
    runs = list(
        (
            await session.execute(
                select(ProactivityRun).where(ProactivityRun.notification_id == notification_id)
            )
        ).scalars()
    )
    for run in runs:
        # Kapatmak COZMEK DEGILDIR: durum `dismissed`, `resolved_at` YAZILMAZ.
        if run.state in {"delivered", "suppressed", "snoozed", "deferred", "digest_queued"}:
            run.state = "dismissed"
            run.evaluated_at = moment
    return len(runs)


async def prune_runs(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Kosu gecmisi budamasi — operasyonel saklama politikasina DEVREDER.

    Ayri bir H6 temizlik zamanlayicisi YOKTUR; mevcut gunluk bakim adimi
    `core.retention` uzerinden budar (§92).
    """
    from app.core.retention import prune_proactivity_runs

    return await prune_proactivity_runs(session, now=now)
