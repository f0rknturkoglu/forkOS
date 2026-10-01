"""H6 karar politikasi — SAF, deterministik, veritabani ve model cagrisi YOK.

Bu dosya "simdi kullaniciya dokunmali miyiz?" sorusunun TEK cevabidir.
Girdi: aday + mevcut durum + konfigurasyon + kosu gecmisi. Cikti:
`InterventionDecision`. Ayni girdi HER ZAMAN ayni karari verir.

Opak puan YOKTUR: ne "aciliyet olasiligi" ne "AI skoru". Karar kategorik
esiklerle ve sinirli gerekce kodlariyla aciklanir. Model (H4) bu karara
KARISMAZ; H6 v1'de "dokunayim mi?" sorusunu model cevaplamaz.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

# ---------------------------------------------------------------------------
# Sonuclar ve gerekce kodlari
# ---------------------------------------------------------------------------

#: Sessizlik birincil siniftir: "yapacak bir sey yok" BASARIDIR.
OUTCOMES: tuple[str, ...] = ("silent", "defer", "digest", "surface", "prepare")

#: Sinirli gerekce sozlugu. Yeni kod eklemek bilincli bir karardir.
REASON_CODES: tuple[str, ...] = (
    "PROACTIVITY_DISABLED",
    "RULE_DISABLED",
    "QUIET_HOURS",
    "FOCUS_ACTIVE",
    "USER_SNOOZED",
    "RECENTLY_SURFACED",
    "DUPLICATE_TRIGGER",
    "CONDITION_RESOLVED",
    "DEADLINE_TODAY",
    "DEADLINE_1D",
    "DEADLINE_3D",
    "DEADLINE_7D",
    "DEADLINE_14D",
    "DEADLINE_30D",
    "CONTINUITY_GAP",
    "MEANINGFUL_STATE_CHANGED",
    "PROJECT_STALLED",
    "DIGEST_ELIGIBLE",
    "RITUAL_DUE",
    "IMMEDIATE_BUDGET_EXHAUSTED",
    "NO_MEANINGFUL_CONTENT",
    "STALE_TRIGGER",
)

# ---------------------------------------------------------------------------
# Kategoriler -> teslim politikasi (§122/§123)
# ---------------------------------------------------------------------------

#: Kategorik oncelik. Ondalik skor YOK: kategori ya vardir ya yoktur.
CATEGORY_OUTCOMES: dict[str, str] = {
    # Son tarih: yakin olan hemen, uzak olan sindirilir.
    "deadline_today": "surface",
    "deadline_tomorrow": "surface",
    "deadline_soon": "surface",
    "deadline_near": "digest",
    "deadline_far": "digest",
    # Sureklilik donusu: once GUNCEL H5 baglami kurulur, sonra teslim edilir.
    "continuity_comeback": "prepare",
    # Ritüeller: anlamli bir sey varsa kisa ve net yuzey.
    "ritual": "surface",
    "project_stalled": "digest",
    "strategy_attention": "digest",
}

#: Odak aktifken ERTELENMEYEN kategoriler. Bunlar da sessiz/snooze/kuiet
#: kurallarini ATLAYAMAZ; yalnizca odak ertelemesinden muaftir.
FOCUS_CRITICAL_CATEGORIES: frozenset[str] = frozenset({"deadline_today", "deadline_tomorrow"})

#: Bildirim onemi (1..3) — mevcut bildirim olcegiyle ayni.
CATEGORY_IMPORTANCE: dict[str, int] = {
    "deadline_today": 3,
    "deadline_tomorrow": 3,
    "deadline_soon": 2,
    "continuity_comeback": 2,
    "ritual": 2,
    "deadline_near": 1,
    "deadline_far": 1,
    "project_stalled": 1,
    "strategy_attention": 1,
}

#: Gunluk ANLIK yuzey butcesi (§120). Asildiginda aday kaybolmaz: digest'e duser.
MAX_IMMEDIATE_SURFACES_PER_DAY = 3


@dataclass(frozen=True)
class InterventionDecision:
    """Karar — gerekceli, tekrar uretilebilir, opak puan icermez."""

    outcome: str
    reason_codes: list[str] = field(default_factory=list)
    why_now: str | None = None
    earliest_delivery_at: datetime | None = None
    requires_revalidation: bool = True


@dataclass(frozen=True)
class PolicyInput:
    """Politikanin TUM girdisi — saf fonksiyon icin acikca tasinir."""

    category: str
    now: datetime
    #: Yerel saat diliminde "simdi" (kuiet saatleri ve ritüel pencereleri icin).
    local_now: datetime
    master_enabled: bool
    rule_enabled: bool
    one_shot: bool
    run_state: str
    delivery_count: int
    last_delivered_at: datetime | None = None
    snoozed_until: datetime | None = None
    cooldown_hours: int | None = None
    quiet_hours: tuple[time, time] | None = None
    focus_active: bool = False
    focus_deferral_enabled: bool = True
    immediate_surfaces_today: int = 0
    immediate_budget: int = MAX_IMMEDIATE_SURFACES_PER_DAY
    why_now: str | None = None


# ---------------------------------------------------------------------------
# Kuiyet saatleri
# ---------------------------------------------------------------------------


def in_quiet_hours(local_now: time, start: time, end: time) -> bool:
    """Kuiyet penceresi — gece yarisini ASAN aralik desteklenir (23:30→08:30)."""
    if start == end:
        return False
    if start < end:
        return start <= local_now < end
    return local_now >= start or local_now < end


def quiet_hours_end(local_now: datetime, start: time, end: time) -> datetime:
    """Kuiyetin bitecegi an (yerel saat diliminde, saat dilimli)."""
    candidate = local_now.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
    if in_quiet_hours(local_now.timetz().replace(tzinfo=None), start, end):
        if candidate <= local_now:
            candidate += timedelta(days=1)
        return candidate
    return local_now


# ---------------------------------------------------------------------------
# Karar
# ---------------------------------------------------------------------------


def decide(state: PolicyInput) -> InterventionDecision:
    """Tek karar noktasi. Sirasi KARARLIDIR: ilk uyan gerekce kazanir."""
    codes: list[str] = []

    # 1) Ana anahtar kapali: hicbir H6 bildirimi cikmaz.
    if not state.master_enabled:
        return InterventionDecision("silent", ["PROACTIVITY_DISABLED"], state.why_now)

    # 2) Kural kapali.
    if not state.rule_enabled:
        return InterventionDecision("silent", ["RULE_DISABLED"], state.why_now)

    # 3) Kullanici acik override'i > otomasyon.
    if state.snoozed_until is not None and state.snoozed_until > state.now:
        return InterventionDecision("silent", ["USER_SNOOZED"], state.why_now)

    # 4) Tek seferlik kosul zaten teslim edildi/sonlandi.
    if state.one_shot and state.delivery_count > 0:
        return InterventionDecision("silent", ["DUPLICATE_TRIGGER"], state.why_now)

    # 5) Cooldown: tekrarlanabilir kosulda yeniden yuzeye cikma beklemesi.
    if (
        state.cooldown_hours is not None
        and state.last_delivered_at is not None
        and state.last_delivered_at + timedelta(hours=state.cooldown_hours) > state.now
    ):
        return InterventionDecision("silent", ["RECENTLY_SURFACED"], state.why_now)

    outcome = CATEGORY_OUTCOMES.get(state.category, "digest")
    codes.append(_category_code(state.category))

    # 6) Kuiyet saatleri: ACIL istisnasi YOK.
    if state.quiet_hours is not None and in_quiet_hours(
        state.local_now.timetz().replace(tzinfo=None), *state.quiet_hours
    ):
        return InterventionDecision(
            "defer",
            ["QUIET_HOURS", *codes],
            state.why_now,
            earliest_delivery_at=quiet_hours_end(state.local_now, *state.quiet_hours),
        )

    # 7) Odak aktifken kritik olmayan aday ertelenir.
    if (
        state.focus_active
        and state.focus_deferral_enabled
        and state.category not in FOCUS_CRITICAL_CATEGORIES
    ):
        return InterventionDecision("defer", ["FOCUS_ACTIVE", *codes], state.why_now)

    # 8) Gunluk anlik butce dolduysa kaybolmaz: digest'e duser.
    if outcome == "surface" and state.immediate_surfaces_today >= state.immediate_budget:
        return InterventionDecision("digest", ["IMMEDIATE_BUDGET_EXHAUSTED", *codes], state.why_now)

    return InterventionDecision(outcome, codes, state.why_now)


def _category_code(category: str) -> str:
    return {
        "deadline_today": "DEADLINE_TODAY",
        "deadline_tomorrow": "DEADLINE_1D",
        "deadline_soon": "DEADLINE_3D",
        "deadline_near": "DEADLINE_7D",
        "deadline_far": "DEADLINE_14D",
        "continuity_comeback": "CONTINUITY_GAP",
        "ritual": "RITUAL_DUE",
        "project_stalled": "PROJECT_STALLED",
        "accumulation": "DIGEST_ELIGIBLE",
    }.get(category, "DIGEST_ELIGIBLE")


def importance_for(category: str) -> int:
    return CATEGORY_IMPORTANCE.get(category, 1)
