"""Google calendar mirror and plan-slot mapping."""

from alembic import op

revision = "0014_calendar"
down_revision = "0013_document"
branch_labels = None
depends_on = None

UPGRADE = [
    "alter table plan_slot add column google_event_id text",
    """create index plan_slot_gcal_idx on plan_slot (google_event_id)
       where google_event_id is not null""",
    """create table external_event (
      id uuid primary key references entity(id) on delete cascade,
      provider text not null default 'google',
      external_id text not null,
      calendar_id text,
      starts_at timestamptz not null,
      ends_at timestamptz,
      all_day boolean not null default false,
      location text,
      url text,
      synced_at timestamptz not null default now()
    )""",
    "create unique index external_event_uniq on external_event (provider, external_id)",
    "create index external_event_time_idx on external_event (starts_at)",
]


def upgrade():
    for statement in UPGRADE:
        op.execute(statement)


def downgrade():
    op.execute("drop table if exists external_event cascade")
    op.execute("drop index if exists plan_slot_gcal_idx")
    op.execute("alter table plan_slot drop column if exists google_event_id")
