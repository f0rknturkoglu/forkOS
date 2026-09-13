"""Durum kolonlarina DB seviyesinde kisit.

Kesif durumu (`opportunity.status`), kaynak durumu, basvuru hatti durumu ve
gereksinim durumu su ana kadar yalnizca Python tarafinda dogrulaniyordu: bir
betik, elle SQL ya da gozden kacmis bir yol semada olmayan bir deger yazabiliyor
ve arayuz o kaydi etiketsiz/rotasiz gosteriyordu. Degerler tek kaynaktan gelir
(`lifecycle.JOB_DISCOVERY_FLOW`, `ANNOUNCEMENT_FLOW`, `APPLICATION_FLOW`,
`SOURCE_STATUS_PRIORITY`, `REQUIREMENT_STATUSES`).

Mevcut veri bu kumelere UYUYOR (canli sayimda 0 ihlal) ve 0050/0051 migration'lari
eski birlesik durumlari zaten donusturmustu; bu yuzden kisitlar `not valid`
kullanmadan dogrudan eklenir.
"""

from alembic import op

revision = "0055_status_constraints"
down_revision = "0054_source_run_scope"
branch_labels = None
depends_on = None

_JOB_KINDS = ("job", "internship")
_JOB_DISCOVERY = ("discovered", "shortlisted", "dismissed", "archived", "closed")
_ANNOUNCEMENT = (
    "new",
    "reviewed",
    "watching",
    "action_required",
    "applied",
    "completed",
    "expired",
    "archived",
)
_SOURCE_STATUSES = ("active", "missing", "likely_closed", "closed")
_APPLICATION = (
    "preparing",
    "applied",
    "interview",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
    "closed",
)
_REQUIREMENT = ("missing", "ready", "submitted", "waived")
_HISTORY = (*_JOB_DISCOVERY, *_ANNOUNCEMENT, *_APPLICATION)


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} in (" + ", ".join(f"'{value}'" for value in values) + ")"


def upgrade() -> None:
    # Kesif durumu TURE baglidir: is ilani ve duyuru ayni kolonu paylasir.
    op.execute(
        "alter table opportunity add constraint opportunity_status_check check ("
        f"(kind in ({', '.join(repr(value) for value in _JOB_KINDS)}) "
        f"and {_in_clause('status', _JOB_DISCOVERY)}) or "
        f"(kind not in ({', '.join(repr(value) for value in _JOB_KINDS)}) "
        f"and {_in_clause('status', _ANNOUNCEMENT)}))"
    )
    op.execute(
        "alter table opportunity add constraint opportunity_source_status_check "
        f"check ({_in_clause('source_status', _SOURCE_STATUSES)})"
    )
    op.execute(
        "alter table opportunity_source_observation "
        "add constraint opportunity_observation_source_status_check "
        f"check ({_in_clause('source_status', _SOURCE_STATUSES)})"
    )
    op.execute(
        "alter table application add constraint application_status_check "
        f"check ({_in_clause('status', _APPLICATION)})"
    )
    op.execute(
        "alter table opportunity_requirement add constraint opportunity_requirement_status_check "
        f"check ({_in_clause('status', _REQUIREMENT)})"
    )
    # Gecmis append-only'dir; yalnizca BILINEN durum kumesi yazilabilir.
    op.execute(
        "alter table application_history add constraint application_history_to_status_check "
        f"check ({_in_clause('to_status', _HISTORY)})"
    )


def downgrade() -> None:
    op.execute(
        "alter table application_history drop constraint if exists application_history_to_status_check"
    )
    op.execute(
        "alter table opportunity_requirement drop constraint if exists opportunity_requirement_status_check"
    )
    op.execute("alter table application drop constraint if exists application_status_check")
    op.execute(
        "alter table opportunity_source_observation "
        "drop constraint if exists opportunity_observation_source_status_check"
    )
    op.execute(
        "alter table opportunity drop constraint if exists opportunity_source_status_check"
    )
    op.execute("alter table opportunity drop constraint if exists opportunity_status_check")
