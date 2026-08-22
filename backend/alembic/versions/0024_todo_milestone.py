"""Gorevi kilometre tasina baglama."""

from alembic import op

revision = "0024_todo_milestone"
down_revision = "0023_todo_recur"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Kural 10: her komut ayri op.execute.
    op.execute(
        "alter table todo add column milestone_id uuid "
        "references milestone(id) on delete set null"
    )
    op.execute("create index todo_milestone_idx on todo (milestone_id)")


def downgrade() -> None:
    op.execute("drop index if exists todo_milestone_idx")
    op.execute("alter table todo drop column if exists milestone_id")
