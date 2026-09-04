"""Firsatlara surumlu iki asamali degerlendirme kaydi ekle (kural 10)."""

from alembic import op

revision = "0043_opportunity_evaluation"
down_revision = "0042_note_folders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table opportunity add column evaluation jsonb not null default '{}'::jsonb")
    op.execute("alter table opportunity add column evaluated_at timestamptz null")


def downgrade() -> None:
    op.execute("alter table opportunity drop column evaluated_at")
    op.execute("alter table opportunity drop column evaluation")
