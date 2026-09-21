"""Kaynak kosum kaydi (source_run).

Kural 6: her scraper/feed kosusu buraya yazar. Ust uste 3 'empty' -> bildirim.
"Sessiz olum" (feed hala 200 donuyor ama artik item uretmiyor) tek yakalama noktasi burasi.
"""
from __future__ import annotations

import asyncio
import json
import re
import socket
import ssl
from datetime import UTC, datetime, timedelta

from sqlalchemy import Text, cast, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.core.models import Entity, SourceRun

EMPTY_STREAK_ALERT = 3      # ust uste bu kadar bos kosum -> bildirim
ERROR_STREAK_ALERT = 3      # ust uste bu kadar hata kosumu -> bildirim
OK = "ok"                   # complete: kaynagin hedeflenen kapsami tamamen tarandi
PARTIAL = "partial"         # bazi gecerli kayitlar alindi, kapsam tam degil
EMPTY = "empty"
ERROR = "error"
ABANDONED = "abandoned"

#: Kapanma taramasi (sweep) YALNIZCA bu durumda guvenlidir: kaynak hedefledigi
#: kapsami tamamen taradi. `partial`/`empty`/`error` kosusunda eksik gorunen
#: kayitlar gercekte var olabilir; onlari kapatmak veri kaybidir.
SWEEPABLE_STATUS = OK

#: Hata siniflari. `source_run.error_kind` kolonu (bkz. rapor) ya da error
#: metninin `[kind]` oneki ile tasinir; ikisi de ayni degerleri kullanir.
ERROR_KINDS = (
    "tls",
    "dns",
    "timeout",
    "http_403",
    "http_404",
    "http_429",
    "http_5xx",
    "parser",
    "partial",
    "circuit_open",
    "unknown",
)

#: Bu siniflar tekrar denemeye deger; digerleri kalici.
RETRYABLE_KINDS = frozenset({"timeout", "dns", "http_429", "http_5xx", "unknown"})

CIRCUIT_FAILURE_THRESHOLD = 5
CIRCUIT_COOLDOWN = timedelta(minutes=30)

# ---------------------------------------------------------------------------
# Hata metni guvenligi
# ---------------------------------------------------------------------------

#: URL userinfo'su: http://kullanici:sifre@host -> sifre gizlenir.
_URL_CREDENTIALS = re.compile(r"(?i)\b([a-z][a-z0-9+.\-]*://)([^/@\s]+)@")
#: Sir tasiyan sorgu parametreleri.
_SECRET_QUERY = re.compile(
    r"(?i)([?&](?:access[_-]?token|api[_-]?key|apikey|auth|authorization|credential"
    r"|key|password|passwd|pwd|secret|sig|signature|token)=)[^&\s\"'#]+"
)
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9\-._~+/=]+")
_KIND_PREFIX = re.compile(r"^\[([a-z0-9_]+)\]\s*")


def _mask_userinfo(match: re.Match[str]) -> str:
    scheme, userinfo = match.group(1), match.group(2)
    user = userinfo.split(":", 1)[0]
    return f"{scheme}{user}:***@"


def sanitize_error(message: str | None) -> str:
    """Hata metninden sir/parola/token temizle. ASLA TLS dogrulamasini kapatma.

    Proxy ve API URL'leri kullanici:parola ve ?token=... tasiyabilir; bunlar
    notification/event/UI'ya sizarsa geri alinamaz. Metin kisaltilmaz --
    `finish_run` zaten 2000 karakterle kirpar.
    """
    text = str(message or "")
    if not text:
        return ""
    text = _URL_CREDENTIALS.sub(_mask_userinfo, text)
    text = _SECRET_QUERY.sub(r"\1***", text)
    text = _BEARER.sub(r"\1 ***", text)
    return text


# ---------------------------------------------------------------------------
# Hata siniflandirma
# ---------------------------------------------------------------------------


def classify_error(exc: BaseException | str | None) -> str:
    """Bir hatayi `ERROR_KINDS` icinden tek bir degere indirger."""
    if exc is None:
        return "unknown"
    text = exc if isinstance(exc, str) else f"{type(exc).__name__}: {exc}"
    low = text.lower()

    if isinstance(exc, ssl.SSLError) or "ssl" in low or "certificate verify" in low:
        return "tls"
    if isinstance(exc, socket.gaierror) or any(
        marker in low
        for marker in (
            "nameresolutionerror",
            "getaddrinfo",
            "name or service not known",
            "nodename nor servname",
            "temporary failure in name resolution",
        )
    ):
        return "dns"
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or "timeout" in low or "timed out" in low:
        return "timeout"

    code = _status_code(exc, low)
    if code == 403:
        return "http_403"
    if code in (404, 410):
        return "http_404"
    if code == 429:
        return "http_429"
    if code is not None and code >= 500:
        return "http_5xx"
    if isinstance(exc, (json.JSONDecodeError, UnicodeDecodeError)):
        return "parser"
    if any(marker in low for marker in ("parse", "selector", "jsondecode", "html", "lxml", "selectolax")):
        return "parser"
    return "unknown"


def _status_code(exc: BaseException | str | None, low: str) -> int | None:
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    if isinstance(code, int):
        return code
    match = re.search(r"\bhttp[\s_]+(\d{3})\b", low)
    if match:
        return int(match.group(1))
    return None


def is_retryable(kind: str) -> bool:
    return kind in RETRYABLE_KINDS


def error_kind_of(run: SourceRun) -> str | None:
    """Kosumun hata sinifi: kolon varsa oradan, yoksa `[kind]` onekinden."""
    kind = getattr(run, "error_kind", None)
    if kind:
        return str(kind)
    match = _KIND_PREFIX.match(str(getattr(run, "error", "") or ""))
    return match.group(1) if match else None


def error_message_of(run: SourceRun) -> str | None:
    """Sir temizlenmis hata metni; degistirilmemis metinde `[kind]` oneki kalir.

    `finish_run` metni YAZARKEN temizler, ama `source_run.error` kolonuna
    yazan tek yol o degildir (media senkronu ham istisna metnini yazar) ve
    eski satirlar temizlikten once uretilmis olabilir. Bu yuzden temizlik
    OKUMA aninda da tekrarlanir: `sanitize_error` idempotenttir, ayni metni
    ikinci kez gecirmek ciktiyi degistirmez. API yuzeyleri (health/runs/
    coverage) ham metni asla disari vermez.
    """
    return sanitize_error(getattr(run, "error", None)) or None


# ---------------------------------------------------------------------------
# Kosum yazimi
# ---------------------------------------------------------------------------


async def start_run(
    session: AsyncSession, source: str, *, batch_id=None
) -> SourceRun:
    if batch_id is not None:
        reserved = (
            await session.execute(
                select(SourceRun)
                .where(
                    SourceRun.source == source,
                    SourceRun.batch_id == batch_id,
                    SourceRun.status == "running",
                )
                .order_by(SourceRun.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if reserved is not None:
            return reserved
    run = SourceRun(source=source, status="running", batch_id=batch_id)
    session.add(run)
    await session.flush()
    return run


async def finish_run(
    session: AsyncSession, run: SourceRun, *,
    status: str, items_found: int = 0, items_seen: int | None = None,
    error: str | None = None,
    error_kind: str | None = None,
) -> None:
    run.status = status
    run.items_found = items_found
    if items_seen is not None:
        run.items_seen = items_seen
    message = sanitize_error(error)
    kind = error_kind or (classify_error(message) if message else None)
    # `error_kind` kolonu modelde varsa ayri tasinir; yoksa metnin onekine
    # gomulur ki API/health onu yine de gosterebilsin (bkz. rapor: DDL istegi).
    if hasattr(run, "error_kind"):
        run.error_kind = kind
        run.error = message[:2000] or None
    else:
        run.error = (f"[{kind}] {message}"[:2000] if message and kind else (message[:2000] or None))
    run.finished_at = datetime.now(UTC)


async def has_live_claim(
    session: AsyncSession,
    source: str,
    *,
    exclude_run_id: int,
    lease: timedelta,
    now: datetime | None = None,
) -> bool:
    """Ayni kaynak icin su an yasiyan baska bir kosum var mi?

    Lease penceresi kaynak sinifinin sert timeout'u kadardir; canli bir
    kosumun bu pencereden uzun surmesi mumkun degildir (wait_for keser).
    """
    moment = now or datetime.now(UTC)
    row = (
        await session.execute(
            select(SourceRun.id)
            .where(
                SourceRun.source == source,
                SourceRun.status == "running",
                SourceRun.id != exclude_run_id,
                SourceRun.started_at > moment - lease,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return row is not None


async def last_statuses(session: AsyncSession, source: str, limit: int) -> list[str]:
    return list((await session.execute(
        select(SourceRun.status)
        .where(SourceRun.source == source, SourceRun.status != "running")
        .order_by(SourceRun.started_at.desc())
        .limit(limit)
    )).scalars())


async def previous_seen_count(
    session: AsyncSession, source: str, *, exclude_run_id: int, status: str = OK
) -> int | None:
    """Ayni kaynagin onceki `status` kosumunda kac kayit gorulmustu?

    Kapsam karsilastirmasinin tabani budur: yeni kosu tabanin yarisindan azi
    gorduyse kaynak daralmis (sayfalama/feed bozulmus) demektir ve kapanma
    taramasi yapilmaz.
    """
    return (
        await session.execute(
            select(SourceRun.items_seen)
            .where(
                SourceRun.source == source,
                SourceRun.status == status,
                SourceRun.id != exclude_run_id,
            )
            .order_by(SourceRun.started_at.desc(), SourceRun.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _fresh_streak(session: AsyncSession, source: str, *, status: str, streak: int) -> bool:
    """Son `streak` kosum tam olarak `status` mi, ve bu seri YENI mi?

    Ayni serinin 4., 5. kosumlarinda tekrar bildirim spam'i yapmamak icin
    bir onceki pencereye de bakilir: seri zaten tamamlanmissa alarm atilmaz.
    """
    statuses = await last_statuses(session, source, streak + 1)
    if len(statuses) < streak or any(item != status for item in statuses[:streak]):
        return False
    return not (len(statuses) > streak and all(item == status for item in statuses[1 : streak + 1]))


async def check_stalled(session: AsyncSession, source: str, *, label: str = "") -> bool:
    """Son N kosum bos mu? Oyleyse bildirim ve event uretir (Kural 6).

    Ust uste 3 empty -> bildirim. Sessiz olum kabul edilemez.
    Ayni bos serinin 4., 5. kosumlarinda tekrar bildirim spam'i yapmaz.
    """
    if not await _fresh_streak(session, source, status=EMPTY, streak=EMPTY_STREAK_ALERT):
        return False

    display = label or source
    message = f"{display}: üst üste {EMPTY_STREAK_ALERT} koşum boş döndü"
    await log_event(
        session,
        verb="source.stalled",
        payload={"source": source, "label": label, "streak": EMPTY_STREAK_ALERT, "message": message},
    )

    from app.core.notifications import notify
    from app.core.time import local_today

    today_str = local_today().isoformat()
    dedup_key = f"source_stalled:{source}:{today_str}"
    await notify(
        session,
        kind="source_stalled",
        title=f"Kaynak duraksadı: {display}",
        body=f"{display} kaynağı üst üste {EMPTY_STREAK_ALERT} kez boş döndü. Kaynak ölmüş veya sayfa yapısı değişmiş olabilir.",
        dedup_key=dedup_key,
        importance=2,
    )
    return True


async def check_failing(
    session: AsyncSession, source: str, *, label: str = "", error_kind: str | None = None
) -> bool:
    """Ust uste hata veren kaynak icin bildirim uretir.

    Bos kosumdan farki: kaynak aga hic cikamiyor ya da cevabi ayristirilamiyor.
    Ayirt edilmezse "empty" alarmi yanlis teshis koydurur (kaynak olmus degil,
    erisilemiyor olabilir). Hata sinifi bildirime tasinir.
    """
    if not await _fresh_streak(session, source, status=ERROR, streak=ERROR_STREAK_ALERT):
        return False

    display = label or source
    detail = f" (son hata türü: {error_kind})" if error_kind else ""
    message = f"{display}: üst üste {ERROR_STREAK_ALERT} koşum hata verdi{detail}"
    await log_event(
        session,
        verb="source.failing",
        payload={
            "source": source,
            "label": label,
            "streak": ERROR_STREAK_ALERT,
            "error_kind": error_kind,
            "message": message,
        },
    )

    from app.core.notifications import notify
    from app.core.time import local_today

    today_str = local_today().isoformat()
    await notify(
        session,
        kind="source_failing",
        title=f"Kaynak erişilemiyor: {display}",
        body=(
            f"{display} kaynağı üst üste {ERROR_STREAK_ALERT} kez hata verdi{detail}. "
            "Site erişilemiyor veya ayrıştırıcı bozulmuş olabilir; kaynak devre kesiciyle geçici olarak atlanır."
        ),
        dedup_key=f"source_failing:{source}:{today_str}",
        importance=2,
    )
    return True


async def check_source_health(
    session: AsyncSession, source: str, *, status: str, label: str = "", error_kind: str | None = None
) -> bool:
    """Kosum sonucuna uygun saglik alarmini uretir; `partial` sessizdir.

    `partial` bir alarm degildir: kaynak calisiyor, yalnizca kapsami eksik.
    Kapsam eksikligi zaten kosumun `status`'unde ve detayinda gorunur.
    """
    if status == EMPTY:
        return await check_stalled(session, source, label=label)
    if status == ERROR:
        return await check_failing(session, source, label=label, error_kind=error_kind)
    return False


# ---------------------------------------------------------------------------
# Circuit breaker (devre kesici) -- source_run gecmisinden turetilir
# ---------------------------------------------------------------------------


async def circuit_states(
    session: AsyncSession,
    sources: list[str],
    *,
    threshold: int = CIRCUIT_FAILURE_THRESHOLD,
    cooldown: timedelta = CIRCUIT_COOLDOWN,
    now: datetime | None = None,
) -> dict[str, dict]:
    """Her kaynak icin ardisik hata sayisi ve devre durumu (tek sorgu).

    Devre, ardisik `threshold` hata sonrasi ve son hatadan bu yana `cooldown`
    gecmemisse ACIKTIR; o sure boyunca kaynak aga hic cikmadan atlanir.
    """
    moment = now or datetime.now(UTC)
    result = {source: {"open": False, "consecutive_failures": 0, "retry_at": None} for source in sources}
    if not sources:
        return result

    ranked = (
        select(
            SourceRun.source.label("source"),
            SourceRun.status.label("status"),
            SourceRun.started_at.label("started_at"),
            SourceRun.finished_at.label("finished_at"),
            func.row_number()
            .over(
                partition_by=SourceRun.source,
                order_by=(SourceRun.started_at.desc(), SourceRun.id.desc()),
            )
            .label("rn"),
        )
        .where(SourceRun.source.in_(list(sources)), SourceRun.status != "running")
        .subquery()
    )
    rows = (await session.execute(select(ranked).where(ranked.c.rn <= max(threshold, 1)))).all()
    grouped: dict[str, list] = {}
    for row in rows:
        grouped.setdefault(row.source, []).append(row)

    for source in sources:
        consecutive = 0
        last_error_at: datetime | None = None
        for row in grouped.get(source, []):  # en yeniden en eskiye
            if row.status != ERROR:
                break
            consecutive += 1
            if last_error_at is None:
                last_error_at = row.finished_at or row.started_at
        retry_at = (last_error_at + cooldown) if last_error_at else None
        open_ = (
            consecutive >= threshold
            and last_error_at is not None
            and (moment - last_error_at) < cooldown
        )
        result[source] = {
            "open": open_,
            "consecutive_failures": consecutive,
            "retry_at": retry_at if open_ else None,
        }
    return result


async def circuit_state(
    session: AsyncSession,
    source: str,
    *,
    threshold: int = CIRCUIT_FAILURE_THRESHOLD,
    cooldown: timedelta = CIRCUIT_COOLDOWN,
    now: datetime | None = None,
) -> dict:
    return (await circuit_states(
        session, [source], threshold=threshold, cooldown=cooldown, now=now
    ))[source]


async def health(
    session: AsyncSession, limit: int = 50, *, active_only: bool = True
) -> list[dict]:
    """Her kaynagin son durumu -- Settings/Today icin ozet."""
    active_source = or_(
        SourceRun.source.not_like("rss:%"),
        exists(
            select(Entity.id).where(
                Entity.type == "feed",
                Entity.archived_at.is_(None),
                cast(Entity.id, Text) == func.substr(SourceRun.source, 5),
            )
        ),
    )
    newest_conditions = [SourceRun.status != "running"]
    if active_only:
        newest_conditions.append(active_source)
    newest = (
        select(SourceRun.source, func.max(SourceRun.started_at).label("last_at"))
        .where(*newest_conditions)
        .group_by(SourceRun.source)
        .subquery()
    )
    rows = list((await session.execute(
        select(SourceRun)
        .join(newest, (SourceRun.source == newest.c.source)
              & (SourceRun.started_at == newest.c.last_at))
        .order_by(SourceRun.started_at.desc())
        .limit(limit)
    )).scalars())
    states = await circuit_states(session, [r.source for r in rows])
    return [
        {"source": r.source, "status": r.status, "items_found": r.items_found,
         "error": error_message_of(r), "error_kind": error_kind_of(r),
         "circuit_open": states.get(r.source, {}).get("open", False),
         "consecutive_failures": states.get(r.source, {}).get("consecutive_failures", 0),
         # Devre kapaliyken null; acikken aga tekrar cikilacagi an. Ek sorgu
         # YOK: `circuit_states` bu degeri zaten hesapliyor.
         "retry_at": states.get(r.source, {}).get("retry_at"),
         "started_at": r.started_at, "finished_at": r.finished_at}
        for r in rows
    ]
