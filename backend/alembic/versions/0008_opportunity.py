"""Opportunity hub and application requirements.

Revision ID: 0008_opportunity
Revises: 0007_habit_review
"""

from alembic import op

revision = "0008_opportunity"
down_revision = "0007_habit_review"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    create table opportunity (
      id            uuid primary key references entity(id) on delete cascade,
      kind          text not null,
      organization  text,
      url           text,
      status        text not null default 'discovered',
      priority      smallint not null default 2,
      found_at      timestamptz not null default now(),
      deadline_at   timestamptz,
      applied_at    timestamptz,
      location      text,
      remote        text,
      compensation  text,
      source        text not null default 'manual',
      external_id   text,
      raw           jsonb not null default '{}',
      notes         text
    )
    """,
    """
    create unique index opportunity_source_uniq on opportunity (source, external_id)
      where external_id is not null
    """,
    "create index opportunity_status_idx on opportunity (status, priority desc)",
    """
    create index opportunity_deadline_idx on opportunity (deadline_at)
      where deadline_at is not null
    """,
    "create index opportunity_kind_idx on opportunity (kind, found_at desc)",
    """
    create table opportunity_requirement (
      id                 uuid primary key default gen_random_uuid(),
      opportunity_id     uuid not null references opportunity(id) on delete cascade,
      name               text not null,
      required           boolean not null default true,
      status             text not null default 'missing',
      document_entity_id uuid references entity(id) on delete set null,
      note               text,
      position           int not null default 0
    )
    """,
    "create index opp_req_idx on opportunity_requirement (opportunity_id, position)",
]

DOWNGRADE = [
    "drop table if exists opportunity_requirement cascade",
    "drop table if exists opportunity cascade",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
