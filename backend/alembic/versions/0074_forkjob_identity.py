"""Rename persisted forkjob source IDs without discarding observation history."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0074_forkjob_identity"
down_revision = "0073_career_strategy_goals"
branch_labels = None
depends_on = None

OLD_PREFIX = "jobhunter:"
NEW_PREFIX = "forkjob_core:"


def _rewrite(value, old_prefix: str, new_prefix: str):
    if isinstance(value, str):
        return new_prefix + value[len(old_prefix):] if value.startswith(old_prefix) else value
    if isinstance(value, list):
        return [_rewrite(item, old_prefix, new_prefix) for item in value]
    if isinstance(value, dict):
        return {key: _rewrite(item, old_prefix, new_prefix) for key, item in value.items()}
    return value


def _rename(value):
    return _rewrite(value, OLD_PREFIX, NEW_PREFIX)


def _earliest(*values):
    available = [value for value in values if value is not None]
    return min(available) if available else None


def _latest(*values):
    available = [value for value in values if value is not None]
    return max(available) if available else None


def _migrate_observations(bind) -> None:
    legacy_rows = bind.execute(
        text("select * from opportunity_source_observation where source like 'jobhunter:%'")
    ).mappings().all()
    update_enrichment = text(
        """update opportunity_source_observation set
            external_id = :external_id,
            canonical_url = :canonical_url,
            payload_hash = :payload_hash,
            source_status = :source_status,
            first_seen_at = :first_seen_at,
            last_seen_at = :last_seen_at,
            last_successful_seen_at = :last_successful_seen_at,
            source_published_at = :source_published_at,
            source_removed_at = :source_removed_at,
            enrichment = :enrichment
           where id = :id"""
    ).bindparams(bindparam("enrichment", type_=JSONB))
    for old in legacy_rows:
        new_source = _rename(old["source"])
        current = bind.execute(
            text(
                """select * from opportunity_source_observation
                   where opportunity_id = :opportunity_id and source = :source"""
            ),
            {"opportunity_id": old["opportunity_id"], "source": new_source},
        ).mappings().first()
        if current is None:
            bind.execute(
                text("update opportunity_source_observation set source = :source where id = :id"),
                {"source": new_source, "id": old["id"]},
            )
            continue

        # The canonical row survives. Conflicting legacy fields remain in its
        # enrichment payload so no source evidence silently disappears.
        enrichment = dict(current["enrichment"] or {})
        history = list(enrichment.get("legacy_source_observations") or [])
        history.append(
            {
                key: value.isoformat() if hasattr(value, "isoformat") else str(value)
                if key in {"id", "opportunity_id"} else value
                for key, value in old.items()
            }
        )
        enrichment["legacy_source_observations"] = history
        latest = (
            current
            if old["last_seen_at"] is None
            or (
                current["last_seen_at"] is not None
                and current["last_seen_at"] >= old["last_seen_at"]
            )
            else old
        )
        bind.execute(
            update_enrichment,
            {
                "id": current["id"],
                "external_id": current["external_id"] or old["external_id"],
                "canonical_url": current["canonical_url"] or old["canonical_url"],
                "payload_hash": latest["payload_hash"],
                "source_status": "active"
                if "active" in {current["source_status"], old["source_status"]}
                else latest["source_status"],
                "first_seen_at": _earliest(current["first_seen_at"], old["first_seen_at"]),
                "last_seen_at": _latest(current["last_seen_at"], old["last_seen_at"]),
                "last_successful_seen_at": _latest(
                    current["last_successful_seen_at"], old["last_successful_seen_at"]
                ),
                "source_published_at": _earliest(
                    current["source_published_at"], old["source_published_at"]
                ),
                "source_removed_at": _latest(
                    current["source_removed_at"], old["source_removed_at"]
                ),
                "enrichment": enrichment,
            },
        )
        bind.execute(
            text("delete from opportunity_source_observation where id = :id"),
            {"id": old["id"]},
        )


def _migrate_json(bind, table: str, key: str, value: str, transform=_rename) -> None:
    rows = bind.execute(text(f"select {key}, {value} from {table}")).mappings().all()
    statement = text(f"update {table} set {value} = :value where {key} = :key").bindparams(
        bindparam("value", type_=JSONB)
    )
    for row in rows:
        renamed = transform(row[value])
        if renamed != row[value]:
            bind.execute(statement, {"key": row[key], "value": renamed})


def _migrate_batches(bind) -> None:
    batches = bind.execute(text("select * from source_sync_batch")).mappings().all()
    update_ids = text(
        "update source_sync_batch set source_ids = :source_ids where id = :id"
    ).bindparams(bindparam("source_ids", type_=JSONB))
    update_collision = text(
        """update source_sync_batch set
            source_ids = :source_ids,
            total_sources = :total_sources,
            completed_sources = :completed_sources,
            ok_sources = :ok_sources,
            partial_sources = :partial_sources,
            empty_sources = :empty_sources,
            error_sources = :error_sources,
            items_found = :items_found,
            status = :status,
            finished_at = :finished_at
           where id = :id"""
    ).bindparams(bindparam("source_ids", type_=JSONB))
    terminal = {"ok", "partial", "empty", "error"}
    for batch in batches:
        original = batch["source_ids"] or []
        renamed = _rename(original)
        if renamed == original:
            continue
        unique = list(dict.fromkeys(renamed))
        if len(unique) == len(renamed):
            bind.execute(update_ids, {"id": batch["id"], "source_ids": unique})
            continue

        runs = bind.execute(
            text(
                """select source, status, items_found from source_run
                   where batch_id = :batch_id order by started_at desc, id desc"""
            ),
            {"batch_id": batch["id"]},
        ).mappings()
        latest = {}
        for run in runs:
            if run["source"] in unique and run["status"] in terminal:
                latest.setdefault(run["source"], run)
        counts = {status: sum(run["status"] == status for run in latest.values()) for status in terminal}
        complete = len(latest) == len(unique)
        status = batch["status"]
        if complete and status in {"queued", "running", "completed", "completed_with_errors"}:
            status = "completed_with_errors" if counts["error"] else "completed"
        bind.execute(
            update_collision,
            {
                "id": batch["id"],
                "source_ids": unique,
                "total_sources": len(unique),
                "completed_sources": len(latest),
                "ok_sources": counts["ok"],
                "partial_sources": counts["partial"],
                "empty_sources": counts["empty"],
                "error_sources": counts["error"],
                "items_found": sum(run["items_found"] or 0 for run in latest.values()),
                "status": status,
                "finished_at": batch["finished_at"] or datetime.now(UTC) if complete else batch["finished_at"],
            },
        )


def upgrade() -> None:
    bind = op.get_bind()
    _migrate_observations(bind)
    bind.execute(
        text(
            """update opportunity set source = 'forkjob_core:' || substring(source from 11)
               where source like 'jobhunter:%'"""
        )
    )
    bind.execute(
        text(
            """update source_run set source = 'forkjob_core:' || substring(source from 11)
               where source like 'jobhunter:%'"""
        )
    )
    _migrate_json(bind, "opportunity", "id", "raw")
    _migrate_batches(bind)
    _migrate_json(bind, "setting", "key", "value")


def downgrade() -> None:
    bind = op.get_bind()
    # Non-colliding databases can round-trip. A collision consolidated two
    # observation rows, so stop instead of pretending that reversing a label
    # reconstructs the deleted row. The archive remains in enrichment.
    collision_count = bind.execute(
        text(
            """select count(*) from opportunity_source_observation
               where enrichment ? 'legacy_source_observations'"""
        )
    ).scalar_one()
    if collision_count:
        raise RuntimeError("forkjob_core collision history requires manual restoration")

    def restore(value):
        return _rewrite(value, NEW_PREFIX, OLD_PREFIX)
    bind.execute(
        text(
            """update opportunity_source_observation
               set source = 'jobhunter:' || substring(source from 14)
               where source like 'forkjob_core:%'"""
        )
    )
    bind.execute(
        text(
            """update opportunity set source = 'jobhunter:' || substring(source from 14)
               where source like 'forkjob_core:%'"""
        )
    )
    bind.execute(
        text(
            """update source_run set source = 'jobhunter:' || substring(source from 14)
               where source like 'forkjob_core:%'"""
        )
    )
    _migrate_json(bind, "opportunity", "id", "raw", restore)
    _migrate_json(bind, "source_sync_batch", "id", "source_ids", restore)
    _migrate_json(bind, "setting", "key", "value", restore)
