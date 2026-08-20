"""Todo module.

Revision ID: 0004_todo
Revises: 0003_rss
"""
from alembic import op

revision = "0004_todo"
down_revision = "0003_rss"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    create table todo (
      id            uuid primary key references entity(id) on delete cascade,
      description   text,
      priority      smallint    not null default 2,
      status        text        not null default 'open',
      due_at        timestamptz,
      reminder_at   timestamptz,
      completed_at  timestamptz,
      parent_id     uuid references todo(id) on delete cascade,
      position      int         not null default 0
    )
    """,
    "create index todo_open_idx on todo (status, due_at) where status in ('open','doing')",
    "create index todo_due_idx on todo (due_at) where due_at is not null",
    "create index todo_parent_idx on todo (parent_id)",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("drop table if exists todo cascade")
