"""Add strategic graph without reinterpreting or rewriting legacy Goals."""

from alembic import op

revision = "0077_goals_strategy"
down_revision = "0076_source_run_telemetry"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""create table strategic_plan (
        id uuid primary key references entity(id) on delete cascade,
        start_at timestamptz not null,
        end_at timestamptz not null,
        status varchar(16) not null default 'active',
        summary text,
        narrative_path text,
        revision integer not null default 1,
        check (end_at > start_at), check (revision > 0),
        check (status in ('active', 'paused', 'archived', 'superseded'))
    )""")
    op.execute("""create table strategic_pillar (
        id uuid primary key references entity(id) on delete cascade,
        plan_id uuid not null references strategic_plan(id),
        weight numeric(16,4) not null default 1 check (weight > 0),
        position integer not null default 0
    )""")
    op.execute("""create table strategic_plan_revision (
        id uuid primary key references entity(id) on delete cascade,
        plan_id uuid not null references strategic_plan(id),
        revision integer not null,
        state jsonb not null,
        reason text,
        unique (plan_id, revision)
    )""")
    op.execute("alter table goal add column strategic_plan_id uuid references strategic_plan(id)")
    op.execute("alter table goal add column pillar_id uuid references strategic_pillar(id)")
    op.execute("alter table goal add column parent_goal_id uuid references goal(id)")
    op.execute(
        "alter table goal add column priority integer not null default 2 check (priority between 1 and 3)"
    )
    op.execute(
        "alter table goal add column weight numeric(16,4) not null default 1 check (weight > 0)"
    )
    op.execute("""create table key_result (
        id uuid primary key references entity(id) on delete cascade,
        goal_id uuid not null references goal(id),
        description text,
        status varchar(16) not null default 'active' check (status in ('active', 'paused', 'completed', 'retired')),
        unit varchar(60) not null default 'adet',
        direction varchar(16) not null default 'increase' check (direction in ('increase', 'decrease')),
        baseline_value numeric(20,4) not null,
        target_value numeric(20,4) not null,
        weight numeric(16,4) not null default 1 check (weight > 0),
        source_key varchar(64) not null default 'manual' check (source_key in ('manual', 'applications_applied', 'applications_interview', 'applications_offer', 'goal_milestones', 'linked_completion')),
        source_config jsonb not null default '{}'::jsonb,
        manual_value numeric(20,4),
        measured_at timestamptz,
        trajectory_model varchar(16) not null default 'none' check (trajectory_model in ('linear', 'deadline', 'none')),
        start_at timestamptz,
        target_at timestamptz,
        position integer not null default 0,
        check ((direction = 'increase' and target_value > baseline_value) or (direction = 'decrease' and target_value < baseline_value)),
        check (start_at is null or target_at is null or target_at > start_at)
    )""")
    op.execute("create index ix_key_result_goal on key_result(goal_id, position)")
    op.execute("create index ix_goal_strategic_plan on goal(strategic_plan_id)")
    op.execute("create index ix_strategic_pillar_plan on strategic_pillar(plan_id, position)")


def downgrade():
    op.execute("drop table key_result")
    op.execute(
        "alter table goal drop column weight, drop column priority, drop column parent_goal_id, drop column pillar_id, drop column strategic_plan_id"
    )
    op.execute("drop table strategic_plan_revision")
    op.execute("drop table strategic_pillar")
    op.execute("drop table strategic_plan")
