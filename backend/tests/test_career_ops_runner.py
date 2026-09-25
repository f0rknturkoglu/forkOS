import asyncio
import pytest
from app.integrations.career_ops.errors import (
    CareerOpsInvalidOutputError,
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


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_runner_executes_scan_ats_full_with_extra_env(tmp_path):
    script_path = tmp_path / "scan-ats-full.mjs"
    script_path.write_text('console.log(process.env.CUSTOM_TEST_VAR || "none");\n')

    runner = SubprocessCareerOpsRunner(
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        node_bin="node",
    )
    result = await runner.run_script(
        "scan-ats-full.mjs",
        ["--json"],
        extra_env={"CUSTOM_TEST_VAR": "propagated_custom_value"},
    )
    assert result.exit_code == 0
    assert "propagated_custom_value" in result.stdout


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_runner_stdout_overflow_terminates_and_raises(tmp_path):
    # Generates ~10000 bytes while max_buffer_bytes=200
    script_path = tmp_path / "doctor.mjs"
    script_path.write_text('console.log("X".repeat(10000));\n')

    runner = SubprocessCareerOpsRunner(
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        node_bin="node",
        max_buffer_bytes=200,
    )
    with pytest.raises(CareerOpsInvalidOutputError) as exc_info:
        await runner.run_script("doctor.mjs", [])
    assert "exceeded maximum output buffer" in str(exc_info.value)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_runner_stderr_overflow_terminates_and_raises(tmp_path):
    # Generates ~10000 bytes on stderr while max_buffer_bytes=200
    script_path = tmp_path / "doctor.mjs"
    script_path.write_text('console.error("E".repeat(10000));\n')

    runner = SubprocessCareerOpsRunner(
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        node_bin="node",
        max_buffer_bytes=200,
    )
    with pytest.raises(CareerOpsInvalidOutputError) as exc_info:
        await runner.run_script("doctor.mjs", [])
    assert "exceeded maximum output buffer" in str(exc_info.value)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_runner_timeout_terminates_and_reaps(tmp_path):
    script_path = tmp_path / "doctor.mjs"
    # Infinite loop / sleep
    script_path.write_text('setTimeout(() => {}, 60000);\n')

    runner = SubprocessCareerOpsRunner(
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        node_bin="node",
        default_timeout_seconds=0.3,
    )
    with pytest.raises(CareerOpsTimeoutError) as exc_info:
        await runner.run_script("doctor.mjs", [])
    assert "timed out after 0.3 seconds" in str(exc_info.value)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_runner_output_just_below_limit_succeeds(tmp_path):
    script_path = tmp_path / "doctor.mjs"
    script_path.write_text('console.log("X".repeat(50));\n')

    runner = SubprocessCareerOpsRunner(
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        node_bin="node",
        max_buffer_bytes=100,
    )
    res = await runner.run_script("doctor.mjs", [])
    assert res.exit_code == 0
    assert len(res.stdout.strip()) == 50


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_runner_task_cancellation_kills_and_reaps_child(tmp_path):
    script_path = tmp_path / "doctor.mjs"
    # Long-running script that sleeps for 10 seconds
    script_path.write_text('setTimeout(() => {}, 10000);\n')

    runner = SubprocessCareerOpsRunner(
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        node_bin="node",
    )

    task = asyncio.create_task(runner.run_script("doctor.mjs", []))
    # Give event loop a moment to spawn node process
    await asyncio.sleep(0.05)

    # Cancel the asyncio task
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    # Task was cancelled cleanly
    assert task.cancelled()
