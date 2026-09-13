"""Firsat yasam donguleri: kesif, basvuru ve duyuru -- tek hakikat kaynagi.

Uc ayri makine vardir ve birbirine karistirilmaz:

* **Kesif** (``opportunity.status``, ``kind == "job"``): ilanin kullanici
  tarafindan ne yapildigi. 19 bin kesfedilmis ilan CRM'e girmez.
* **Basvuru** (``application.status``): yalnizca gercekten takip edilen
  basvurularin hatti.
* **Duyuru** (``opportunity.status``, ``kind != "job"``): YLSY/OSYM/kamu
  duyurusunun yasam dongusu; is basvurusu statuleri kullanilmaz.

Frontend bu kumeleri elle kopyalamaz; ``GET /api/opportunities/lifecycle``
ucundan okur (AGENTS.md kural 13).
"""

from __future__ import annotations

JOB_KINDS = frozenset({"job", "internship"})

#: Is ilani kesif dongusu.
JOB_DISCOVERY_FLOW: tuple[str, ...] = (
    "discovered",
    "shortlisted",
    "dismissed",
    "archived",
    "closed",
)

#: Duyuru yasam dongusu.
ANNOUNCEMENT_FLOW: tuple[str, ...] = (
    "new",
    "reviewed",
    "watching",
    "action_required",
    "applied",
    "completed",
    "expired",
    "archived",
)

#: Basvuru hatti (CRM).
APPLICATION_FLOW: tuple[str, ...] = (
    "preparing",
    "applied",
    "interview",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
    "closed",
)

#: Cop kutusuna atilan bir ilanin kesif durumu.
TRASH_STATUS = "dismissed"

_DISCOVERY_TRANSITIONS: dict[str, set[str]] = {
    "discovered": {"shortlisted", "dismissed", "archived"},
    "shortlisted": {"discovered", "dismissed", "archived"},
    "dismissed": {"shortlisted", "archived"},
    "archived": {"discovered", "shortlisted"},
    "closed": {"discovered", "archived"},
}

_ANNOUNCEMENT_TRANSITIONS: dict[str, set[str]] = {
    "new": {"reviewed", "watching", "action_required", "expired", "archived"},
    "reviewed": {"new", "watching", "action_required", "applied", "completed", "archived"},
    "watching": {"reviewed", "action_required", "applied", "completed", "expired", "archived"},
    "action_required": {"watching", "applied", "completed", "expired", "archived"},
    "applied": {"watching", "completed", "expired", "archived"},
    "completed": {"archived"},
    "expired": {"new", "watching", "archived"},
    "archived": {"new", "reviewed", "watching"},
}

_APPLICATION_TRANSITIONS: dict[str, set[str]] = {
    "preparing": {"applied", "withdrawn", "closed"},
    "applied": {"preparing", "interview", "offer", "rejected", "withdrawn", "closed"},
    "interview": {"applied", "offer", "rejected", "withdrawn", "closed"},
    "offer": {"accepted", "rejected", "withdrawn", "closed"},
    "accepted": set(),
    "rejected": set(),
    "withdrawn": {"preparing"},
    "closed": set(),
}

#: Kapanmis basvurular analitik gecmis icin arsivlenir, silinmez.
APPLICATION_TERMINAL: frozenset[str] = frozenset({"accepted", "rejected", "closed"})

#: Basvuru hattina girmis sayilan durumlar (funnel paydalari bunu kullanir).
APPLICATION_TRACKED: frozenset[str] = frozenset(APPLICATION_FLOW)

#: Gereksinim (belge) durumlari. Tek hakikat kaynagi: Pydantic Literal'leri ve
#: DB check constraint'i buradan turer; `satisfied` gibi kumede olmayan bir
#: deger yazilamaz.
REQUIREMENT_STATUSES: tuple[str, ...] = ("missing", "ready", "submitted", "waived")
REQUIREMENT_MISSING = "missing"
REQUIREMENT_READY = "ready"

#: Kohort tabanli donusum oranlari icin en kucuk payda. Altinda yuzde yerine
#: ham sayi gosterilir; iki basvurudan "%100 gorusme" yanilticidir.
MIN_FUNNEL_COHORT = 10


def validate_requirement_status(status: str) -> None:
    """Kumede olmayan gereksinim durumunda ``ValueError`` yukseltir."""
    if status not in REQUIREMENT_STATUSES:
        raise ValueError(
            f"'{status}' gecerli bir gereksinim durumu degil ({'/'.join(REQUIREMENT_STATUSES)})"
        )

#: Kullanicinin HALA ILGILENDIGI kesif durumlari: deadline/hatirlatma ve
#: Today akisi yalnizca bunlari gorur. `dismissed`, `archived`, `closed`,
#: `expired`, `completed` terminal/arsiv sayilir ve hatirlatma uretmez.
ACTIVE_DISCOVERY_STATUSES: frozenset[str] = frozenset(
    {"discovered", "shortlisted", "new", "reviewed", "watching", "action_required"}
)

#: Kaynak sahipli kesif durumlari: kullanici bu kayitla henuz bir sey yapmadi,
#: dolayisiyla ilan kaynakta kaybolunca durum guncellenebilir.
#: `shortlisted`, `watching`, `action_required`, `archived` gibi durumlar
#: KULLANICIYA aittir ve kaynak kapanmasi bunlari EZMEZ.
SOURCE_OWNED_DISCOVERY: frozenset[str] = frozenset({"discovered", "new"})

#: Kaynak durumu -> kesif durumu. Kaynak ilani biraktiginda kullaniciya
#: dokunmadan isaretlenen durum: is ilani `closed`, duyuru `expired`.
_SOURCE_CLOSED: dict[bool, str] = {True: "closed", False: "expired"}


def source_closed_status(kind: str | None) -> str:
    """Kaynakta kaybolan kaydin kesif durumu."""
    return _SOURCE_CLOSED[is_job_kind(kind)]


def source_reopen_status(kind: str | None) -> str:
    """Kaynakta tekrar gorunen kaydin kesif durumu (dongunun ilk adimi)."""
    return discovery_flow(kind)[0]

#: Eski (0050 oncesi) birlesik durumlardan kesif durumuna esleme.
_LEGACY_DISCOVERY_MAP: dict[str, str] = {
    "considering": "shortlisted",
    "preparing": "shortlisted",
    "applied": "shortlisted",
    "interview": "shortlisted",
    "offer": "shortlisted",
    "accepted": "archived",
    "rejected": "archived",
    "withdrawn": "archived",
    "closed": "archived",
    "trashed": "dismissed",
    "discovered": "discovered",
}

_LEGACY_ANNOUNCEMENT_MAP: dict[str, str] = {
    "considering": "reviewed",
    "preparing": "reviewed",
    "applicable": "action_required",
    "accepted": "archived",
    "rejected": "archived",
    "withdrawn": "archived",
    "closed": "archived",
    "trashed": "dismissed",
    "discovered": "new",
}


def is_job_kind(kind: str | None) -> bool:
    """Is ilani mi? Bilinmeyen tur duyuru sayilir (guvenli taraf)."""
    return (kind or "") in JOB_KINDS


def is_announcement_kind(kind: str | None) -> bool:
    return not is_job_kind(kind)


def discovery_flow(kind: str | None) -> tuple[str, ...]:
    return JOB_DISCOVERY_FLOW if is_job_kind(kind) else ANNOUNCEMENT_FLOW


def discovery_transitions(kind: str | None) -> dict[str, set[str]]:
    return _DISCOVERY_TRANSITIONS if is_job_kind(kind) else _ANNOUNCEMENT_TRANSITIONS


def application_transitions() -> dict[str, set[str]]:
    return _APPLICATION_TRANSITIONS


def allowed_discovery_transitions(kind: str | None, current: str) -> list[str]:
    return sorted(discovery_transitions(kind).get(current, set()))


def allowed_application_transitions(current: str) -> list[str]:
    return sorted(_APPLICATION_TRANSITIONS.get(current, set()))


def coerce_discovery_status(kind: str | None, status: str | None) -> str:
    """Eski/eski birlesik durumu tur uygun kesif durumuna indirger."""
    if not status:
        return discovery_flow(kind)[0]
    flow = discovery_flow(kind)
    if status in flow:
        return status
    table = _LEGACY_DISCOVERY_MAP if is_job_kind(kind) else _LEGACY_ANNOUNCEMENT_MAP
    return table.get(status, flow[0])


def validate_discovery_transition(kind: str | None, from_status: str, to_status: str) -> None:
    """Gecersiz kesif gecisinde ``ValueError`` yukseltir."""
    flow = discovery_flow(kind)
    if to_status not in flow:
        raise ValueError(
            f"'{to_status}' bu tur icin gecerli bir durum degil "
            f"({'/'.join(flow)})"
        )
    if from_status == to_status:
        raise ValueError(f"kayit zaten '{to_status}' durumunda")
    allowed = discovery_transitions(kind).get(from_status, set())
    if to_status not in allowed:
        raise ValueError(f"{from_status} -> {to_status} gecisi gecersiz")


def validate_application_transition(from_status: str, to_status: str) -> None:
    """Gecersiz basvuru gecisinde ``ValueError`` yukseltir."""
    if to_status not in APPLICATION_FLOW:
        raise ValueError(
            f"'{to_status}' gecerli bir basvuru durumu degil "
            f"({'/'.join(APPLICATION_FLOW)})"
        )
    if from_status == to_status:
        raise ValueError(f"basvuru zaten '{to_status}' durumunda")
    allowed = _APPLICATION_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise ValueError(f"{from_status} -> {to_status} gecisi gecersiz")


def lifecycle_payload() -> dict[str, object]:
    """``GET /opportunities/lifecycle`` cevabi."""
    return {
        "job_discovery": {
            "flow": list(JOB_DISCOVERY_FLOW),
            "transitions": {k: sorted(v) for k, v in _DISCOVERY_TRANSITIONS.items()},
        },
        "announcement": {
            "flow": list(ANNOUNCEMENT_FLOW),
            "transitions": {k: sorted(v) for k, v in _ANNOUNCEMENT_TRANSITIONS.items()},
        },
        "application": {
            "flow": list(APPLICATION_FLOW),
            "transitions": {k: sorted(v) for k, v in _APPLICATION_TRANSITIONS.items()},
            "terminal": sorted(APPLICATION_TERMINAL),
        },
        "trash_status": TRASH_STATUS,
        "job_kinds": sorted(JOB_KINDS),
    }
