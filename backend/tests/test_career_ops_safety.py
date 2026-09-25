from pathlib import Path
import pytest
from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.errors import CareerOpsSecurityError
from app.integrations.career_ops.runner import SubprocessCareerOpsRunner


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_zero_canonical_mutation(tmp_path):
    # Verify adapter operates purely in-memory and in isolated workspace
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
