"""Ogrenme kaynaklari (learning_resource) + not baglantilari icin indeksler.

Konu altinda URL listesi tutar; tamamlananlar konunun ilerlemesini uretir.
PK entity.id'ye FK (kural 1) -- kaynak aranabilir, etiketlenebilir, linklenebilir.
Her SQL komutu ayri op.execute() (kural 10).
"""

from alembic import op

revision = "0034_learning_resource"
down_revision = "0033_finance_income"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table learning_resource (
            id uuid primary key references entity(id) on delete cascade,
            topic_id uuid not null references study_topic(id) on delete cascade,
            url text,
            kind text not null default 'link',
            position integer not null default 0,
            completed_at timestamptz,
            note text
        )
    """)
    op.execute("create index learning_resource_topic_idx on learning_resource (topic_id, position)")
    # Backlink paneli ve graf: "bana kim baglanmis" sorgusu ters yonde gider.
    op.execute("create index link_to_relation_idx on link (to_id, relation)")


def downgrade() -> None:
    op.execute("drop index if exists link_to_relation_idx")
    op.execute("drop index if exists learning_resource_topic_idx")
    op.execute("drop table learning_resource")
