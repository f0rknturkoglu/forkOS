"""Legacy evaluation payloads retain their identity across the 0075 split."""

from __future__ import annotations

import runpy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import text

from app.core.entity import create_entity
from app.db import SessionLocal, engine
from app.modules.opportunity.models import Opportunity


async def test_split_evaluations_migrates_known_shapes_and_preserves_unknown():
    migration = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "alembic/versions/0075_split_evaluations.py")
    )
    timestamp = datetime(2026, 9, 28, tzinfo=UTC)
    payloads = [
        {"version": "career-ops-v1", "score": 78, "recommendation": "pursue", "requirements": []},
        {"candidate_context_revision": "rev-1", "overall_assessment": "Good match"},
        {"unknown_legacy_format": True},
    ]
    ids = []
    async with SessionLocal() as session:
        for index, payload in enumerate(payloads):
            entity = await create_entity(session, type="opportunity", title=f"Migration {index}")
            session.add(
                Opportunity(
                    id=entity.id,
                    kind="job",
                    found_at=timestamp,
                    legacy_evaluation=payload,
                    legacy_evaluated_at=timestamp,
                )
            )
            ids.append(entity.id)
        await session.commit()

    def invoke(connection, direction: str) -> None:
        migration[direction].__globals__["op"] = SimpleNamespace(
            execute=lambda sql: connection.execute(text(sql)),
            get_bind=lambda: connection,
        )
        migration[direction]()

    async with engine.begin() as connection:
        await connection.run_sync(invoke, "downgrade")
        await connection.run_sync(invoke, "upgrade")

    async with SessionLocal() as session:
        rows = [await session.get(Opportunity, item_id) for item_id in ids]
        assert all(row is not None for row in rows)
        assert [row.legacy_evaluation for row in rows] == payloads
        assert [row.legacy_evaluated_at for row in rows] == [timestamp] * 3
        assert rows[0].candidate_evaluation == payloads[0]
        assert rows[0].deep_evaluation is None
        assert rows[1].candidate_evaluation is None
        assert rows[1].deep_evaluation == payloads[1]
        assert rows[2].candidate_evaluation is None
        assert rows[2].deep_evaluation is None
