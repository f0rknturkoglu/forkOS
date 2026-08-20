"""rss: feed + feed_item

Revision ID: 0003_rss
Revises: 0002_capture
"""
from alembic import op

revision = "0003_rss"
down_revision = "0002_capture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    create table feed (
      id              uuid primary key references entity(id) on delete cascade,
      url             text not null unique,
      site_url        text,
      category        text,
      etag            text,                     -- conditional GET
      last_modified   text,
      last_fetched_at timestamptz,
      last_status     text,
      error_count     int  not null default 0,
      active          boolean not null default true
    );
    create index feed_due_idx on feed (last_fetched_at) where active;

    create table feed_item (
      id           uuid primary key references entity(id) on delete cascade,
      feed_id      uuid not null references feed(id) on delete cascade,
      guid         text not null,               -- yoksa sha256(url + title)
      url          text,
      author       text,
      summary      text,
      published_at timestamptz,
      fetched_at   timestamptz not null default now(),
      read_at      timestamptz,
      constraint feed_item_uniq unique (feed_id, guid)
    );
    create index feed_item_unread_idx on feed_item (feed_id, published_at desc)
      where read_at is null;
    -- retention taramasi (prune_old_items) bu indeksi kullanir
    create index feed_item_fetched_idx on feed_item (fetched_at);
    """)


def downgrade() -> None:
    op.execute("drop table if exists feed_item, feed cascade;")
