"""Generic weekly planner slots.

Revision ID: 0005_plan_slot
Revises: 0004_todo
"""
from alembic import op

revision = "0005_plan_slot"
down_revision = "0004_todo"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    create table plan_slot (
      id           uuid primary key default gen_random_uuid(),
      entity_id    uuid not null references entity(id) on delete cascade,
      day          date not null,
      start_min    int,
      duration_min int,
      note         text,
      position     int not null default 0
    )
    """,
    "create index plan_slot_day_idx on plan_slot (day, position)",
    "create unique index plan_slot_uniq on plan_slot (entity_id, day)",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("drop table if exists plan_slot cascade")
