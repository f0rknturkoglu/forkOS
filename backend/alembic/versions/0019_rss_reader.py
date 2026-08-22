"""RSS reader: full content (content:encoded) column on feed_item."""

from alembic import op

revision = "0019_rss_reader"
down_revision = "0018_opportunity_trash_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Kural 10: tek op.execute'te tek komut
    op.execute("alter table feed_item add column content text")


def downgrade() -> None:
    op.execute("alter table feed_item drop column if exists content")
