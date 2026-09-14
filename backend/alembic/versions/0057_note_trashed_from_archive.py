"""0056 sonradan duzenlendigi icin canli semada eksik kalan kolonu geri getirir.

`0056_note_pkm` canli veritabanina uygulandiginda bu dosyada
`trashed_from_archive` ifadesi YOKTU; ifade sonradan eklendi ama Alembic
revizyonu coktan ilerledigi icin bir daha kosmadi. Sonuc: sema ile model
ayristi ve her `POST /notes` cagrisi

    UndefinedColumnError: column "trashed_from_archive" of relation "note"
    does not exist

ile 500 dondu -- yani Notlar modulu hic yazamiyordu.

Testler bunu yakalayamaz: `pytest` semayi sifirdan `upgrade head` ile kurar ve
orada ifade zaten dosyada oldugu icin kolon olusur. Kirilma yalnizca ifade
eklenmeden ONCE migrate edilmis veritabanlarinda gorunur. Bu yuzden eksik
kolonu ileri yonlu ve idempotent bir onarim migration'i ile geri getiriyoruz:
0056'yi tam kosmus veritabanlarinda islem yoktur.
"""

from alembic import op

revision = "0057_note_trashed_from_archive"
down_revision = "0056_note_pkm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "alter table note add column if not exists trashed_from_archive boolean not null default false"
    )


def downgrade() -> None:
    # Simetrik: kolonu birakmak 0056'nin tam kosmadigi duruma geri donmek olurdu.
    op.execute("alter table note drop column if exists trashed_from_archive")
