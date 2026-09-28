import json
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
        self.last_timeout: float | None = None

    async def run_script(
        self,
        script_name: str,
        args: list[str],
        timeout_seconds: float | None = None,
        extra_env: dict[str, str] | None = None,
        max_buffer_bytes: int | None = None,
    ) -> ExecutionResult:
        self.last_args = list(args)
        self.last_timeout = timeout_seconds
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
      "postedAt": "2026-09-25T10:00:00Z",
      "dateStatus": "explicit",
      "blacklisted": false,
      "source": "greenhouse"
    },
    {
      "company": "Acme Corp",
      "title": "Staff DevOps Engineer",
      "url": "https://boards.greenhouse.io/acme/jobs/102",
      "location": "Berlin, Germany",
      "postedAt": null,
      "dateStatus": "undated",
      "blacklisted": false,
      "source": "greenhouse"
    }
  ]
}"""


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_reverse_scan_valid_json(mock_checkout: Path, tmp_path: Path):
    runner = MockRunner(stdout=SAMPLE_VALID_REVERSE_JSON)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("scoring:\n  role_terms:\n    - backend\n", encoding="utf-8")

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=mock_checkout,
        runtime_dir=tmp_path / "runtime",
        runner=runner,
    )
    result = await adapter.reverse_scan("greenhouse", since_days=7, limit=50, config_path=config_file)

    assert result.provider == "greenhouse"
    assert result.is_partial is False
    assert len(result.offers) == 2
    assert result.offers[0].company == "Acme Corp"
    assert result.offers[0].title == "Senior Backend Engineer"
    assert result.offers[0].url == "https://boards.greenhouse.io/acme/jobs/101"
    assert result.offers[0].location == "Remote"
    assert result.offers[0].source == "greenhouse"

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
async def test_workday_reverse_scan_has_longer_timeout(mock_checkout: Path, tmp_path: Path):
    runner = MockRunner(stdout=SAMPLE_VALID_REVERSE_JSON)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("scoring:\n  role_terms: [backend]\n", encoding="utf-8")
    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=mock_checkout,
        runtime_dir=tmp_path / "runtime",
        runner=runner,
    )

    await adapter.reverse_scan("workday", config_path=config_file)

    assert runner.last_timeout is not None
    assert runner.last_timeout >= 600.0


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_reverse_scan_rejects_unknown_provider(mock_checkout: Path, tmp_path: Path):
    runner = MockRunner(stdout="{}")
    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=mock_checkout,
        runtime_dir=tmp_path / "runtime",
        runner=runner,
    )
    with pytest.raises(CareerOpsSecurityError, match="Unknown or unallowlisted discovery provider"):
        await adapter.reverse_scan("unsupported_provider")


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_reverse_scan_rejects_invalid_ranges(mock_checkout: Path, tmp_path: Path):
    runner = MockRunner(stdout="{}")
    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=mock_checkout,
        runtime_dir=tmp_path / "runtime",
        runner=runner,
    )
    with pytest.raises(ValueError, match="since_days must be between 1 and 90"):
        await adapter.reverse_scan("greenhouse", since_days=0)

    with pytest.raises(ValueError, match="limit must be positive"):
        await adapter.reverse_scan("greenhouse", limit=-5)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_reverse_scan_cap_hit_and_truncation_is_partial(mock_checkout: Path, tmp_path: Path):
    # capHit = True must set is_partial = True and detail 'scan reached configured cap'
    cap_json = """{
      "date": "2026-09-25",
      "sources": ["lever"],
      "companiesAvailable": 500,
      "companiesScanned": 20,
      "capHit": true,
      "cappedBoards": 5,
      "stoppedByOutage": false,
      "datasetStatus": "ok",
      "offers": [
        {
          "company": "Valid Corp",
          "title": "Platform Engineer",
          "url": "https://jobs.lever.co/valid/1",
          "location": "Remote",
          "source": "lever"
        }
      ]
    }"""
    runner = MockRunner(stdout=cap_json)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("scoring:\n  role_terms:\n    - platform\n", encoding="utf-8")

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=mock_checkout,
        runtime_dir=tmp_path / "runtime",
        runner=runner,
    )
    result = await adapter.reverse_scan("lever", since_days=7, config_path=config_file)
    assert result.is_partial is True
    assert "scan reached configured cap" in result.partial_detail
    assert "5 boards capped" in result.partial_detail
    assert len(result.offers) == 1


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_reverse_scan_url_boundary_validation(mock_checkout: Path, tmp_path: Path):
    # Only http:// and https:// URLs with valid host are accepted; dangerous/malformed URLs quarantined
    url_test_json = """{
      "date": "2026-09-25",
      "capHit": false,
      "offers": [
        {"company": "Co", "title": "Job 1", "url": "https://jobs.ashbyhq.com/valid/1"},
        {"company": "Co", "title": "Job 2", "url": "http://jobs.ashbyhq.com/valid/2"},
        {"company": "Co", "title": "Job 3", "url": "javascript:alert('pwned')"},
        {"company": "Co", "title": "Job 4", "url": "file:///etc/passwd"},
        {"company": "Co", "title": "Job 5", "url": "ftp://files.example.com/job"},
        {"company": "Co", "title": "Job 6", "url": "https://"},
        {"company": "Co", "title": "Job 7", "url": "not-even-a-url"}
      ]
    }"""
    runner = MockRunner(stdout=url_test_json)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("scoring:\n  role_terms:\n    - job\n", encoding="utf-8")

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=mock_checkout,
        runtime_dir=tmp_path / "runtime",
        runner=runner,
    )
    result = await adapter.reverse_scan("ashby", config_path=config_file)
    assert len(result.offers) == 2
    assert result.offers[0].url == "https://jobs.ashbyhq.com/valid/1"
    assert result.offers[1].url == "http://jobs.ashbyhq.com/valid/2"


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_reverse_scan_strict_single_json_document(mock_checkout: Path, tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("scoring:\n  role_terms:\n    - backend\n", encoding="utf-8")

    # 1. Valid JSON with leading/trailing whitespace passes
    runner1 = MockRunner(stdout="   \n  {\"offers\": [], \"capHit\": false}  \n\t")
    adapter1 = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=runner1)
    res = await adapter1.reverse_scan("greenhouse", config_path=config_file)
    assert res.offers == []

    # 2. Text before JSON fails
    runner2 = MockRunner(stdout="DEBUG: scanning greenhouse boards...\n{\"offers\": []}")
    adapter2 = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=runner2)
    with pytest.raises(CareerOpsInvalidOutputError, match="Strict JSON contract failed"):
        await adapter2.reverse_scan("greenhouse", config_path=config_file)

    # 3. Text after JSON fails
    runner3 = MockRunner(stdout="{\"offers\": []}\nDone in 3.4 seconds.")
    adapter3 = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=runner3)
    with pytest.raises(CareerOpsInvalidOutputError, match="Strict JSON contract failed"):
        await adapter3.reverse_scan("greenhouse", config_path=config_file)

    # 4. Multiple JSON documents fail
    runner4 = MockRunner(stdout="{\"offers\": []}{\"offers\": []}")
    adapter4 = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=runner4)
    with pytest.raises(CareerOpsInvalidOutputError, match="Strict JSON contract failed"):
        await adapter4.reverse_scan("greenhouse", config_path=config_file)

    # 5. Array instead of object fails
    runner5 = MockRunner(stdout="[]")
    adapter5 = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=runner5)
    with pytest.raises(CareerOpsInvalidOutputError, match="Expected JSON object"):
        await adapter5.reverse_scan("greenhouse", config_path=config_file)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_reverse_scan_typed_receipt_rejects_string_booleans(mock_checkout: Path, tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("scoring:\n  role_terms:\n    - backend\n", encoding="utf-8")

    # capHit as string "false" is rejected by StrictBool
    runner = MockRunner(stdout=json.dumps({"capHit": "false", "offers": []}))
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=runner)
    with pytest.raises(CareerOpsInvalidOutputError, match="Receipt validation failed"):
        await adapter.reverse_scan("greenhouse", config_path=config_file)

    # stoppedByOutage as string "true" is rejected by StrictBool
    runner2 = MockRunner(stdout=json.dumps({"stoppedByOutage": "true", "offers": []}))
    adapter2 = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=runner2)
    with pytest.raises(CareerOpsInvalidOutputError, match="Receipt validation failed"):
        await adapter2.reverse_scan("greenhouse", config_path=config_file)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_reverse_scan_quarantines_malformed_offers(mock_checkout: Path, tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("scoring:\n  role_terms:\n    - backend\n", encoding="utf-8")

    payload = {
        "date": "2026-09-25",
        "sinceDays": 7,
        "companiesAvailable": 10,
        "companiesScanned": 5,
        "capHit": False,
        "unknownFutureField": "compatible",
        "offers": [
            # Valid offer
            {"company": "Acme", "title": "DevOps", "url": "https://example.com/1"},
            # Malformed offer: missing title
            {"company": "BadCo", "url": "https://example.com/2"},
            # Malformed offer: invalid blacklisted type
            {"company": "BadCo2", "title": "Eng", "url": "https://example.com/3", "blacklisted": "false"},
            # Malformed offer: not a dict
            "not a dict",
        ],
    }
    runner = MockRunner(stdout=json.dumps(payload))
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=runner)
    result = await adapter.reverse_scan("greenhouse", config_path=config_file)
    assert len(result.offers) == 1
    assert result.offers[0].company == "Acme"
    assert result.offers[0].title == "DevOps"
