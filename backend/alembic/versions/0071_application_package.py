"""Add package JSONB column to application table.

Revision ID: 0071_application_package
Revises: 0070_observation_enrichment
Create Date: 2026-09-26
"""

from alembic import op

revision = "0071_application_package"
down_revision = "0070_observation_enrichment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "alter table application "
        "add column if not exists package jsonb not null default '{}'::jsonb"
    )


def downgrade() -> None:
    op.execute(
        "alter table application "
        "drop column if exists package"
    )
