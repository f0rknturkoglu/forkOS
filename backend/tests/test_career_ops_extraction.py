import json
from pathlib import Path

import pytest

from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.models import CareerOpsJobExtractionResult
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
async def test_adapter_extract_job_success(mock_checkout: Path):
    payload = {
        "url": "https://example.com/job/123",
        "title": "Staff Backend Engineer",
        "text": "Full job description text with requirements and responsibilities...",
    }
    runner = MockRunner(stdout=json.dumps(payload))
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=runner)

    result = await adapter.extract_job("https://example.com/job/123")
    assert isinstance(result, CareerOpsJobExtractionResult)
    assert result.title == "Staff Backend Engineer"
    assert "Full job description" in result.text
    assert result.error is None
    assert runner.captured_scripts[0][0] == "browser-extract.mjs"
    assert "--mode" in runner.captured_scripts[0][1]


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_extract_job_handles_non_zero_exit(mock_checkout: Path):
    error_payload = json.dumps({"error": "Job no longer available", "code": "empty_text"})
    runner = MockRunner(stderr=error_payload, exit_code=1)
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=runner)

    result = await adapter.extract_job("https://example.com/job/dead")
    assert isinstance(result, CareerOpsJobExtractionResult)
    assert result.error == "Job no longer available"
    assert result.code == "empty_text"
