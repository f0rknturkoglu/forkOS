from pathlib import Path

import pytest

from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.models import CareerOpsStatusEnum


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_doctor_disabled_status():
    adapter = CareerOpsAdapter(enabled=False)
    report = await adapter.doctor()
    assert report.status == CareerOpsStatusEnum.DISABLED


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_doctor_missing_checkout_status(tmp_path):
    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=tmp_path / "nonexistent",
        runtime_dir=tmp_path / "runtime",
    )
    report = await adapter.doctor()
    assert report.status == CareerOpsStatusEnum.UNAVAILABLE


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_doctor_version_mismatch(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"name": "career-ops", "version": "9.9.9"}')
    (tmp_path / "doctor.mjs").write_text('console.log("{}");')
    (tmp_path / "path-resolver.mjs").write_text('export {};')

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
    )
    report = await adapter.doctor()
    assert report.status == CareerOpsStatusEnum.VERSION_MISMATCH


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_doctor_commit_unknown_cannot_be_ready(tmp_path):
    # Valid version 1.34.0, but no .git directory -> commit is unknown
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"name": "career-ops", "version": "1.34.0"}')
    (tmp_path / "doctor.mjs").write_text('console.log("{}");')
    (tmp_path / "path-resolver.mjs").write_text('export {};')

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
    )
    report = await adapter.doctor()
    assert report.status == CareerOpsStatusEnum.MISCONFIGURED
    assert any("positively verified" in err for err in report.errors)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_doctor_separates_upstream_onboarding_and_does_not_pass_target_flag(tmp_path):
    # Mock runner to observe args passed to doctor.mjs
    captured_args = []

    class MockRunner:
        async def run_script(self, script_name, args, timeout_seconds=None):
            captured_args.extend(args)
            from app.integrations.career_ops.runner import ExecutionResult
            return ExecutionResult(
                script_name=script_name,
                exit_code=0,
                stdout='{"onboardingNeeded":true,"missing":["cv.md"],"warnings":["Playwright MCP tools not detected"],"unpersonalized":[{"path":"modes/_profile.md"}]}\n',
                stderr="",
            )

    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"name": "career-ops", "version": "1.34.0"}')
    (tmp_path / "doctor.mjs").write_text('console.log("{}");')
    (tmp_path / "path-resolver.mjs").write_text('export {};')

    # Create dummy git commit
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        runner=MockRunner(),
    )
    # Monkeypatch git check to return expected commit
    import subprocess
    orig_check_output = subprocess.check_output

    def mock_check_output(cmd, **kwargs):
        if "rev-parse" in cmd:
            return "6326eb5d3804e8cb20d28acd5701a4e603a301f9\n"
        return orig_check_output(cmd, **kwargs)

    subprocess.check_output = mock_check_output
    try:
        report = await adapter.doctor()
    finally:
        subprocess.check_output = orig_check_output

    # Crucial finding 1: --target must NOT be passed to doctor.mjs
    assert "--target" not in captured_args
    assert "--json" in captured_args

    # Integration is READY even if upstream user onboarding files (cv.md) are missing
    assert report.status == CareerOpsStatusEnum.READY
    assert report.upstream_onboarding is not None
    assert report.upstream_onboarding.onboarding_needed is True
    assert "cv.md" in report.upstream_onboarding.missing
    assert len(report.upstream_onboarding.warnings) == 1


@pytest.mark.no_database
def test_probe_browser_readiness(tmp_path: Path):
    from app.integrations.career_ops.doctor import probe_browser_readiness

    # Missing node_modules/playwright returns False
    assert probe_browser_readiness(tmp_path) is False
