"""Opportunity trash lifecycle and persistent source sync batches."""

from alembic import op

revision = "0018_opportunity_trash_sync"
down_revision = "0017_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table opportunity add column trashed_at timestamptz")
    op.execute("alter table opportunity add column trashed_from_status text")
    op.execute(
        "create index opportunity_trash_idx on opportunity (trashed_at desc) "
        "where trashed_at is not null"
    )
    op.execute(
        """create table source_sync_batch (
          id uuid primary key default gen_random_uuid(),
          status text not null default 'queued',
          source_ids jsonb not null default '[]',
          total_sources int not null default 0,
          completed_sources int not null default 0,
          ok_sources int not null default 0,
          empty_sources int not null default 0,
          error_sources int not null default 0,
          items_found int not null default 0,
          created_at timestamptz not null default now(),
          started_at timestamptz,
          finished_at timestamptz
        )"""
    )
    op.execute(
        "create index source_sync_batch_time_idx on source_sync_batch (created_at desc)"
    )
    op.execute(
        "alter table source_run add column batch_id uuid "
        "references source_sync_batch(id) on delete set null"
    )
    op.execute("create index source_run_batch_idx on source_run (batch_id, started_at)")


def downgrade() -> None:
    op.execute("drop index if exists source_run_batch_idx")
    op.execute("alter table source_run drop column if exists batch_id")
    op.execute("drop table if exists source_sync_batch")
    op.execute("drop index if exists opportunity_trash_idx")
    op.execute("alter table opportunity drop column if exists trashed_from_status")
    op.execute("alter table opportunity drop column if exists trashed_at")
