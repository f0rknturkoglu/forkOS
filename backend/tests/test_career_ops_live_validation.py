import os
import time
from pathlib import Path

import pytest

from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.models import (
    CareerOpsDiscoveryResult,
    CareerOpsProviderScanReceipt,
)


@pytest.mark.no_database
@pytest.mark.live_network
@pytest.mark.asyncio
async def test_live_career_ops_bounded_provider_scan():
    if not os.environ.get("FORKOS_RUN_LIVE_CAREER_TESTS"):
        pytest.skip("SKIPPED — live network test not enabled (set FORKOS_RUN_LIVE_CAREER_TESTS=1)")

    repo_root = Path(__file__).resolve().parent.parent.parent
    vendor_dir = repo_root / ".vendor" / "career-ops"

    if not vendor_dir.exists():
        pytest.skip(".vendor/career-ops not provisioned")

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=vendor_dir,
    )

    targets = {
        "job_boards": [
            {
                "name": "arbeitnow-test",
                "provider": "arbeitnow",
                "max_results": 5,
                "max_pages": 1,
            },
            {
                "name": "4dayweek-test",
                "provider": "4dayweek",
                "max_results": 5,
                "max_pages": 1,
            },
        ],
        "tracked_companies": [
            {
                "name": "GitLab",
                "provider": "greenhouse",
                "careers_url": "https://job-boards.greenhouse.io/gitlab",
                "max_results": 5,
                "max_pages": 1,
            }
        ],
    }

    start = time.perf_counter()
    receipt = await adapter.provider_scan(targets=targets, since_days=30)
    duration = time.perf_counter() - start

    assert isinstance(receipt, CareerOpsProviderScanReceipt)
    assert receipt.version == "forkos.careerops.scan@1"
    assert receipt.providers_loaded == 89
    assert isinstance(receipt.offers, list)
    assert duration < 30.0

    # Verify targets were reached and reported
    target_names = {t.target for t in receipt.target_results}
    assert "arbeitnow-test" in target_names
    assert "4dayweek-test" in target_names
    assert "GitLab" in target_names

    # Check cap adherence: each target has max_results=5, so total offers <= 15
    assert len(receipt.offers) <= 15

    # Check target telemetry: verify cap_hit and result_limit are tracked
    for tr in receipt.target_results:
        assert tr.requests_made is not None
        assert tr.requests_made >= 1
        assert tr.result_limit == 5

    # Check deduplication: URLs in returned offers must be unique
    urls = [offer.url for offer in receipt.offers]
    assert len(urls) == len(set(urls))


@pytest.mark.no_database
@pytest.mark.live_network
@pytest.mark.asyncio
async def test_live_reverse_ats_scan_bounds():
    if not os.environ.get("FORKOS_RUN_LIVE_CAREER_TESTS"):
        pytest.skip("SKIPPED — live network test not enabled (set FORKOS_RUN_LIVE_CAREER_TESTS=1)")

    repo_root = Path(__file__).resolve().parent.parent.parent
    vendor_dir = repo_root / ".vendor" / "career-ops"

    if not vendor_dir.exists():
        pytest.skip(".vendor/career-ops not provisioned")

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=vendor_dir,
    )

    # 1 company limit on reverse scan
    start = time.perf_counter()
    result = await adapter.reverse_scan("greenhouse", since_days=7, limit=1)
    duration = time.perf_counter() - start

    assert isinstance(result, CareerOpsDiscoveryResult)
    assert result.provider == "greenhouse"
    assert result.companies_scanned == 1
    assert duration < 20.0
    assert not (adapter.runtime_dir / "portals.yml").exists()
