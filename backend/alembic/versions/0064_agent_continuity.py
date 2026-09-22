"""A2: agent oturum bağlamı ve kaynak devamlılığı destek tabloları.

Revision ID: 0064_agent_continuity
Revises: 0063_agent_lifecycle
"""

from alembic import op

revision = "0064_agent_continuity"
down_revision = "0063_agent_lifecycle"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    create table agent_session_context (
        id bigserial primary key,
        session_id bigint not null references agent_session(id) on delete cascade,
        turn_id bigint references agent_session_turn(id) on delete cascade,
        schema_version integer not null default 1,
        is_first_turn boolean not null,
        item_count integer not null default 0,
        char_count integer not null default 0,
        truncated boolean not null default false,
        omitted_count integer not null default 0,
        degraded_reasons jsonb not null default '[]'::jsonb,
        created_at timestamptz not null default now()
    )
    """,
    """
    create table agent_session_source (
        id bigserial primary key,
        session_id bigint not null references agent_session(id) on delete cascade,
        turn_id bigint references agent_session_turn(id) on delete cascade,
        source_id varchar(128) not null,
        source_type varchar(32) not null,
        source_version varchar(64),
        scope_project varchar(64),
        topic_signature varchar(64),
        delivered_at timestamptz not null,
        expires_at timestamptz not null,
        constraint uq_agent_session_source_identity unique (session_id, source_id)
    )
    """,
    "create index ix_agent_session_context_session_created on agent_session_context (session_id, created_at desc)",
    "create index ix_agent_session_source_session_expires on agent_session_source (session_id, expires_at desc)",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("drop table if exists agent_session_source")
    op.execute("drop table if exists agent_session_context")
