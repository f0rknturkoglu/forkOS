"""Finance: subscription brand on expenses and recurring payments."""

from alembic import op

revision = "0022_finance_sub"
down_revision = "0026_media_domain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table expense add column sub text")
    op.execute("alter table recurring_payment add column sub text")


def downgrade() -> None:
    op.execute("alter table expense drop column if exists sub")
    op.execute("alter table recurring_payment drop column if exists sub")
