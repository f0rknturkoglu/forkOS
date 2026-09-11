"""bookmark pocket engine sutunlari ve highlight tablosu.

Revision ID: 0053_bookmark_pocket_engine
Revises: 0052_source_run_error_kind
Create Date: 2026-09-11
"""

from alembic import op

revision = "0053_bookmark_pocket_engine"
down_revision = "0052_source_run_error_kind"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table bookmark add column if not exists content_html text")
    op.execute("alter table bookmark add column if not exists content_text text")
    op.execute("alter table bookmark add column if not exists hero_image_url text")
    op.execute("alter table bookmark add column if not exists favicon_url text")
    op.execute("alter table bookmark add column if not exists author varchar(128)")
    op.execute("alter table bookmark add column if not exists published_at timestamptz")
    op.execute("alter table bookmark add column if not exists reading_time_min integer not null default 1")
    op.execute("alter table bookmark add column if not exists word_count integer not null default 0")
    op.execute("alter table bookmark add column if not exists scroll_progress integer not null default 0")
    op.execute("""create table bookmark_highlight (
        id uuid primary key,
        bookmark_id uuid not null references bookmark(id) on delete cascade,
        text text not null,
        note text,
        color varchar(16) not null default 'yellow',
        anchor_index integer not null default 0,
        created_at timestamptz not null default now()
    )""")
    op.execute("create index ix_bookmark_highlight_bookmark_id on bookmark_highlight(bookmark_id)")


def downgrade() -> None:
    op.execute("drop index if exists ix_bookmark_highlight_bookmark_id")
    op.execute("drop table if exists bookmark_highlight")
    op.execute("alter table bookmark drop column if exists scroll_progress")
    op.execute("alter table bookmark drop column if exists word_count")
    op.execute("alter table bookmark drop column if exists reading_time_min")
    op.execute("alter table bookmark drop column if exists published_at")
    op.execute("alter table bookmark drop column if exists author")
    op.execute("alter table bookmark drop column if exists favicon_url")
    op.execute("alter table bookmark drop column if exists hero_image_url")
    op.execute("alter table bookmark drop column if exists content_text")
    op.execute("alter table bookmark drop column if exists content_html")
