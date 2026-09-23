"""A4: Semantic Promotion & Durable Memory candidate workflow and A3 epistemic fields.

Adds:
- source_role and evidence_digest columns to agent_session_episode_item
- agent_semantic_candidate table for candidate workflow and review state

Revision ID: 0068_semantic_memory_candidates
Revises: 0067_episode_evidence_guard
"""

from alembic import op

revision = "0068_semantic_memory_candidates"
down_revision = "0067_episode_evidence_guard"
branch_labels = None
depends_on = None

UPGRADE = [
    "alter table agent_session_episode_item add column if not exists source_role varchar(16) null",
    "alter table agent_session_episode_item add column if not exists evidence_digest varchar(64) null",
    """
    alter table agent_session_episode_item
        add constraint ck_agent_session_episode_item_source_role
        check (source_role is null or source_role in ('user', 'assistant', 'mixed'))
    """,
    """
    alter table agent_session_episode_item
        add constraint ck_agent_session_episode_item_evidence_digest
        check (evidence_digest is null or char_length(evidence_digest) = 64)
    """,
    """create table agent_semantic_candidate (
        id uuid primary key,
        candidate_key varchar(64) not null,
        kind varchar(32) not null,
        statement varchar(500) not null,
        scope varchar(32) not null default 'global',
        scope_project varchar(64) null,
        subject_key varchar(64) null,
        domains jsonb not null default '[]'::jsonb,
        suggested_destination varchar(32) not null,
        primary_evidence_class varchar(32) not null,
        evidence_refs jsonb not null default '[]'::jsonb,
        observed_at timestamptz not null,
        valid_from timestamptz null,
        valid_to timestamptz null,
        rationale varchar(500) null,
        conditions jsonb not null default '[]'::jsonb,
        exceptions jsonb not null default '[]'::jsonb,
        sensitivity varchar(16) not null default 'normal',
        remote_allowed boolean not null default false,
        status varchar(24) not null default 'proposed',
        reviewed_by varchar(32) null,
        possible_related_card_ids jsonb not null default '[]'::jsonb,
        warnings jsonb not null default '[]'::jsonb,
        recurrence_count integer not null default 1,
        first_seen_at timestamptz not null,
        last_seen_at timestamptz not null,
        revision varchar(64) not null,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now(),
        constraint uq_agent_semantic_candidate_key unique (candidate_key),
        constraint ck_agent_semantic_candidate_status check (
            status in ('proposed', 'needs_review', 'ready', 'promoted', 'rejected', 'stale')
        ),
        constraint ck_agent_semantic_candidate_kind check (
            kind in ('identity', 'preference', 'correction', 'constraint', 'goal', 'decision', 'lesson', 'project_knowledge', 'reference')
        ),
        constraint ck_agent_semantic_candidate_evidence check (
            primary_evidence_class in ('explicit_user', 'canonical_source', 'episode_derived', 'model_derived')
        ),
        constraint ck_agent_semantic_candidate_destination check (
            suggested_destination in ('operational', 'hot_memory', 'durable_vault', 'procedural_candidate', 'discard')
        ),
        constraint ck_agent_semantic_candidate_recurrence check (
            recurrence_count >= 1
        )
    )
    """,
    """
    create index if not exists ix_agent_semantic_candidate_status
        on agent_semantic_candidate (status)
    """,
    """
    create index if not exists ix_agent_semantic_candidate_kind
        on agent_semantic_candidate (kind)
    """,
    """
    create index if not exists ix_agent_semantic_candidate_last_seen
        on agent_semantic_candidate (last_seen_at desc)
    """,
]

DOWNGRADE = [
    "drop table if exists agent_semantic_candidate",
    "alter table agent_session_episode_item drop constraint if exists ck_agent_session_episode_item_evidence_digest",
    "alter table agent_session_episode_item drop constraint if exists ck_agent_session_episode_item_source_role",
    "alter table agent_session_episode_item drop column if exists evidence_digest",
    "alter table agent_session_episode_item drop column if exists source_role",
]


def upgrade() -> None:
    for stmt in UPGRADE:
        op.execute(stmt)


def downgrade() -> None:
    for stmt in DOWNGRADE:
        op.execute(stmt)
