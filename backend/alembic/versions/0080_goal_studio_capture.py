"""Goal Studio revisions and capture receipts, all Entity-backed."""

import sqlalchemy as sa

from alembic import op

revision = "0080_goal_studio_capture"
down_revision = "0079_retire_media_batches"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("capture_receipt"):
        op.execute("""CREATE TABLE capture_receipt (
            id UUID PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE,
            client_uuid UUID NOT NULL UNIQUE,
            fingerprint VARCHAR NOT NULL,
            destination VARCHAR NOT NULL,
            result JSONB NOT NULL
        )""")
    if not sa.inspect(op.get_bind()).has_table("goal_studio_session"):
        op.execute("""CREATE TABLE goal_studio_session (
            id UUID PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE,
            client_uuid UUID NOT NULL UNIQUE,
            state VARCHAR(32) NOT NULL,
            data JSONB NOT NULL
        )""")
    if not sa.inspect(op.get_bind()).has_table("goal_studio_revision"):
        op.execute("""CREATE TABLE goal_studio_revision (
            id UUID PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE,
            session_id UUID NOT NULL REFERENCES goal_studio_session(id),
            state VARCHAR(32) NOT NULL,
            fingerprint VARCHAR(64) NOT NULL,
            proposal JSONB NOT NULL,
            before JSONB NOT NULL,
            results JSONB NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            error VARCHAR
        )""")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_goal_studio_revision_session ON goal_studio_revision(session_id)"
    )


def downgrade():
    # Workflow receipts/revisions are retained deliberately, like historical event data.
    pass
