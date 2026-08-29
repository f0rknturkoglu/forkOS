"""Media tracking: media_item (Ryot-style)."""

from alembic import op

revision = "0021_media_item"
down_revision = "0020_feed_favicon"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """create table media_item (
          id uuid primary key references entity(id) on delete cascade,
          kind text not null,
          status text not null default 'planned',
          progress int,
          total int,
          score int,
          notes text,
          started_at timestamptz,
          finished_at timestamptz,
          meta jsonb not null default '{}'
        )"""
    )
    op.execute("create index media_item_kind_idx on media_item (kind, status)")
    op.execute(
        "create index media_item_status_idx on media_item (status) "
        "where status <> 'completed'"
    )


def downgrade() -> None:
    op.execute("drop index if exists media_item_status_idx")
    op.execute("drop index if exists media_item_kind_idx")
    op.execute("drop table if exists media_item")
