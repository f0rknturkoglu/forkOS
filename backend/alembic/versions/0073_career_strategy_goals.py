"""Canonical operational goals and evidence-bound career proposals."""

from alembic import op

revision = "0073_career_strategy_goals"
down_revision = "0072_interview_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""create table goal (
        id uuid primary key references entity(id) on delete cascade,
        status varchar(16) not null default 'active',
        horizon varchar(16) not null default 'quarter',
        description text,
        target_at timestamptz,
        position integer not null default 0,
        source_memory_id varchar(64),
        constraint ck_goal_status check (status in ('active', 'paused', 'completed', 'retired')),
        constraint ck_goal_horizon check (horizon in ('short_term', 'quarter', 'year', 'long_term'))
    )""")
    op.execute("""create table goal_milestone (
        id uuid primary key references entity(id) on delete cascade,
        goal_id uuid not null references goal(id) on delete cascade,
        title text not null,
        due_at timestamptz,
        completed_at timestamptz,
        position integer not null default 0
    )""")
    op.execute("create index ix_goal_milestone_goal on goal_milestone (goal_id, position)")
    op.execute("""create table career_action_proposal (
        id uuid primary key references entity(id) on delete cascade,
        type varchar(16) not null,
        status varchar(16) not null default 'proposed',
        title text not null,
        rationale text not null,
        evidence_refs jsonb not null default '[]'::jsonb,
        sample_size integer,
        estimated_scope varchar(120),
        related_goal_id uuid references goal(id) on delete set null,
        payload jsonb not null default '{}'::jsonb,
        strategy_revision varchar(80) not null,
        fingerprint varchar(80) not null unique,
        materialization_status varchar(24) not null default 'pending',
        target_type varchar(32),
        target_id uuid references entity(id) on delete set null,
        warnings jsonb not null default '[]'::jsonb,
        created_at timestamptz not null default now(),
        decided_at timestamptz,
        constraint ck_career_proposal_type check (type in ('goal', 'milestone', 'learning', 'project', 'todo')),
        constraint ck_career_proposal_status check (status in ('proposed', 'approved', 'rejected', 'materialized', 'expired')),
        constraint ck_career_proposal_materialization check (materialization_status in ('pending', 'materialized', 'unsupported_target', 'failed', 'stale'))
    )""")
    op.execute("create index ix_career_proposal_status on career_action_proposal (status, created_at desc)")


def downgrade() -> None:
    op.execute("drop table career_action_proposal")
    op.execute("drop table goal_milestone")
    op.execute("drop table goal")
