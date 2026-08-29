"""Local notes (Faz 21): note tablosu.

PK entity.id'ye FK (kural 1 -- EntityBacked); baslik Entity.title'da yasar.
Her SQL komutu ayri op.execute() (kural 10).
"""

from alembic import op

revision = "0028_note"
down_revision = "0027_book_to_media_item"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table note (
            id uuid primary key references entity(id) on delete cascade,
            body text not null default '',
            pinned boolean not null default false
        )
    """)


def downgrade() -> None:
    op.execute("drop table note")
