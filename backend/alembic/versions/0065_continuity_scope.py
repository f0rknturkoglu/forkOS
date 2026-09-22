"""A2.1: agent_session_context tablosuna scope_project kolonu eklenmesi.

Revision ID: 0065_continuity_scope
Revises: 0064_agent_continuity
"""

from alembic import op

revision = "0065_continuity_scope"
down_revision = "0064_agent_continuity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table agent_session_context add column scope_project varchar(64)")


def downgrade() -> None:
    op.execute("alter table agent_session_context drop column if exists scope_project")
