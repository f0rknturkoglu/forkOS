"""Persist bounded semantic eligibility while raw turn text is transient.

Existing turns are deliberately ineligible: their opt-out intent cannot be
reconstructed safely from distilled text.
"""

from alembic import op

revision = "0069_semantic_eligibility"
down_revision = "0068_semantic_memory_candidates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "alter table agent_session_episode_turn "
        "add column semantic_memory_eligible boolean not null default false"
    )
    op.execute(
        "update agent_semantic_candidate set status = 'stale' "
        "where status in ('proposed', 'needs_review', 'ready')"
    )
    op.execute(
        "alter table agent_semantic_candidate drop constraint ck_agent_semantic_candidate_kind"
    )
    op.execute(
        "alter table agent_semantic_candidate add constraint ck_agent_semantic_candidate_kind "
        "check (kind in ('identity', 'preference', 'correction', 'constraint', 'goal', "
        "'decision', 'lesson', 'project_knowledge', 'reference', 'commitment'))"
    )


def downgrade() -> None:
    op.execute(
        "alter table agent_semantic_candidate drop constraint ck_agent_semantic_candidate_kind"
    )
    op.execute(
        "alter table agent_semantic_candidate add constraint ck_agent_semantic_candidate_kind "
        "check (kind in ('identity', 'preference', 'correction', 'constraint', 'goal', "
        "'decision', 'lesson', 'project_knowledge', 'reference'))"
    )
    op.execute("alter table agent_session_episode_turn drop column semantic_memory_eligible")
