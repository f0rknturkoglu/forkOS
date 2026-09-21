"""H7 kalıcı plan/karar/yürütme tabloları.

Revision ID: 0061_execution
Revises: 0060_proactivity
Create Date: 2026-09-21

Üç tablo:
  execution_plan      bir satır = bir IMMUTABLE plan revizyonu (soy ağacı: plan_id)
  execution_receipt   adım başına TEK makbuz (append-only, idempotans çapası)
  execution_decision  append-only karar/yürütme denetim izi

Neden entity FK'si YOK: bunlar `source_run`/`proactivity_run` ile aynı sınıf
OPERASYONEL ajan/iş akışı kaydıdır; bağımsız aranabilir/linklenebilir nesne
değildir. Plan adımlarının hedef entity'leri JSONB adım gövdesinde referans
olarak durur, FK olarak DEĞİL: hedef silinse bile "ne yapılmak istendi"
tarihi okunabilir kalmalı.
"""

from alembic import op

revision = "0061_execution"
down_revision = "0060_proactivity"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    create table execution_plan (
      id                  bigserial primary key,
      plan_id             uuid not null,
      revision            varchar(80) not null,
      supersedes_revision varchar(80),
      state               varchar(24) not null default 'draft',
      title               text not null,
      summary             text,
      reason              text,
      steps               jsonb not null default '[]'::jsonb,
      step_count          integer not null default 0,
      mutation_count      integer not null default 0,
      budget              jsonb not null default '{}'::jsonb,
      source_refs         jsonb not null default '[]'::jsonb,
      evidence_refs       jsonb not null default '[]'::jsonb,
      validation_status   varchar(16) not null default 'pending',
      validation_errors   jsonb not null default '[]'::jsonb,
      input_questions     jsonb not null default '[]'::jsonb,
      input_answers       jsonb not null default '{}'::jsonb,
      approved_at         timestamptz,
      approved_revision   varchar(80),
      decided_by          varchar(32),
      rejected_at         timestamptz,
      cancelled_at        timestamptz,
      expires_at          timestamptz,
      execution_started_at timestamptz,
      execution_finished_at timestamptz,
      executor_token      varchar(64),
      final_status        varchar(16),
      failure_code        varchar(48),
      created_at          timestamptz not null default now(),
      updated_at          timestamptz not null default now(),
      constraint execution_plan_state_valid check (state in (
        'draft', 'validating', 'input_required', 'awaiting_approval', 'approved',
        'executing', 'completed', 'partial', 'failed', 'rejected', 'cancelled',
        'expired'
      )),
      constraint execution_plan_counts_non_negative
        check (step_count >= 0 and mutation_count >= 0)
    )
    """,
    # Ayni planin ayni revizyonu IKI KEZ satir acamaz (deterministik kimlik).
    "create unique index execution_plan_revision_uniq on execution_plan (plan_id, revision)",
    "create index ix_execution_plan_lineage on execution_plan (plan_id, created_at desc)",
    # Karar yuzeyi ve yurutme claim'i bu indeksleri kullanir.
    "create index ix_execution_plan_state on execution_plan (state, expires_at)",
    "create index ix_execution_plan_expiry on execution_plan (expires_at) where expires_at is not null",
    """
    create table execution_receipt (
      id               bigserial primary key,
      plan_row_id      bigint not null references execution_plan(id) on delete cascade,
      step_id          varchar(48) not null,
      ordinal          integer not null,
      action           varchar(48) not null,
      target           text,
      idempotency_key  varchar(120) not null,
      status           varchar(16) not null,
      error_code       varchar(48),
      result_ref       text,
      detail           text,
      started_at       timestamptz not null,
      completed_at     timestamptz,
      created_at       timestamptz not null default now(),
      claimed_by       varchar(64),
      constraint execution_receipt_status_valid check (status in (
        'completed', 'failed', 'skipped', 'not_attempted'
      ))
    )
    """,
    # Adim basina TEK makbuz: restart sonrasi ayni adim korlemesine tekrarlanmaz.
    "create unique index execution_receipt_step_uniq on execution_receipt (plan_row_id, step_id)",
    "create index ix_execution_receipt_plan on execution_receipt (plan_row_id, ordinal)",
    """
    create table execution_decision (
      id          bigserial primary key,
      plan_id     uuid not null,
      plan_row_id bigint references execution_plan(id) on delete cascade,
      kind        varchar(32) not null,
      revision    varchar(80),
      detail      jsonb not null default '{}'::jsonb,
      actor       varchar(32) not null default 'system',
      is_current  boolean not null default true,
      at          timestamptz not null default now()
    )
    """,
    "create index ix_execution_decision_plan on execution_decision (plan_id, at desc)",
    "create index ix_execution_decision_row on execution_decision (plan_row_id, at desc)",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("drop table if exists execution_decision cascade")
    op.execute("drop table if exists execution_receipt cascade")
    op.execute("drop table if exists execution_plan cascade")
