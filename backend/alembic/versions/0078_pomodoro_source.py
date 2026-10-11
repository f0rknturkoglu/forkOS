"""Preserve session history and mark existing manual records from append-only evidence."""
from alembic import op

revision = "0078_pomodoro_source"
down_revision = "0077_goals_strategy"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("alter table pomodoro_session add column source varchar(16) not null default 'timer'")
    op.execute("""update pomodoro_session p set source = 'manual'
        where exists (select 1 from event e where e.entity_id = p.id
        and e.verb = 'pomodoro.completed' and e.payload->>'manual' = 'true')""")
    op.execute("alter table pomodoro_session add constraint pomodoro_source_check check (source in ('timer', 'manual'))")


def downgrade():
    op.execute("alter table pomodoro_session drop constraint pomodoro_source_check")
    op.execute("alter table pomodoro_session drop column source")
