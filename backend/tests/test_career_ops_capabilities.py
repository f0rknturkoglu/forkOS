import pytest
from app.config import settings
from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.capabilities import (
    ALL_CAPABILITIES,
    CapabilityStatus,
    CareerOpsCapabilityContext,
    count_available_capabilities,
    get_capability_status,
    get_declared_capabilities,
    get_provider_capability_inventory,
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

    # Foundation doctor and reverse_ats capabilities are supported when runtime is ready
    status_doc = get_capability_status("foundation.doctor", enabled=True, runtime_ready=True)
    assert status_doc == CapabilityStatus.SUPPORTED

    status_rev = get_capability_status("discovery.reverse_ats", enabled=True, runtime_ready=True)
    assert status_rev == CapabilityStatus.SUPPORTED

    inv = get_provider_capability_inventory()
    assert "greenhouse" in inv
    assert inv["greenhouse"]["status"] == "supported"
    assert inv["curated_scan_lane"]["status"] == "deferred_contract_limitation"


@pytest.mark.no_database
def test_c3_capabilities_status_and_browser_independence():
    # 1. Repost analysis is deterministic Node+TSV, DOES NOT require browser
    assert get_capability_status("job.repost_analysis", enabled=True, runtime_ready=True, browser_ready=False) == CapabilityStatus.SUPPORTED
    assert get_capability_status("job.repost_analysis", enabled=True, runtime_ready=True, browser_ready=True) == CapabilityStatus.SUPPORTED

    # 2. job.legitimacy is supported as deterministic listing health signals
    assert get_capability_status("job.legitimacy", enabled=True, runtime_ready=True, browser_ready=False) == CapabilityStatus.SUPPORTED

    # 3. Liveness and JD extraction are DEGRADED without browser (ATS API works, browser fallback unavailable)
    assert get_capability_status("discovery.liveness", enabled=True, runtime_ready=True, browser_ready=False) == CapabilityStatus.DEGRADED
    assert get_capability_status("job.extract", enabled=True, runtime_ready=True, browser_ready=False) == CapabilityStatus.DEGRADED

    # 4. With browser ready, they become fully SUPPORTED
    assert get_capability_status("discovery.liveness", enabled=True, runtime_ready=True, browser_ready=True) == CapabilityStatus.SUPPORTED
    assert get_capability_status("job.extract", enabled=True, runtime_ready=True, browser_ready=True) == CapabilityStatus.SUPPORTED


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_doctor_and_adapter_capabilities_agreement(mock_checkout, monkeypatch):
    """Assert doctor capabilities_available == count of adapter.capabilities() with SUPPORTED across all states (Finding G)."""
    # Case 1: Browser ready
    monkeypatch.setattr("app.integrations.career_ops.doctor.probe_browser_readiness", lambda *args, **kwargs: True)
    adapter_ready = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout)
    doc_ready = await adapter_ready.doctor()
    caps_ready = await adapter_ready.capabilities()
    supported_ready_count = sum(1 for c in caps_ready if c.status == CapabilityStatus.SUPPORTED)
    assert doc_ready.capabilities_available == supported_ready_count
    assert doc_ready.capabilities_available == 6  # doctor, reverse_ats, repost, legitimacy, liveness, extract

    # Case 2: Browser missing (degraded tier for liveness & extract)
    monkeypatch.setattr("app.integrations.career_ops.doctor.probe_browser_readiness", lambda *args, **kwargs: False)
    adapter_nobrowser = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout)
    doc_nobrowser = await adapter_nobrowser.doctor()
    caps_nobrowser = await adapter_nobrowser.capabilities()
    supported_nobrowser_count = sum(1 for c in caps_nobrowser if c.status == CapabilityStatus.SUPPORTED)
    assert doc_nobrowser.capabilities_available == supported_nobrowser_count
    assert doc_nobrowser.capabilities_available == 4  # doctor, reverse_ats, repost, legitimacy
    # liveness and extract should be DEGRADED
    cap_dict = {c.id: c.status for c in caps_nobrowser}
    assert cap_dict["discovery.liveness"] == CapabilityStatus.DEGRADED
    assert cap_dict["job.extract"] == CapabilityStatus.DEGRADED

    # Case 3: Discovery disabled
    monkeypatch.setattr(settings, "career_ops_discovery_enabled", False)
    adapter_nodisc = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout)
    doc_nodisc = await adapter_nodisc.doctor()
    caps_nodisc = await adapter_nodisc.capabilities()
    supported_nodisc_count = sum(1 for c in caps_nodisc if c.status == CapabilityStatus.SUPPORTED)
    assert doc_nodisc.capabilities_available == supported_nodisc_count
    assert doc_nodisc.capabilities_available == 3  # doctor, repost, legitimacy

    # Case 4: Integration disabled
    adapter_disabled = CareerOpsAdapter(enabled=False, checkout_dir=mock_checkout)
    doc_disabled = await adapter_disabled.doctor()
    caps_disabled = await adapter_disabled.capabilities()
    supported_disabled_count = sum(1 for c in caps_disabled if c.status == CapabilityStatus.SUPPORTED)
    assert doc_disabled.capabilities_available == 0
    assert supported_disabled_count == 0
