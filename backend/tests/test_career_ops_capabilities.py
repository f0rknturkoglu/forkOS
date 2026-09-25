import pytest
from app.integrations.career_ops.capabilities import (
    ALL_CAPABILITIES,
    CapabilityStatus,
    get_capability_status,
    get_declared_capabilities,
)


@pytest.mark.no_database
def test_capability_registry():
    declared = get_declared_capabilities()
    assert len(declared) >= 20
    cap_ids = [c.id for c in declared]
    assert "discovery.scan" in cap_ids
    assert "evaluation.deep" in cap_ids
    assert "cv.tailor" in cap_ids
    assert "foundation.doctor" in cap_ids

    # When disabled
    status_disabled = get_capability_status("discovery.scan", enabled=False, runtime_ready=False)
    assert status_disabled == CapabilityStatus.DISABLED

    # When enabled but runtime unavailable
    status_unavail = get_capability_status("discovery.scan", enabled=True, runtime_ready=False)
    assert status_unavail == CapabilityStatus.UNAVAILABLE

    # In C1 domain capabilities are not yet implemented, so even if runtime ready they remain UNAVAILABLE
    # Foundation doctor and reverse_ats capabilities are supported when runtime is ready
    status_doc = get_capability_status("foundation.doctor", enabled=True, runtime_ready=True)
    assert status_doc == CapabilityStatus.SUPPORTED

    status_rev = get_capability_status("discovery.reverse_ats", enabled=True, runtime_ready=True)
    assert status_rev == CapabilityStatus.SUPPORTED

    from app.integrations.career_ops.capabilities import get_provider_capability_inventory
    inv = get_provider_capability_inventory()
    assert "greenhouse" in inv
    assert inv["greenhouse"]["status"] == "supported"
    assert inv["curated_scan_lane"]["status"] == "deferred_contract_limitation"
