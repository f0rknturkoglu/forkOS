from collections.abc import AsyncIterator
from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity
from app.db import SessionLocal
from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.errors import CareerOpsSecurityError
from app.integrations.career_ops.runner import SubprocessCareerOpsRunner
from tests.agent_test_utils import capture_db_content_fingerprint


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_workspace_isolation_does_not_write_upstream_tracker(tmp_path: Path):
    """Verify adapter operates purely in-memory and in isolated workspace without writing upstream trackers."""
    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
    )
    doc = await adapter.doctor()
    assert doc is not None
    caps = await adapter.capabilities()
    assert len(caps) > 0

    # Ensure no tracker files were written to repo or unexpected paths
    assert not (tmp_path / "data" / "applications.md").exists()
    assert not (tmp_path / "data" / "pipeline.md").exists()
    assert not (tmp_path / "runtime" / "applications.md").exists()
    assert not (tmp_path / "runtime" / "pipeline.md").exists()


@pytest.mark.asyncio
async def test_doctor_causes_zero_canonical_db_mutations(db_session: AsyncSession, tmp_path: Path):
    """Verify doctor and capability probes cause ZERO mutations in canonical PostgreSQL tables."""
    # Seed baseline entity so database is non-trivial
    entity = await create_entity(db_session, type="opportunity", title="Baseline Career Opportunity")
    await db_session.commit()

    fp_before = await capture_db_content_fingerprint(db_session)

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
    )
    doc = await adapter.doctor()
    assert doc is not None
    caps = await adapter.capabilities()
    assert len(caps) > 0

    fp_after = await capture_db_content_fingerprint(db_session)
    assert fp_before == fp_after, "Canonical database fingerprint changed during career-ops doctor/capability probe"


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_runner_security_rejections():
    runner = SubprocessCareerOpsRunner(
        checkout_dir=Path("/tmp"),
        runtime_dir=Path("/tmp/runtime"),
    )
    unallowlisted = [
        "scan.mjs",
        "scan-ats-full.mjs",
        "update-system.mjs",
        "set-status.mjs",
        "arbitrary.sh",
        "tracker.mjs",
    ]
    for script in unallowlisted:
        with pytest.raises(CareerOpsSecurityError):
            await runner.run_script(script, [])
