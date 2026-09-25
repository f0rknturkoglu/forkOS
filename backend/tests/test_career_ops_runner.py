import pytest
from app.integrations.career_ops.errors import (
    CareerOpsSecurityError,
    CareerOpsTimeoutError,
)
from app.integrations.career_ops.runner import SubprocessCareerOpsRunner


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_runner_security_rejects_unallowlisted(tmp_path):
    runner = SubprocessCareerOpsRunner(
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        node_bin="node",
    )
    with pytest.raises(CareerOpsSecurityError):
        await runner.run_script("malicious.mjs", [])


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_runner_executes_allowlisted_script(tmp_path):
    # Create fake doctor.mjs in tmp checkout
    script_path = tmp_path / "doctor.mjs"
    script_path.write_text('console.log(JSON.stringify({ok: true}));\n')

    runner = SubprocessCareerOpsRunner(
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        node_bin="node",
    )
    result = await runner.run_script("doctor.mjs", ["--json"])
    assert result.exit_code == 0
    assert '"ok":true' in result.stdout
    assert (tmp_path / "runtime" / "generated-input").exists()
    assert (tmp_path / "runtime" / "temporary-output").exists()
    assert (tmp_path / "runtime" / "cache").exists()
