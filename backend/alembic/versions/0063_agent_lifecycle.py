"""A1: içeriği saklamayan, kimliği özetlenmiş agent oturum gözlemleri.

Revision ID: 0063_agent_lifecycle
Revises: 0062_execution_recovery
"""

from alembic import op

revision = "0063_agent_lifecycle"
down_revision = "0062_execution_recovery"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    create table agent_session (
        id bigserial primary key,
        schema_version integer not null,
        harness varchar(16) not null,
        session_key varchar(64) not null unique,
        platform varchar(64) not null,
        first_seen_at timestamptz not null,
        start_seen_at timestamptz,
        last_seen_at timestamptz not null,
        finalized_at timestamptz,
        status varchar(16) not null,
        turn_count integer not null default 0,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now(),
        constraint agent_session_status_valid check (status in ('active', 'finalized')),
        constraint agent_session_harness_valid check (harness in ('hermes', 'codex', 'claude')),
        constraint agent_session_turn_count_nonnegative check (turn_count >= 0)
    )
    """,
    """
    create table agent_session_turn (
        id bigserial primary key,
        session_id bigint not null references agent_session(id) on delete cascade,
        turn_key varchar(64) not null,
        first_seen_at timestamptz not null,
        constraint uq_agent_session_turn_identity unique (session_id, turn_key)
    )
    """,
    "create index ix_agent_session_last_seen_at on agent_session (last_seen_at desc)",
    "create index ix_agent_session_status on agent_session (status)",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("drop table if exists agent_session_turn")
    op.execute("drop table if exists agent_session")
