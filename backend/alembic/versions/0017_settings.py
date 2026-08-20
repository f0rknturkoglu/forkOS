"""Portable application settings."""

from alembic import op

revision = "0017_settings"
down_revision = "0016_finance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """create table setting (
          key text primary key,
          value jsonb not null,
          updated_at timestamptz not null default now()
        )"""
    )


def downgrade() -> None:
    op.execute("drop table if exists setting cascade")
