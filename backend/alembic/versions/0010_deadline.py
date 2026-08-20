"""Cross-module deadline view.

Revision ID: 0010_deadline
Revises: 0009_notification
"""

from alembic import op

revision = "0010_deadline"
down_revision = "0009_notification"
branch_labels = None
depends_on = None

DEADLINE_VIEW = """
create view deadline_v as
  select e.id as entity_id, e.type, e.title, o.deadline_at as due_at,
         'opportunity'::text as module, o.kind as sub_kind, o.priority
    from opportunity o join entity e on e.id = o.id
   where o.deadline_at is not null
     and o.status not in ('archived','rejected','accepted')
     and e.archived_at is null
union all
  select e.id, e.type, e.title, t.due_at, 'todo'::text, null::text, t.priority
    from todo t join entity e on e.id = t.id
   where t.due_at is not null and t.status in ('open','doing')
     and e.archived_at is null
"""


def upgrade() -> None:
    op.execute(DEADLINE_VIEW)


def downgrade() -> None:
    op.execute("drop view if exists deadline_v")
