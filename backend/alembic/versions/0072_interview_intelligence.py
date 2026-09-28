"""Add evidence-bound artifacts to existing interview support rows."""

from alembic import op

revision = "0072_interview_intelligence"
down_revision = "0071_application_package"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table interview add column intelligence jsonb not null default '{}'::jsonb")


def downgrade() -> None:
    op.execute("alter table interview drop column intelligence")
