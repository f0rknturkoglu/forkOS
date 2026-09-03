"""Performans indeksleri: opportunity url, score, event entity_id ve feed_item global unread (kural 10).

1. opportunity.url: Ingest deduplication sirasinda full table scan engeller.
2. opportunity.score: forkjob score siralamasinda JSONB sequential scan engeller.
3. event.entity_id: Milyonluk append-only logda varlik gecmisi sorgularini hizlandirir.
4. feed_item unread global: feed_id sarti olmadan tum okunmamislari sirali getirir.

Her komut ayri op.execute() icindedir (asyncpg kural 10).
"""

from alembic import op

revision = "0040_performance_indexes"
down_revision = "0039_event_github_oid_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "create index opportunity_url_idx on opportunity (url) where url is not null"
    )
    op.execute(
        "create index opportunity_score_idx on opportunity "
        "((cast(raw->'forkjob'->>'score' as float)) desc nulls last)"
    )
    op.execute(
        "create index event_entity_id_idx on event (entity_id, occurred_at desc)"
    )
    op.execute(
        "create index feed_item_unread_global_idx on feed_item (published_at desc) "
        "where read_at is null"
    )


def downgrade() -> None:
    op.execute("drop index if exists feed_item_unread_global_idx")
    op.execute("drop index if exists event_entity_id_idx")
    op.execute("drop index if exists opportunity_score_idx")
    op.execute("drop index if exists opportunity_url_idx")
