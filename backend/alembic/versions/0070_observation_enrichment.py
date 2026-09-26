"""Add enrichment JSONB column to opportunity_source_observation.

Revision ID: 0070_observation_enrichment
Revises: 0069_semantic_eligibility
Create Date: 2026-09-26
"""

from alembic import op

revision = "0070_observation_enrichment"
down_revision = "0069_semantic_eligibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "alter table opportunity_source_observation "
        "add column if not exists enrichment jsonb not null default '{}'::jsonb"
    )


def downgrade() -> None:
    op.execute(
        "alter table opportunity_source_observation "
        "drop column if exists enrichment"
    )
