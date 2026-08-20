"""Courses, books and bookmark-backed learning queue."""

from alembic import op

revision = "0012_course_book"
down_revision = "0011_study"
branch_labels = None
depends_on = None

UPGRADE = [
    """create table course (
      id uuid primary key references entity(id) on delete cascade,
      platform text,
      url text,
      status text not null default 'planned',
      progress_pct smallint not null default 0,
      started_at date,
      completed_at date,
      certificate_entity_id uuid references entity(id) on delete set null,
      notes text
    )""",
    """create table book (
      id uuid primary key references entity(id) on delete cascade,
      author text,
      status text not null default 'want',
      total_pages int,
      current_page int not null default 0,
      started_at date,
      finished_at date,
      rating smallint,
      notes text
    )""",
    "alter table bookmark add column queue_kind text",
    """create index bookmark_queue_idx on bookmark (queue_kind, saved_at desc)
       where collection = 'learning'""",
]


def upgrade():
    for statement in UPGRADE:
        op.execute(statement)


def downgrade():
    op.execute("drop index if exists bookmark_queue_idx")
    op.execute("alter table bookmark drop column if exists queue_kind")
    op.execute("drop table if exists book cascade")
    op.execute("drop table if exists course cascade")
