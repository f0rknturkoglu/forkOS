"""Milestone entity-backed (kural 1): PK'si entity.id'ye FK.

Milestone son tarihleri deadline_provider'dan /api/deadlines'a gidiyor ama
rows_with_titles entity tablosundan baslik okur; milestone id'leri entity'de
olmadigi icin son tarihler sessizce dusuyordu. Ayni id ile entity satirlari
acilir ve FK eklenir -- mevcut id'ler KORUNUR (frontend baglantilari bozulmaz).

Her SQL komutu ayri op.execute() (kural 10).
"""

from alembic import op

revision = "0036_milestone_entity"
down_revision = "0035_note_attachments"
branch_labels = None
depends_on = None

UPGRADE = [
    # Mevcut her milestone icin ayni id'de entity kaydi (title arama metnine de girer).
    """insert into entity (id, type, title, search_text)
       select id, 'milestone', title, title from milestone""",
    # PK zaten id; FK ekle. Entity silinirse milestone cascade silinir.
    """alter table milestone add constraint milestone_id_fk
       foreign key (id) references entity(id) on delete cascade""",
]

DOWNGRADE = [
    "alter table milestone drop constraint milestone_id_fk",
    "delete from entity where type = 'milestone'",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
