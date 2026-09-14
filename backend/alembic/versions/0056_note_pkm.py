"""Not yasam dongusu ve yer imi bilgi yakalama temeli.

Notlar artik kalici silinmeden once cop kutusuna tasinir. Yer imi secimleri ise
ayri vurgu kayitlarina tasinarak hem kutuphane hem de not akisi tarafindan
tek kaynaktan okunur.
"""

from alembic import op

revision = "0056_note_pkm"
down_revision = "0055_status_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table note add column if not exists trashed_at timestamptz")
    op.execute(
        "alter table note add column if not exists trashed_from_archive boolean not null default false"
    )
    op.execute(
        "alter table note add column if not exists source_bookmark_id uuid "
        "references bookmark(id) on delete set null"
    )
    op.execute(
        "create unique index if not exists uq_note_source_bookmark "
        "on note(source_bookmark_id) where source_bookmark_id is not null"
    )
    op.execute(
        "create unique index if not exists uq_note_personal_journal_day "
        "on note(journal_day) where project_id is null and journal_day is not null"
    )
    op.execute(
        "alter table bookmark_highlight add column if not exists position_start integer not null default 0"
    )
    op.execute(
        "alter table bookmark_highlight add column if not exists position_end integer not null default 0"
    )
    op.execute(
        "insert into bookmark_highlight "
        "(id, bookmark_id, text, note, color, anchor_index, position_start, position_end) "
        "select gen_random_uuid(), b.id, b.selection, null, 'yellow', 0, 0, char_length(b.selection) "
        "from bookmark b "
        "where nullif(btrim(b.selection), '') is not null "
        "and not exists (select 1 from bookmark_highlight h "
        "where h.bookmark_id = b.id and h.text = b.selection)"
    )


def downgrade() -> None:
    op.execute("drop index if exists uq_note_personal_journal_day")
    op.execute("drop index if exists uq_note_source_bookmark")
    op.execute("alter table bookmark_highlight drop column if exists position_end")
    op.execute("alter table bookmark_highlight drop column if exists position_start")
    op.execute("alter table note drop column if exists source_bookmark_id")
    op.execute("alter table note drop column if exists trashed_from_archive")
    op.execute("alter table note drop column if exists trashed_at")
