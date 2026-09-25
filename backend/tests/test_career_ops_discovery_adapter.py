from pathlib import Path
import pytest

from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.errors import (
    CareerOpsInvalidOutputError,
    CareerOpsSecurityError,
)
from app.integrations.career_ops.runner import ExecutionResult


class MockRunner:
    def __init__(self, stdout: str, exit_code: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.exit_code = exit_code
        self.stderr = stderr
        self.last_args: list[str] = []
        self.last_env: dict[str, str] = {}

    async def run_script(
        self,
        script_name: str,
        args: list[str],
        timeout_seconds: float | None = None,
        extra_env: dict[str, str] | None = None,
        max_buffer_bytes: int | None = None,
    ) -> ExecutionResult:
        self.last_args = list(args)
        if extra_env:
            self.last_env = dict(extra_env)
        return ExecutionResult(
            script_name=script_name,
            exit_code=self.exit_code,
            stdout=self.stdout,
            stderr=self.stderr,
        )


SAMPLE_VALID_REVERSE_JSON = """{
  "date": "2026-09-25",
  "sources": ["greenhouse"],
  "resumed": false,
  "sinceDays": 7,
  "companiesAvailable": 500,
  "companiesScanned": 50,
  "capHit": false,
  "stoppedByOutage": false,
  "datasetStatus": "ok",
  "postingsKept": 2,
  "postingsDroppedNoDate": 1,
  "postingsFilteredBlacklist": 0,
  "postingsAnnotatedBlacklisted": 0,
  "postingsDroppedContent": 0,
  "unreachableBoards": 0,
  "retiredBoardsSkipped": 0,
  "cappedBoards": 0,
  "dnsPacing": {"delayed": 0, "waitedMs": 0},
  "saved": false,
  "offers": [
    {
      "company": "Acme Corp",
      "title": "Senior Backend Engineer",
      "url": "https://boards.greenhouse.io/acme/jobs/101",
      "location": "Remote",
      "postedAt": "2026-09-24",
      "dateStatus": "dated",
      "blacklisted": false,
      "note": null,
      "source": "greenhouse"
    },
    {
      "company": "Beta Inc",
      "title": "Staff Python Developer",
      "url": "https://boards.greenhouse.io/beta/jobs/202",
      "location": "Ankara, Turkey",
      "postedAt": "2026-09-23",
      "dateStatus": "dated",
      "blacklisted": false,
      "note": null,
      "source": "greenhouse"
    }
  ]
}"""


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_reverse_scan_valid_json(tmp_path: Path):
    runner = MockRunner(stdout=SAMPLE_VALID_REVERSE_JSON)
    # Seed fake config.yaml for targeting projection
    config_file = tmp_path / "config.yaml"
    config_file.write_text("scoring:\n  role_terms:\n    - backend\n", encoding="utf-8")

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        runner=runner,
    )
    # Monkeypatch config path
    import app.integrations.career_ops.adapter as adapter_module
    result = await adapter.reverse_scan("greenhouse", since_days=7, limit=50, config_path=config_file)

    assert result.provider == "greenhouse"
    assert result.is_partial is False
    assert len(result.offers) == 2
    assert result.offers[0].company == "Acme Corp"
    assert result.offers[0].title == "Senior Backend Engineer"
    assert result.offers[0].url == "https://boards.greenhouse.io/acme/jobs/101"
    assert result.offers[0].location == "Remote"
    assert result.offers[0].source == "greenhouse"

    # Verify command line arguments passed to runner
    assert "--json" in runner.last_args
    assert "--dry-run" in runner.last_args
    assert "--ats" in runner.last_args
    assert "greenhouse" in runner.last_args
    assert "--since" in runner.last_args
    assert "7" in runner.last_args
    assert "--limit" in runner.last_args
    assert "50" in runner.last_args


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_reverse_scan_rejects_unknown_provider(tmp_path: Path):
    runner = MockRunner(stdout="{}")
    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        runner=runner,
    )
    with pytest.raises(CareerOpsSecurityError, match="Unknown or unallowlisted discovery provider"):
        await adapter.reverse_scan("unsupported_provider")


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_reverse_scan_rejects_invalid_ranges(tmp_path: Path):
    runner = MockRunner(stdout="{}")
    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        runner=runner,
    )
    with pytest.raises(ValueError, match="since_days must be between 1 and 90"):
        await adapter.reverse_scan("greenhouse", since_days=0)

    with pytest.raises(ValueError, match="limit must be positive"):
        await adapter.reverse_scan("greenhouse", limit=-5)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_reverse_scan_detects_partial_degradation(tmp_path: Path):
    partial_json = """{
      "date": "2026-09-25",
      "sources": ["lever"],
      "resumed": false,
      "sinceDays": 7,
      "companiesAvailable": 500,
      "companiesScanned": 20,
      "capHit": true,
      "stoppedByOutage": true,
      "datasetStatus": "stale",
      "unreachableBoards": 15,
      "offers": [
        {
          "company": "Valid Corp",
          "title": "Platform Engineer",
          "url": "https://jobs.lever.co/valid/1",
          "location": "Remote",
          "postedAt": "2026-09-24",
          "source": "lever"
        }
      ]
    }"""
    runner = MockRunner(stdout=partial_json)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("scoring:\n  role_terms:\n    - platform\n", encoding="utf-8")

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        runner=runner,
    )
    result = await adapter.reverse_scan("lever", since_days=7, config_path=config_file)
    assert result.is_partial is True
    assert "outage" in result.partial_detail.lower() or "stale" in result.partial_detail.lower()
    assert len(result.offers) == 1


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_reverse_scan_fails_on_malformed_json(tmp_path: Path):
    runner = MockRunner(stdout="Not A JSON Document At All")
    config_file = tmp_path / "config.yaml"
    config_file.write_text("scoring:\n  role_terms:\n    - backend\n", encoding="utf-8")

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        runner=runner,
    )
    with pytest.raises(CareerOpsInvalidOutputError):
        await adapter.reverse_scan("greenhouse", config_path=config_file)
