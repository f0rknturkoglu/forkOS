from pathlib import Path
import pytest

from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.models import CareerOpsDiscoveryResult


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_live_reverse_ats_scan_smoke():
    repo_root = Path(__file__).resolve().parent.parent.parent
    vendor_dir = repo_root / ".vendor" / "career-ops"

    if not vendor_dir.exists():
        pytest.skip(".vendor/career-ops not provisioned; run 'make career-ops-setup'")

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=vendor_dir,
    )

    # Bounded smoke scan: greenhouse provider with 1 company limit
    result = await adapter.reverse_scan("greenhouse", since_days=3, limit=1)

    assert isinstance(result, CareerOpsDiscoveryResult)
    assert result.provider == "greenhouse"
    assert result.companies_scanned >= 1
    assert result.date != ""
    assert isinstance(result.offers, list)
    assert isinstance(result.is_partial, bool)
    assert not (adapter.runtime_dir / "portals.yml").exists()

    # Bounded smoke scan: ashby provider with 1 company limit
    result_ashby = await adapter.reverse_scan("ashby", since_days=3, limit=1)
    assert isinstance(result_ashby, CareerOpsDiscoveryResult)
    assert result_ashby.provider == "ashby"
    assert result_ashby.companies_scanned >= 1
    assert not (adapter.runtime_dir / "portals.yml").exists()
