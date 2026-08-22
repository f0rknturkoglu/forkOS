"""RSS reader: favicon url on feed."""

from alembic import op

revision = "0020_feed_favicon"
down_revision = "0019_rss_reader"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table feed add column favicon_url text")


def downgrade() -> None:
    op.execute("alter table feed drop column if exists favicon_url")
