"""Study areas and topic tree."""

from alembic import op

revision = "0011_study"
down_revision = "0010_deadline"
branch_labels = None
depends_on = None

UPGRADE = [
    """create table study_area (
      id uuid primary key references entity(id) on delete cascade,
      color text,
      active boolean not null default true,
      position int not null default 0
    )""",
    """create table study_topic (
      id uuid primary key references entity(id) on delete cascade,
      area_id uuid not null references study_area(id) on delete cascade,
      parent_id uuid references study_topic(id) on delete cascade,
      status text not null default 'not_started',
      confidence smallint,
      target_min int,
      position int not null default 0,
      last_studied_at timestamptz
    )""",
    "create index study_topic_area_idx on study_topic (area_id, position)",
    "create index study_topic_parent_idx on study_topic (parent_id)",
]


def upgrade():
    for statement in UPGRADE:
        op.execute(statement)


def downgrade():
    op.execute("drop table if exists study_topic cascade")
    op.execute("drop table if exists study_area cascade")
