"""A3.1: Epistemic evidence-class DB CHECK invariants on agent_session_episode_item.

Enforces:
- canonical_supported requires jsonb_array_length(support_refs) > 0
- turn_derived requires jsonb_array_length(support_refs) = 0

Revision ID: 0067_episode_evidence_guard
Revises: 0066_agent_episode
"""

from alembic import op

revision = "0067_episode_evidence_guard"
down_revision = "0066_agent_episode"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    alter table agent_session_episode_item
        add constraint ck_agent_session_episode_item_canonical_evidence
        check (evidence_class <> 'canonical_supported' or jsonb_array_length(support_refs) > 0)
    """,
    """
    alter table agent_session_episode_item
        add constraint ck_agent_session_episode_item_turn_derived_evidence
        check (evidence_class <> 'turn_derived' or jsonb_array_length(support_refs) = 0)
    """,
]

DOWNGRADE = [
    "alter table agent_session_episode_item drop constraint if exists ck_agent_session_episode_item_turn_derived_evidence",
    "alter table agent_session_episode_item drop constraint if exists ck_agent_session_episode_item_canonical_evidence",
]


def upgrade() -> None:
    for stmt in UPGRADE:
        op.execute(stmt)


def downgrade() -> None:
    for stmt in DOWNGRADE:
        op.execute(stmt)
