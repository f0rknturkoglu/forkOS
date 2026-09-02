"""Flashcard module tablolari (kural 1): deck ve card PK'leri entity.id'ye FK.

Anki benzeri aralikli tekrar (SM-2). Deck arama/linklenebilir; kartin on
yuzu entity.title'a gider (global arama karti da bulur). Her SQL komutu
ayri op.execute() (kural 10).
"""

from alembic import op

revision = "0037_flashcard"
down_revision = "0036_milestone_entity"
branch_labels = None
depends_on = None

UPGRADE = [
    """create table flashcard_deck (
        id         uuid primary key references entity(id) on delete cascade,
        created_at timestamptz not null default now()
    )""",
    """create table flashcard_card (
        id          uuid primary key references entity(id) on delete cascade,
        deck_id     uuid not null references flashcard_deck(id) on delete cascade,
        front       text not null default '',
        back        text not null default '',
        -- SM-2 zamanlama alanlari. interval gun cinsinden. due_at NULL = henuz
        -- hic tekrar edilmemis (yeni kart, "yeni" sirasinda bekler).
        interval_days integer not null default 0,
        ease        double precision not null default 2.5,
        due_at      timestamptz,
        reps        integer not null default 0,
        lapses      integer not null default 0,
        suspended   boolean not null default false
    )""",
    "create index flashcard_card_deck_idx on flashcard_card (deck_id)",
    "create index flashcard_card_due_idx on flashcard_card (due_at) where suspended = false",
]


DOWNGRADE = [
    "drop table flashcard_card",
    "drop table flashcard_deck",
    "delete from entity where type in ('flashcard_deck', 'flashcard_card')",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
