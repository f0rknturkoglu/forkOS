import json
from pathlib import Path
import pytest
from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.models import CareerOpsLivenessReceipt
from app.integrations.career_ops.runner import ExecutionResult


class MockRunner:
    def __init__(self, stdout: str = "", stderr: str = "", exit_code: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.captured_scripts: list[tuple[str, list[str]]] = []

    async def run_script(self, script_name: str, args: list[str], **kwargs) -> ExecutionResult:
        self.captured_scripts.append((script_name, args))
        return ExecutionResult(
            script_name=script_name,
            exit_code=self.exit_code,
            stdout=self.stdout,
            stderr=self.stderr,
        )


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_check_liveness_parses_json_receipt(mock_checkout: Path):
    payload = {
        "url": "https://boards.greenhouse.io/example/jobs/123",
        "status": "active",
        "code": "greenhouse_api_ok",
        "reason": "ATS API returns the posting (live)",
        "method": "api",
        "checked_at": "2026-09-25T20:20:00Z",
    }
    runner = MockRunner(stdout=json.dumps(payload))
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=runner)

    receipt = await adapter.check_liveness("https://boards.greenhouse.io/example/jobs/123")
    assert isinstance(receipt, CareerOpsLivenessReceipt)
    assert receipt.status == "active"
    assert receipt.method == "api"
    assert receipt.code == "greenhouse_api_ok"
    assert runner.captured_scripts[0][0] == "bridges/liveness.mjs"


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_check_liveness_rejects_unsafe_urls(mock_checkout: Path):
    runner = MockRunner()
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=runner)

    # file:// or javascript: scheme rejected before running script
    receipt = await adapter.check_liveness("file:///etc/passwd")
    assert receipt.status == "uncertain"
    assert receipt.code == "invalid_url"
    assert len(runner.captured_scripts) == 0
