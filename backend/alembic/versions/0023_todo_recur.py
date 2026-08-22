"""Gorevlere tekrar (rutin) alani."""

from alembic import op

revision = "0023_todo_recur"
down_revision = "0022_pomodoro_pause"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Kural 10: her komut ayri op.execute.
    op.execute("alter table todo add column recur text")
    op.execute(
        "alter table todo add constraint todo_recur_valid "
        "check (recur is null or recur in ('daily','weekdays','weekly','monthly'))"
    )
    # Tamamlanan rutinin urettigi yeni kayit, kaynagini gosterir.
    op.execute(
        "alter table todo add column recur_origin_id uuid "
        "references todo(id) on delete set null"
    )


def downgrade() -> None:
    op.execute("alter table todo drop column if exists recur_origin_id")
    op.execute("alter table todo drop constraint if exists todo_recur_valid")
    op.execute("alter table todo drop column if exists recur")
