"""rss: feed + feed_item

Revision ID: 0003_rss
Revises: 0002_capture

Her DDL komutu ayri string -- asyncpg tek execute'a birden fazla komut almaz.
"""
from alembic import op

revision = "0003_rss"
down_revision = "0002_capture"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    create table feed (
      id              uuid primary key references entity(id) on delete cascade,
      url             text not null unique,
      site_url        text,
      category        text,
      etag            text,
      last_modified   text,
      last_fetched_at timestamptz,
      last_status     text,
      error_count     int  not null default 0,
      active          boolean not null default true
    )
    """,
    "create index feed_due_idx on feed (last_fetched_at) where active",
    """
    create table feed_item (
      id           uuid primary key references entity(id) on delete cascade,
      feed_id      uuid not null references feed(id) on delete cascade,
      guid         text not null,
      url          text,
      author       text,
      summary      text,
      published_at timestamptz,
      fetched_at   timestamptz not null default now(),
      read_at      timestamptz,
      constraint feed_item_uniq unique (feed_id, guid)
    )
    """,
    """
    create index feed_item_unread_idx on feed_item (feed_id, published_at desc)
      where read_at is null
    """,
    # retention taramasi (prune_old_items) bu indeksi kullanir
    "create index feed_item_fetched_idx on feed_item (fetched_at)",
]

DOWNGRADE = [
    "drop table if exists feed_item cascade",
    "drop table if exists feed cascade",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
