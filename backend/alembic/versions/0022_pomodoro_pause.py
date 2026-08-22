"""Pomodoro duraklatma: paused_at + biriken duraklama suresi."""

from alembic import op

revision = "0022_pomodoro_pause"
down_revision = "0021_media_item"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Kural 10: her komut ayri op.execute -- asyncpg tek prepared statement'a
    # birden fazla DDL almaz.
    op.execute("alter table pomodoro_session add column paused_at timestamptz")
    op.execute(
        "alter table pomodoro_session add column paused_s integer not null default 0"
    )


def downgrade() -> None:
    op.execute("alter table pomodoro_session drop column if exists paused_s")
    op.execute("alter table pomodoro_session drop column if exists paused_at")
