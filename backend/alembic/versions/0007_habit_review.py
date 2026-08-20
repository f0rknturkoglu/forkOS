"""Habits and immutable review snapshots.

Revision ID: 0007_habit_review
Revises: 0006_pomodoro
"""
from alembic import op

revision = "0007_habit_review"
down_revision = "0006_pomodoro"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    create table habit (
      id              uuid primary key references entity(id) on delete cascade,
      cadence         text    not null default 'daily',
      target_per_week int     not null default 7,
      color           text,
      active          boolean not null default true,
      position        int     not null default 0
    )
    """,
    """
    create table habit_log (
      habit_id uuid not null references habit(id) on delete cascade,
      day      date not null,
      done     boolean not null default true,
      note     text,
      primary key (habit_id, day)
    )
    """,
    """
    create table review (
      id           uuid primary key references entity(id) on delete cascade,
      kind         text not null,
      period_start date not null,
      period_end   date not null,
      stats        jsonb not null default '{}',
      decisions    jsonb not null default '{}',
      note         text
    )
    """,
    "create unique index review_period_uniq on review (kind, period_start)",
]

DOWNGRADE = [
    "drop table if exists review cascade",
    "drop table if exists habit_log cascade",
    "drop table if exists habit cascade",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
