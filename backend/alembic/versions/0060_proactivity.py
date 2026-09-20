"""H6 proaktivite kalici durumu (kural + kosu).

Revision ID: 0060_proactivity
Revises: 0059_note_attachment
Create Date: 2026-09-21

Iki tablo: kullaniciya ait kural konfigurasyonu ve motorun kosu gecmisi.

Neden entity FK'si YOK: bunlar bagimsiz aranabilir/linklenebilir nesne
degil, `source_run`/`source_sync_batch` ile ayni siniftan OPERASYONEL
kayittir. `subject_id` bilincli olarak FK'sizdir: entity silinse bile
"neden o gun durtuldu" tarihi okunabilir kalmali.

`logical_trigger_key` UNIQUE'tir: idempotans veritabaninda zorlanir, yalnizca
zamanlayicinin `max_instances=1` davranisina guvenilmez.
"""

from alembic import op

revision = "0060_proactivity"
down_revision = "0059_note_attachment"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    create table proactivity_rule (
      id              bigserial primary key,
      kind            varchar(48) not null,
      version         integer not null default 1,
      logical_key     text not null,
      enabled         boolean not null default true,
      scope_entity_id uuid references entity(id) on delete cascade,
      config          jsonb not null default '{}'::jsonb,
      snoozed_until   timestamptz,
      created_at      timestamptz not null default now(),
      updated_at      timestamptz not null default now()
    )
    """,
    "create unique index proactivity_rule_key_uniq on proactivity_rule (logical_key)",
    "create index ix_proactivity_rule_kind on proactivity_rule (kind, enabled)",
    """
    create table proactivity_run (
      id                  bigserial primary key,
      rule_id             bigint not null references proactivity_rule(id) on delete cascade,
      logical_trigger_key text not null,
      state               varchar(16) not null default 'candidate',
      reason_codes        jsonb not null default '[]'::jsonb,
      why_now             text,
      subject_type        varchar(48),
      subject_id          uuid,
      triggered_at        timestamptz not null,
      evaluated_at        timestamptz,
      deferred_until      timestamptz,
      last_delivered_at   timestamptz,
      delivery_count      integer not null default 0,
      snoozed_until       timestamptz,
      resolved_at         timestamptz,
      cancelled_at        timestamptz,
      notification_id     bigint references notification(id) on delete set null,
      failure_code        varchar(48),
      created_at          timestamptz not null default now(),
      updated_at          timestamptz not null default now(),
      constraint proactivity_run_state_valid check (state in (
        'candidate', 'suppressed', 'deferred', 'digest_queued', 'delivered',
        'snoozed', 'dismissed', 'resolved', 'cancelled', 'failed'
      )),
      constraint proactivity_run_delivery_count_non_negative check (delivery_count >= 0)
    )
    """,
    # Idempotans: ayni mantiksal tetik ikinci kez satir ACAMAZ.
    "create unique index proactivity_run_trigger_uniq on proactivity_run (logical_trigger_key)",
    # Bekleyen teslimler (ertelenen + digest kuyrugu) her turda taranir.
    """
    create index ix_proactivity_run_pending on proactivity_run (state, deferred_until)
      where state in ('candidate', 'deferred', 'digest_queued', 'snoozed')
    """,
    "create index ix_proactivity_run_snoozed on proactivity_run (snoozed_until) where snoozed_until is not null",
    "create index ix_proactivity_run_rule on proactivity_run (rule_id, created_at desc)",
    "create index ix_proactivity_run_notification on proactivity_run (notification_id)",
    # Budama `created_at`e gore; terminal durumlar disinda silinmez.
    "create index ix_proactivity_run_created on proactivity_run (created_at)",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("drop table if exists proactivity_run cascade")
    op.execute("drop table if exists proactivity_rule cascade")
