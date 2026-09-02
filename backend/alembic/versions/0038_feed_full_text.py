"""feed_item.full_text: RSS tam-metin cikarimi icin kolon (kural 10).

Feed'lerin summary/content alani cogu zaman ozet ya da truncate'dir; okuma
aninda makale HTML'inden readability cikarimi yapilip buraya yazilir
(talebe bagli -- worker yavaslamaz). Tek SQL komutu.
"""

from alembic import op

revision = "0038_feed_full_text"
down_revision = "0037_flashcard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table feed_item add column full_text text")


def downgrade() -> None:
    op.execute("alter table feed_item drop column full_text")
