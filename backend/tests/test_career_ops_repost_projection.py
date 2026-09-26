import json
from pathlib import Path
import pytest
from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.models import CareerOpsRepostCluster
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
async def test_adapter_detect_reposts_projects_ephemeral_tsv_and_cleans_up(mock_checkout: Path, tmp_path: Path):
    cluster_payload = {
        "metadata": {"clusters": 1},
        "clusters": [
            {
                "company": "Acme Corp",
                "role": "Platform Engineer",
                "repostCount": 2,
                "firstSeen": "2026-08-01",
                "lastSeen": "2026-09-15",
                "daysSpan": 45,
                "appearances": [
                    {"url": "https://example.com/1", "date": "2026-08-01", "title": "Platform Engineer"},
                    {"url": "https://example.com/2", "date": "2026-09-15", "title": "Platform Engineer"},
                ],
            }
        ],
    }
    runner = MockRunner(stdout=json.dumps(cluster_payload))
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runtime_dir=tmp_path / "runtime", runner=runner)

    rows = [
        {"url": "https://example.com/1", "first_seen": "2026-08-01", "title": "Platform Engineer", "company": "Acme Corp"},
        {"url": "https://example.com/2", "first_seen": "2026-09-15", "title": "Platform Engineer", "company": "Acme Corp"},
    ]
    clusters = await adapter.detect_reposts(rows)
    assert len(clusters) == 1
    assert isinstance(clusters[0], CareerOpsRepostCluster)
    assert clusters[0].company == "Acme Corp"
    assert clusters[0].repost_count == 2
    assert clusters[0].days_span == 45

    # Invariant: scan-history.tsv is ephemeral and deleted after execution
    assert not (adapter.runtime_dir / "data" / "scan-history.tsv").exists()
