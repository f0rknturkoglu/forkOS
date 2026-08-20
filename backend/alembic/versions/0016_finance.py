"""Expenses, recurring payments and deadline integration."""

from alembic import op

revision = "0016_finance"
down_revision = "0015_project"
branch_labels = None
depends_on = None

UPGRADE = [
    """create table expense (
      id uuid primary key references entity(id) on delete cascade,
      amount numeric(12,2) not null,
      currency char(3) not null default 'TRY',
      category text not null,
      spent_on date not null default current_date,
      note text
    )""",
    "create index expense_month_idx on expense (spent_on desc, category)",
    """create table recurring_payment (
      id uuid primary key references entity(id) on delete cascade,
      amount numeric(12,2) not null,
      currency char(3) not null default 'TRY',
      category text not null default 'subscriptions',
      billing_day smallint,
      frequency text not null default 'monthly',
      next_due_at date,
      active boolean not null default true,
      note text
    )""",
    """create index recurring_active_idx on recurring_payment (next_due_at)
       where active""",
]

DEADLINE_VIEW = """create view deadline_v as
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
   where r.active and r.next_due_at is not null and e.archived_at is null
"""

ORIGINAL_DEADLINE_VIEW = """create view deadline_v as
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
    for statement in UPGRADE:
        op.execute(statement)
    op.execute("drop view if exists deadline_v")
    op.execute(DEADLINE_VIEW)


def downgrade() -> None:
    op.execute("drop view if exists deadline_v")
    op.execute("drop table if exists recurring_payment cascade")
    op.execute("drop table if exists expense cascade")
    op.execute(ORIGINAL_DEADLINE_VIEW)
