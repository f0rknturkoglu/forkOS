"""capture: bookmark (Universal Inbox + Bookmark Library ayni tablo)

Revision ID: 0002_capture
Revises: 0001_core
"""
from alembic import op

revision = "0002_capture"
down_revision = "0001_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    -- Universal Inbox ve Bookmark Library AYNI tablo.
    -- collection='inbox' -> Inbox ekrani, digerleri -> Bookmark Library.
    -- Surukle-birak tek UPDATE; link ve event'ler kopmaz.
    create table bookmark (
      id           uuid primary key references entity(id) on delete cascade,
      url          text        not null,
      url_hash     text        not null,
      description  text,
      selection    text,
      note         text,
      collection   text        not null default 'inbox',
      source       text        not null default 'extension',
      read_status  text        not null default 'unread',
      favorite     boolean     not null default false,
      saved_at     timestamptz not null default now(),
      client_uuid  uuid unique
    );
    create index bookmark_collection_idx on bookmark (collection, saved_at desc);
    -- url_hash BILEREK unique degil: ayni sayfayi ikinci kez kaydetmek hata degil.
    create index bookmark_urlhash_idx    on bookmark (url_hash);
    create index bookmark_unread_idx     on bookmark (read_status, saved_at desc);
    """)


def downgrade() -> None:
    op.execute("drop table if exists bookmark cascade;")
