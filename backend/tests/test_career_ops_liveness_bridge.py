import json
import subprocess
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
async def test_adapter_check_liveness_rejects_unsafe_and_private_urls(mock_checkout: Path):
    runner = MockRunner()
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=runner)

    unsafe_urls = [
        "file:///etc/passwd",
        "javascript:alert(1)",
        "http://localhost:8000/job",
        "http://127.0.0.1:3000/api",
        "http://0.0.0.0:80/job",
        "http://10.0.1.5:8080/internal",
        "http://192.168.1.1/admin",
        "http://172.16.0.1/private",
        "http://169.254.169.254/latest/meta-data",
        "http://metadata.google.internal/computeMetadata",
    ]

    for u in unsafe_urls:
        receipt = await adapter.check_liveness(u)
        assert receipt.status == "uncertain"
        assert receipt.code == "invalid_url"

    assert len(runner.captured_scripts) == 0


@pytest.mark.no_database
def test_bridge_playwright_resolution_contract():
    """Verify bridge resolves Playwright from pinned checkout using createRequire (Finding B)."""
    bridge_script = Path(__file__).parent.parent / "app" / "integrations" / "career_ops" / "bridges" / "liveness.mjs"
    assert bridge_script.exists()

    # 1. When CAREER_OPS_CHECKOUT points to pinned checkout (.vendor/career-ops) where Playwright exists
    vendor_checkout = Path(__file__).parent.parent.parent / ".vendor" / "career-ops"
    if (vendor_checkout / "node_modules" / "playwright").exists():
        proc = subprocess.run(
            [
                "node",
                "-e",
                f"""
                const {{ createRequire }} = require('node:module');
                const {{ pathToFileURL }} = require('node:url');
                const {{ resolve }} = require('node:path');
                const req = createRequire(pathToFileURL(resolve('{vendor_checkout}', 'package.json')));
                const pw = req('playwright');
                process.stdout.write(typeof pw.chromium.launch);
                """,
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        assert proc.stdout.strip() == "function"

    # 2. When Playwright is absent in checkout, bridge outputs typed no_playwright receipt
    import os
    import shutil
    import tempfile
    node_bin = shutil.which("node") or "node"
    with tempfile.TemporaryDirectory() as empty_checkout:
        (Path(empty_checkout) / "package.json").write_text('{"name": "career-ops", "version": "1.34.0"}')
        (Path(empty_checkout) / "liveness-api.mjs").write_text("export async function checkLivenessViaApi() { return null; }")
        (Path(empty_checkout) / "liveness-browser.mjs").write_text("export function rejectPrivateOrInvalid() { return null; }")

        res = subprocess.run(
            [node_bin, str(bridge_script), "https://example.com/job/fallback-needed"],
            env={**os.environ, "CAREER_OPS_CHECKOUT": empty_checkout},
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0
        payload = json.loads(res.stdout)
        assert payload["status"] == "uncertain"
        assert payload["code"] == "no_playwright"
        assert "Playwright not installed" in payload["reason"]
