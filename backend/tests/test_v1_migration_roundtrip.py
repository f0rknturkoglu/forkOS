"""Real PostgreSQL 16 downgrade/re-upgrade and portable restore; isolated test DB only."""

import asyncio
import subprocess
from uuid import uuid4

from sqlalchemy import select, text

from app.config import settings
from app.core.entity import create_entity
from app.db import Base, SessionLocal
from app.modules.bookmark.receipts import CaptureReceipt
from app.modules.goal import studio
from app.modules.goal.studio_models import GoalStudioRevision, GoalStudioSession
from app.modules.goal.studio_schemas import StudioProposal, StudioSessionIn
from app.modules.system import export, restore


async def migration(*args):
    def run():
        subprocess.run(["alembic", *args], check=True, capture_output=True, text=True)

    await asyncio.to_thread(run)


async def test_real_0080_noop_downgrade_upgrade_and_backup_restore_preserve_workflows():
    assert settings.database_url.rsplit("/", 1)[-1].endswith("_test")
    async with SessionLocal() as db:
        item = await studio.start(db, StudioSessionIn(client_uuid=uuid4()))
        draft = await studio.revise(
            db,
            await studio.get_session(db, item.id),
            StudioProposal.model_validate(
                {
                    "rationale": "migration sentinel",
                    "operations": [
                        {
                            "type": "goal.create",
                            "key": "goal",
                            "data": {"title": "Synthetic retained draft"},
                        }
                    ],
                }
            ),
        )
        entity = await create_entity(db, type="capture_receipt", title="Synthetic durable receipt")
        receipt_id = entity.id
        db.add(
            CaptureReceipt(
                id=receipt_id,
                client_uuid=uuid4(),
                fingerprint="a" * 64,
                destination="todo",
                result={"retained": True},
            )
        )
        row = await db.get(GoalStudioSession, item.id)
        row.data = {
            **row.data,
            "runtime": {"provider": "custom", "model": "sentinel"},
            "turns": {"sentinel": {"policy_id": "b" * 64, "request": {"input": "bounded"}}},
        }
        await db.commit()
        payload = await export.full_json(db)
    await migration("downgrade", "0079_retire_media_batches")
    async with SessionLocal() as db:
        assert (
            await db.scalar(text("SELECT version_num FROM alembic_version"))
            == "0079_retire_media_batches"
        )
        assert await db.get(CaptureReceipt, receipt_id)
        assert (
            await db.get(GoalStudioRevision, draft.revision.id)
        ).fingerprint == draft.revision.fingerprint
    await migration("upgrade", "head")
    async with SessionLocal() as db:
        assert (
            await db.scalar(text("SELECT version_num FROM alembic_version"))
            == "0081_goal_roadmap"
        )
        before = (await db.get(GoalStudioSession, item.id)).data
        assert before["runtime"]["model"] == "sentinel"
        names = ", ".join('"' + t.name + '"' for t in reversed(Base.metadata.sorted_tables))
        await db.execute(text("TRUNCATE TABLE " + names + " RESTART IDENTITY CASCADE"))
        await db.commit()
        await restore.restore(db, payload)
        restored = await db.get(GoalStudioSession, item.id, populate_existing=True)
        assert restored.data == before
        assert (
            await db.get(GoalStudioRevision, draft.revision.id)
        ).fingerprint == draft.revision.fingerprint
        assert (await db.get(CaptureReceipt, receipt_id)).result == {"retained": True}
        ids = set((await db.scalars(select(GoalStudioSession.id))).all())
        assert item.id in ids
