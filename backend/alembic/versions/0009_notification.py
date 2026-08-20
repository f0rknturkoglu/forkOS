"""Deduplicated notification center.

Revision ID: 0009_notification
Revises: 0008_opportunity
"""

from alembic import op

revision = "0009_notification"
down_revision = "0008_opportunity"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    create table notification (
      id           bigserial primary key,
      kind         text not null,
      title        text not null,
      body         text,
      entity_id    uuid references entity(id) on delete cascade,
      importance   smallint not null default 1,
      dedup_key    text not null,
      created_at   timestamptz not null default now(),
      read_at      timestamptz,
      dismissed_at timestamptz
    )
    """,
    "create unique index notification_dedup_uniq on notification (dedup_key)",
    """
    create index notification_unread_idx on notification (created_at desc)
      where read_at is null and dismissed_at is null
    """,
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("drop table if exists notification cascade")
