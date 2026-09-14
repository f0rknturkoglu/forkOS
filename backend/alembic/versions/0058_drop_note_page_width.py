"""Not genişliği tercihi kaldırıldı: her not tam genişlik yazar.

`note.page_width` (Dar/Geniş/Tam) arayüzden sökülüyor; editör artık her zaman
çalışma alanının tamamını kullanıyor. Tercihi tasiyan kolon ve CHECK'i
birlikte duser, boylece sema ile model (kolon ve kisit kaldirildi) ayni kalir.
"""

from alembic import op

revision = "0058_drop_note_page_width"
down_revision = "0057_note_trashed_from_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table note drop constraint if exists note_page_width_ck")
    op.execute("alter table note drop column if exists page_width")


def downgrade() -> None:
    # Simetrik geri donus: 0041'deki varsayilan ve CHECK aynen kurulur.
    op.execute(
        "alter table note add column if not exists page_width text not null default 'compact'"
    )
    op.execute(
        "alter table note add constraint note_page_width_ck "
        "check (page_width in ('compact', 'wide', 'full'))"
    )
