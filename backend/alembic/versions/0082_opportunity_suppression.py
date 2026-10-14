"""Opportunity suppression tombstone table for permanent bulk cleanup.

Revision ID: 0082_opportunity_suppression
Revises: 0081_goal_roadmap
Create Date: 2026-10-14
"""

from alembic import op
import sqlalchemy as sa

revision = "0082_opportunity_suppression"
down_revision = "0081_goal_roadmap"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """CREATE TABLE IF NOT EXISTS opportunity_suppression (
            id UUID PRIMARY KEY,
            source TEXT NOT NULL,
            external_id TEXT,
            canonical_url TEXT,
            dedup_hash TEXT,
            reason TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )"""
    )
    op.execute(
        """CREATE INDEX IF NOT EXISTS ix_opp_suppression_source_ext
           ON opportunity_suppression (source, external_id)
           WHERE external_id IS NOT NULL"""
    )
    op.execute(
        """CREATE INDEX IF NOT EXISTS ix_opp_suppression_canonical_url
           ON opportunity_suppression (canonical_url)
           WHERE canonical_url IS NOT NULL"""
    )
    op.execute(
        """CREATE INDEX IF NOT EXISTS ix_opp_suppression_dedup_hash
           ON opportunity_suppression (dedup_hash)
           WHERE dedup_hash IS NOT NULL"""
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS opportunity_suppression CASCADE")
