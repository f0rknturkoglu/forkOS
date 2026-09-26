import json
from pathlib import Path
import subprocess
import pytest

from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.config import (
    CAREER_OPS_PINNED_COMMIT,
    CAREER_OPS_PINNED_VERSION,
)
from app.integrations.career_ops.errors import (
    CareerOpsConfigurationError,
    CareerOpsUnavailableError,
    CareerOpsVersionMismatchError,
)
from app.integrations.career_ops.runner import ExecutionResult


class TrackingMockRunner:
    def __init__(self):
        self.invoked = False
        self.last_script = None

    async def run_script(self, script_name, args, **kwargs):
        self.invoked = True
        self.last_script = script_name
        return ExecutionResult(
            script_name=script_name,
            exit_code=0,
            stdout='{"offers":[],"sinceDays":7,"companiesScanned":1,"capHit":false,"stoppedByOutage":false}',
            stderr="",
        )


def _setup_checkout(
    path: Path,
    version: str = CAREER_OPS_PINNED_VERSION,
    has_git: bool = True,
    has_script: bool = True,
):
    (path / "package.json").write_text(json.dumps({"name": "career-ops", "version": version}), encoding="utf-8")
    if has_git:
        git_dir = path / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)
    if has_script:
        (path / "scan-ats-full.mjs").write_text("// test", encoding="utf-8")


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_identity_gate_allows_correct_version_and_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _setup_checkout(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda cmd, **kwargs: CAREER_OPS_PINNED_COMMIT if "rev-parse" in cmd else "v22.5.0",
    )

    runner = TrackingMockRunner()
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=tmp_path, runner=runner)
    result = await adapter.reverse_scan("greenhouse")

    assert runner.invoked is True
    assert result.provider == "greenhouse"


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_identity_gate_blocks_wrong_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _setup_checkout(tmp_path, version="9.9.9")
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda cmd, **kwargs: CAREER_OPS_PINNED_COMMIT if "rev-parse" in cmd else "v22.5.0",
    )

    runner = TrackingMockRunner()
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=tmp_path, runner=runner)

    with pytest.raises(CareerOpsVersionMismatchError, match="Version mismatch"):
        await adapter.reverse_scan("greenhouse")

    # Scanner MUST NOT be invoked!
    assert runner.invoked is False


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_identity_gate_blocks_wrong_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _setup_checkout(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda cmd, **kwargs: "0000000000000000000000000000000000000000" if "rev-parse" in cmd else "v22.5.0",
    )

    runner = TrackingMockRunner()
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=tmp_path, runner=runner)

    with pytest.raises(CareerOpsVersionMismatchError, match="Commit mismatch"):
        await adapter.reverse_scan("greenhouse")

    assert runner.invoked is False


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_identity_gate_blocks_unknown_commit(tmp_path: Path):
    # has_git=False -> commit is unknown
    _setup_checkout(tmp_path, has_git=False)

    runner = TrackingMockRunner()
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=tmp_path, runner=runner)

    with pytest.raises(CareerOpsConfigurationError, match="Pinned commit SHA could not be positively verified"):
        await adapter.reverse_scan("greenhouse")

    assert runner.invoked is False


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_identity_gate_blocks_missing_package_json(tmp_path: Path):
    runner = TrackingMockRunner()
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=tmp_path, runner=runner)

    with pytest.raises(CareerOpsUnavailableError, match="missing"):
        await adapter.reverse_scan("greenhouse")

    assert runner.invoked is False


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_identity_gate_blocks_missing_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _setup_checkout(tmp_path, has_script=False)
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda cmd, **kwargs: CAREER_OPS_PINNED_COMMIT if "rev-parse" in cmd else "v22.5.0",
    )

    runner = TrackingMockRunner()
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=tmp_path, runner=runner)

    with pytest.raises(CareerOpsUnavailableError, match="scan-ats-full.mjs"):
        await adapter.reverse_scan("greenhouse")

    assert runner.invoked is False


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_discovery_feature_flag_blocks_execution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _setup_checkout(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda cmd, **kwargs: CAREER_OPS_PINNED_COMMIT if "rev-parse" in cmd else b"v22.5.0",
    )
    from app.config import settings
    monkeypatch.setattr(settings, "career_ops_discovery_enabled", False)

    runner = TrackingMockRunner()
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=tmp_path, runner=runner)

    with pytest.raises(CareerOpsConfigurationError, match="discovery capability is disabled"):
        await adapter.reverse_scan("greenhouse")

    assert runner.invoked is False


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_c3_liveness_identity_gate_blocks_wrong_commit_or_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _setup_checkout(tmp_path)
    (tmp_path / "liveness-api.mjs").write_text("// test", encoding="utf-8")
    (tmp_path / "liveness-browser.mjs").write_text("// test", encoding="utf-8")
    # Wrong commit
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda cmd, **kwargs: "deadbeef00000000000000000000000000000000" if "rev-parse" in cmd else "v22.5.0",
    )
    runner = TrackingMockRunner()
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=tmp_path, runner=runner)

    with pytest.raises(CareerOpsVersionMismatchError, match="Commit mismatch"):
        await adapter.check_liveness("https://boards.greenhouse.io/test/1")
    assert runner.invoked is False

    # Missing companion script liveness-browser.mjs
    (tmp_path / "liveness-browser.mjs").unlink()
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda cmd, **kwargs: CAREER_OPS_PINNED_COMMIT if "rev-parse" in cmd else "v22.5.0",
    )
    with pytest.raises(CareerOpsUnavailableError, match="liveness-browser.mjs"):
        await adapter.check_liveness("https://boards.greenhouse.io/test/1")
    assert runner.invoked is False


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_c3_extract_job_identity_gate_blocks_wrong_commit_or_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _setup_checkout(tmp_path)
    (tmp_path / "browser-extract.mjs").write_text("// test", encoding="utf-8")
    # Wrong version
    (tmp_path / "package.json").write_text(json.dumps({"name": "career-ops", "version": "0.0.1"}), encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda cmd, **kwargs: CAREER_OPS_PINNED_COMMIT if "rev-parse" in cmd else "v22.5.0",
    )
    runner = TrackingMockRunner()
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=tmp_path, runner=runner)

    with pytest.raises(CareerOpsVersionMismatchError, match="Version mismatch"):
        await adapter.extract_job("https://example.com/job/123")
    assert runner.invoked is False


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_c3_detect_reposts_identity_gate_blocks_and_leaves_no_scratch_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    checkout_dir = tmp_path / "checkout"
    checkout_dir.mkdir(parents=True)
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)
    _setup_checkout(checkout_dir)
    (checkout_dir / "detect-reposts.mjs").write_text("// test", encoding="utf-8")

    # Unknown commit (has_git=False)
    (checkout_dir / ".git").rmdir()
    runner = TrackingMockRunner()
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=checkout_dir, runtime_dir=runtime_dir, runner=runner)

    rows = [{"url": "https://example.com/1", "first_seen": "2026-08-01", "title": "Platform Engineer", "company": "Acme"}]
    with pytest.raises(CareerOpsConfigurationError, match="Pinned commit SHA could not be positively verified"):
        await adapter.detect_reposts(rows)

    assert runner.invoked is False
    # Invariant: Gate check failed BEFORE any projection created; no repost_scratch or scan-history.tsv exists!
    assert not (runtime_dir / "repost_scratch").exists()
    assert not (runtime_dir / "data" / "scan-history.tsv").exists()
