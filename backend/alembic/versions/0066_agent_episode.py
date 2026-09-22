"""A3: source-bound episodic oturum devri destek tabloları.

Üç tablo da A1/A2 gibi operasyonel destek kayıtlarıdır: bağımsız aranabilir
veya linklenebilir entity DEĞİLDİR. Hiçbirinde ham transkript kolonu yoktur;
yalnız türetilmiş, sınırlı ve kaynağa bağlanabilen ifadeler saklanır.

Revision ID: 0066_agent_episode
Revises: 0065_continuity_scope
"""

from alembic import op

revision = "0066_agent_episode"
down_revision = "0065_continuity_scope"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    create table agent_session_episode (
        id bigserial primary key,
        session_id bigint not null references agent_session(id) on delete cascade,
        schema_version integer not null default 1,
        status varchar(24) not null default 'draft',
        scope_project varchar(64),
        started_at timestamptz not null,
        sealed_at timestamptz,
        turn_count integer not null default 0,
        item_count integer not null default 0,
        degraded_reasons jsonb not null default '[]'::jsonb,
        expires_at timestamptz not null,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now(),
        constraint uq_agent_session_episode_session unique (session_id),
        constraint ck_agent_session_episode_status
            check (status in ('draft', 'sealed', 'sealed_degraded', 'sealed_empty')),
        constraint ck_agent_session_episode_counts
            check (turn_count >= 0 and item_count >= 0),
        constraint ck_agent_session_episode_sealed_at
            check ((status = 'draft') = (sealed_at is null))
    )
    """,
    """
    create table agent_session_episode_turn (
        id bigserial primary key,
        episode_id bigint not null references agent_session_episode(id) on delete cascade,
        turn_id bigint references agent_session_turn(id) on delete cascade,
        turn_key varchar(64) not null,
        status varchar(24) not null default 'pending',
        turn_digest varchar(64),
        item_count integer not null default 0,
        delivered_refs jsonb not null default '[]'::jsonb,
        degraded_reasons jsonb not null default '[]'::jsonb,
        delivered_at timestamptz not null,
        observed_at timestamptz,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now(),
        constraint uq_agent_session_episode_turn_identity unique (episode_id, turn_key),
        constraint ck_agent_session_episode_turn_status
            check (status in ('pending', 'extracted', 'degraded')),
        constraint ck_agent_session_episode_turn_items
            check (item_count >= 0 and item_count <= 6),
        constraint ck_agent_session_episode_turn_digest
            check (status <> 'extracted' or turn_digest is not null)
    )
    """,
    """
    create table agent_session_episode_item (
        id bigserial primary key,
        episode_id bigint not null references agent_session_episode(id) on delete cascade,
        episode_turn_id bigint references agent_session_episode_turn(id) on delete cascade,
        ordinal integer not null,
        kind varchar(24) not null,
        text varchar(300) not null,
        evidence_class varchar(32) not null,
        support_refs jsonb not null default '[]'::jsonb,
        created_at timestamptz not null default now(),
        constraint ck_agent_session_episode_item_kind
            check (kind in ('topic', 'outcome', 'open_thread', 'session_decision', 'next_focus', 'reference')),
        constraint ck_agent_session_episode_item_evidence
            check (evidence_class in ('turn_derived', 'canonical_supported', 'observed_during_session')),
        constraint ck_agent_session_episode_item_ordinal check (ordinal >= 0),
        constraint ck_agent_session_episode_item_text check (char_length(text) between 1 and 300),
        constraint ck_agent_session_episode_item_turn_binding
            check (
                (evidence_class in ('turn_derived', 'canonical_supported') and episode_turn_id is not null)
                or (evidence_class = 'observed_during_session' and episode_turn_id is null)
            ),
        constraint ck_agent_session_episode_item_observed_evidence
            check (
                evidence_class <> 'observed_during_session'
                or jsonb_array_length(support_refs) > 0
            )
    )
    """,
    "create index ix_agent_session_episode_status_sealed on agent_session_episode (status, sealed_at desc)",
    "create index ix_agent_session_episode_expires on agent_session_episode (expires_at)",
    "create index ix_agent_session_episode_item_episode_ordinal on agent_session_episode_item (episode_id, ordinal)",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("drop table if exists agent_session_episode_item")
    op.execute("drop table if exists agent_session_episode_turn")
    op.execute("drop table if exists agent_session_episode")
