"""Proje zaman akisiyla birlesen gunluk notlari.

Her SQL komutu ayri op.execute() cagrisi kullanir (kural 10).
"""

from alembic import op

revision = "0029_project_journal"
down_revision = "0028_note"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "alter table note add column project_id uuid references project(id) on delete set null"
    )
    op.execute("alter table note add column journal_day date")
    op.execute(
        "alter table note add constraint note_project_journal_day_ck "
        "check (project_id is null or journal_day is not null)"
    )
    op.execute(
        "alter table note add constraint note_project_journal_day_uniq "
        "unique (project_id, journal_day)"
    )
    op.execute("alter table project drop column notes")


def downgrade() -> None:
    op.execute("alter table project add column notes text")
    op.execute("alter table note drop constraint note_project_journal_day_uniq")
    op.execute("alter table note drop constraint note_project_journal_day_ck")
    op.execute("alter table note drop column journal_day")
    op.execute("alter table note drop column project_id")
