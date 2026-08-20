"""Projects, milestones and GitHub activity."""

from alembic import op

revision = "0015_project"
down_revision = "0014_calendar"
branch_labels = None
depends_on = None

UPGRADE = [
    """create table project (
      id uuid primary key references entity(id) on delete cascade,
      status text not null default 'active',
      github_repo text,
      url text,
      stack text[],
      next_action text,
      last_activity_at timestamptz,
      notes text,
      position int not null default 0
    )""",
    "create index project_status_idx on project (status, position)",
    """create table milestone (
      id uuid primary key default gen_random_uuid(),
      project_id uuid not null references project(id) on delete cascade,
      title text not null,
      due_at timestamptz,
      completed_at timestamptz,
      position int not null default 0
    )""",
    """create table github_activity (
      day date not null,
      repo text not null,
      commit_count int not null default 0,
      primary key (day, repo)
    )""",
    "create index github_day_idx on github_activity (day desc)",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("drop table if exists github_activity cascade")
    op.execute("drop table if exists milestone cascade")
    op.execute("drop table if exists project cascade")
