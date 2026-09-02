"""Notlara yedeklenebilir yerel fotograf ve ses ekleri.

Ekler note JSONB kolonu icinde tutulur. Boylece yeni bir destek tablosu
istisnasi gerekmez ve mevcut full_json yedegi medyayi da kapsar.
Her SQL komutu ayri op.execute() (kural 10).
"""

from alembic import op

revision = "0035_note_attachments"
down_revision = "0034_learning_resource"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table note add column attachments jsonb not null default '[]'::jsonb")


def downgrade() -> None:
    op.execute("alter table note drop column attachments")
