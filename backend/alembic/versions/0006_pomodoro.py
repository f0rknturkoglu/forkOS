"""Server-authoritative pomodoro sessions.

Revision ID: 0006_pomodoro
Revises: 0005_plan_slot
"""
from alembic import op

revision = "0006_pomodoro"
down_revision = "0005_plan_slot"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    create table pomodoro_session (
      id                uuid primary key references entity(id) on delete cascade,
      started_at        timestamptz not null default now(),
      ended_at          timestamptz,
      planned_min       int         not null default 25,
      actual_min        int,
      kind              text        not null default 'focus',
      context_entity_id uuid references entity(id) on delete set null,
      topic             text,
      interrupted       boolean     not null default false
    )
    """,
    "create index pomo_time_idx on pomodoro_session (started_at desc)",
    "create index pomo_ctx_idx on pomodoro_session (context_entity_id, started_at desc)",
    "create unique index pomo_one_active_idx on pomodoro_session ((true)) where ended_at is null",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("drop table if exists pomodoro_session cascade")
