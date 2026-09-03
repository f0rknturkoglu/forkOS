"""event.payload github commit oid taramasi icin kismi indeks (kural 10).

GitHub senkronu her commit icin `Event.payload['oid'].astext == oid` arar;
payload JSONB oldugundan indekssiz full table scan yapiliyordu. Kismi indeks
yalnizca github.commit satirlarinda payload->>'oid' uzerine kurulur.

Tek SQL komutu.
"""

from alembic import op

revision = "0039_event_github_oid_idx"
down_revision = "0038_feed_full_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "create index event_github_oid_idx on event ((payload ->> 'oid')) "
        "where verb = 'github.commit'"
    )


def downgrade() -> None:
    op.execute("drop index event_github_oid_idx")
