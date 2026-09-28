"""Persist structured scrape telemetry in SourceRun."""

from alembic import op

revision = "0076_source_run_telemetry"
down_revision = "0075_split_evaluations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table source_run add column telemetry jsonb")


def downgrade() -> None:
    op.execute("alter table source_run drop column if exists telemetry")
