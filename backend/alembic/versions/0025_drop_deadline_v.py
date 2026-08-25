"""Drop deadline_v view (kural 16): son tarihler artik ModuleSpec.deadline_provider
saglayicilarindan toplaniyor (app/core/deadlines.py). Görünüm elle SQL union'di;
yeni son-tarihli modul migration degil provider yazar.
"""

from alembic import op

revision = "0025_drop_deadline_v"
down_revision = "0024_remove_habit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("drop view if exists deadline_v")


def downgrade() -> None:
    # Geri donus: eski union gorunumu (opportunity + todo + recurring).
    op.execute(
        """create view deadline_v as
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
union all
  select e.id, e.type, e.title, r.next_due_at::timestamptz,
         'recurring'::text, null::text, 1
    from recurring_payment r join entity e on e.id = r.id
   where r.active and r.next_due_at is not null and e.archived_at is null"""
    )
