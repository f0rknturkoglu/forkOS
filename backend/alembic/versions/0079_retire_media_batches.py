"""Retire orphaned Media work without executing or deleting its history."""

from alembic import op

revision = "0079_retire_media_batches"
down_revision = "0078_pomodoro_source"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""update source_run r set status = 'abandoned', finished_at = now(),
        error = concat_ws(' | ', r.error, 'V1: Media synchronization retired'),
        error_kind = 'unknown'
        where r.status = 'running' and r.batch_id in
        (select id from source_sync_batch where scope = 'media')""")
    op.execute("""with retired as (
        update source_sync_batch set status = 'completed_with_errors', finished_at = now()
        where scope = 'media' and status in ('queued', 'running') returning id, scope
        ) insert into event (entity_type, verb, payload, occurred_at)
        select 'source_sync_batch', 'source_sync.retired',
        jsonb_build_object('batch_id', id, 'scope', scope,
            'reason', 'V1: Media synchronization retired'), now() from retired""")


def downgrade():
    # Retirement is an operational fact, not a reversible schema change.
    # Never resurrect jobs or remove append-only audit events.
    pass
