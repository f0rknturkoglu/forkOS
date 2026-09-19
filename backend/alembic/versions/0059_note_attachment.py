"""not ekleri icin metadata tablosu (binary artik dosya sisteminde).

Revision ID: 0059_note_attachment
Revises: 0058_drop_note_page_width
Create Date: 2026-09-20

Not eki icerigi `note.attachments` JSONB dizisinde base64 olarak duruyordu.
Binary artik `data/attachments/<sha256>` altinda tutulur; bu tablo yalnizca
metadata tasir ve `note.attachments` KOLONU SIMDILIK DURUR (veri kaybi yok).

Donusum uygulama tarafinda, not bazli ve idempotent yapilir
(`note/service.py::convert_legacy_attachments`): blob yazilir, satir olusur,
ancak ikisi de basariliysa eski JSONB temizlenir. Kolonun dusurulmesi ayri bir
fazdir; bu migration semayi geriye uyumlu tutar.
"""

from alembic import op

revision = "0059_note_attachment"
down_revision = "0058_drop_note_page_width"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""create table note_attachment (
        id uuid primary key default gen_random_uuid(),
        note_id uuid not null references note(id) on delete cascade,
        name text not null,
        mime varchar(128) not null,
        size integer not null,
        sha256 char(64) not null,
        created_at timestamptz not null default now()
    )""")
    op.execute(
        "create index ix_note_attachment_note_id on note_attachment(note_id, created_at)"
    )
    # Ayni blob'u paylasan satirlar icin: silme sonrasi "hala referans var mi?"
    op.execute("create index ix_note_attachment_sha256 on note_attachment(sha256)")


def downgrade() -> None:
    op.execute("drop index if exists ix_note_attachment_sha256")
    op.execute("drop index if exists ix_note_attachment_note_id")
    op.execute("drop table if exists note_attachment")
