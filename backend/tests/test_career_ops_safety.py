import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity
from app.db import SessionLocal
from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.config import (
    CAREER_OPS_PINNED_COMMIT,
    CAREER_OPS_PINNED_VERSION,
    CAREER_OPS_UPSTREAM_REPO,
)
from app.integrations.career_ops.errors import CareerOpsSecurityError
from app.integrations.career_ops.guard import CareerOpsRuntimeGuard
from app.integrations.career_ops.models import (
    CareerOpsIdentity,
)
from app.integrations.career_ops.runner import (
    CareerOpsRunner,
    ExecutionResult,
    SubprocessCareerOpsRunner,
)
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
    await create_entity(db_session, type="opportunity", title="Baseline Career Opportunity")
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


@pytest.mark.asyncio
async def test_doctor_ready_path_causes_zero_canonical_db_mutations(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify that doctor and capability probes reaching the READY path cause ZERO DB mutations."""
    await create_entity(
        db_session, type="opportunity", title="Baseline Career Opportunity for Ready Probe"
    )
    await db_session.commit()

    fp_before = await capture_db_content_fingerprint(db_session)

    checkout_dir = tmp_path / "checkout"
    checkout_dir.mkdir(parents=True)
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)

    (checkout_dir / "package.json").write_text(
        json.dumps({"name": "career-ops", "version": CAREER_OPS_PINNED_VERSION}),
        encoding="utf-8",
    )
    (checkout_dir / "doctor.mjs").write_text("// dummy doctor", encoding="utf-8")
    (checkout_dir / "path-resolver.mjs").write_text("// dummy resolver", encoding="utf-8")

    class ReadyMockRunner(CareerOpsRunner):
        async def run_script(
            self, script_name: str, args: list[str], **kwargs: Any
        ) -> ExecutionResult:
            if script_name == "doctor.mjs":
                return ExecutionResult(
                    script_name=script_name,
                    exit_code=0,
                    stdout=json.dumps({"onboarding_status": "complete", "warnings": []}),
                    stderr="",
                )
            return ExecutionResult(script_name=script_name, exit_code=0, stdout="{}", stderr="")

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=checkout_dir,
        runtime_dir=runtime_dir,
        runner=ReadyMockRunner(),
    )
    monkeypatch.setattr(
        CareerOpsRuntimeGuard,
        "get_actual_identity",
        lambda self: (
            CareerOpsIdentity(
                repository=CAREER_OPS_UPSTREAM_REPO,
                version=CAREER_OPS_PINNED_VERSION,
                commit=CAREER_OPS_PINNED_COMMIT,
            ),
            None,
        ),
    )

    doc = await adapter.doctor()
    caps = await adapter.capabilities()
    assert len(caps) > 0
    supported_caps = [c for c in caps if c.status.value == "supported"]
    assert doc.capabilities_available == len(supported_caps)
    assert len(supported_caps) == 11


    fp_after = await capture_db_content_fingerprint(db_session)
    assert fp_before == fp_after, "Canonical database fingerprint changed during READY doctor probe"


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_runner_security_rejections():
    runner = SubprocessCareerOpsRunner(
        checkout_dir=Path("/tmp"),
        runtime_dir=Path("/tmp/runtime"),
    )
    from app.integrations.career_ops.runner import ALLOWLISTED_SCRIPTS
    assert "scan-ats-full.mjs" in ALLOWLISTED_SCRIPTS

    unallowlisted = [
        "scan.mjs",
        "update-system.mjs",
        "set-status.mjs",
        "arbitrary.sh",
        "tracker.mjs",
        "apply.mjs",
    ]
    for script in unallowlisted:
        with pytest.raises(CareerOpsSecurityError):
            await runner.run_script(script, [])
