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
    status_ready = get_capability_status("discovery.scan", enabled=True, runtime_ready=True)
    assert status_ready == CapabilityStatus.UNAVAILABLE

    # Foundation doctor capability is supported when runtime is ready
    status_doc = get_capability_status("foundation.doctor", enabled=True, runtime_ready=True)
    assert status_doc == CapabilityStatus.SUPPORTED
