import httpx
import pytest

from app.config import settings
from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.capabilities import (
    CapabilityStatus,
    get_capability_status,
    get_declared_capabilities,
)
from app.integrations.career_ops.models import CareerOpsStatusEnum
from app.integrations.career_ops.reasoner_status import (
    get_career_reasoner_runtime_status,
    probe_local_career_reasoner,
)
from app.modules.opportunity.reasoner.factory import get_career_reasoner


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
    assert get_capability_status("discovery.scan", enabled=True, runtime_ready=True) == CapabilityStatus.SUPPORTED


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
    assert doc_ready.capabilities_available == 13

    # Case 2: Browser missing (degraded tier for liveness & extract)
    monkeypatch.setattr("app.integrations.career_ops.doctor.probe_browser_readiness", lambda *args, **kwargs: False)
    adapter_nobrowser = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout)
    doc_nobrowser = await adapter_nobrowser.doctor()
    caps_nobrowser = await adapter_nobrowser.capabilities()
    supported_nobrowser_count = sum(1 for c in caps_nobrowser if c.status == CapabilityStatus.SUPPORTED)
    assert doc_nobrowser.capabilities_available == supported_nobrowser_count
    assert doc_nobrowser.capabilities_available == 11
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
    assert doc_nodisc.capabilities_available == 9

    # Case 4: Integration disabled
    adapter_disabled = CareerOpsAdapter(enabled=False, checkout_dir=mock_checkout)
    doc_disabled = await adapter_disabled.doctor()
    caps_disabled = await adapter_disabled.capabilities()
    supported_disabled_count = sum(1 for c in caps_disabled if c.status == CapabilityStatus.SUPPORTED)
    assert doc_disabled.capabilities_available == 0
    assert supported_disabled_count == 0

    # Case 5: C3.2 Finding C - Doctor probe fails/degraded, but core scripts are ready
    class FailingDoctorRunner:
        async def run_script(self, script_name, args, timeout_seconds=None):
            from app.integrations.career_ops.runner import ExecutionResult
            if script_name == "doctor.mjs":
                return ExecutionResult(script_name=script_name, exit_code=1, stdout="", stderr="simulated probe error")
            return ExecutionResult(script_name=script_name, exit_code=0, stdout="{}", stderr="")

    monkeypatch.setattr(settings, "career_ops_discovery_enabled", True)
    monkeypatch.setattr("app.integrations.career_ops.doctor.probe_browser_readiness", lambda *args, **kwargs: True)
    adapter_degraded = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout, runner=FailingDoctorRunner())
    doc_degraded = await adapter_degraded.doctor()
    assert doc_degraded.status == CareerOpsStatusEnum.DEGRADED
    assert doc_degraded.core_ready is True
    caps_degraded = await adapter_degraded.capabilities()
    supported_degraded_count = sum(1 for c in caps_degraded if c.status == CapabilityStatus.SUPPORTED)
    assert doc_degraded.capabilities_available == supported_degraded_count
    assert doc_degraded.capabilities_available == 13


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "healthy", "expected", "factory_name"),
    [
        ("none", False, CapabilityStatus.DEGRADED, "none"),
        ("mock", False, CapabilityStatus.DEGRADED, "mock"),
        ("ollama", True, CapabilityStatus.SUPPORTED, "ollama"),
        ("ollama", False, CapabilityStatus.DEGRADED, "ollama"),
        ("openai", False, CapabilityStatus.DISABLED, "none"),
        ("gemini", False, CapabilityStatus.DISABLED, "none"),
        ("openrouter", False, CapabilityStatus.DISABLED, "none"),
    ],
)
async def test_reasoner_truth_matrix(
    mock_checkout, monkeypatch, provider, healthy, expected, factory_name
):
    monkeypatch.setattr(settings, "career_reasoner_provider", provider)
    monkeypatch.setattr(settings, "career_reasoner_model", "fixture:latest")
    assert get_career_reasoner().provider_name == factory_name
    runtime = get_career_reasoner_runtime_status(ollama_healthy=healthy)
    assert runtime.capability == expected

    async def probe():
        return runtime

    monkeypatch.setattr("app.integrations.career_ops.doctor.probe_local_career_reasoner", probe)
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=mock_checkout)
    doctor = await adapter.doctor()
    capabilities = await adapter.capabilities()
    assert doctor.reasoner_status == expected
    assert {c.status for c in capabilities if c.id in {"evaluation.deep", "application.package"}} == {expected}
    assert doctor.capabilities_available == sum(
        c.status == CapabilityStatus.SUPPORTED for c in capabilities
    )


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_reasoner_probe_reads_only_loopback_model_metadata(monkeypatch):
    monkeypatch.setattr(settings, "career_reasoner_provider", "ollama")
    monkeypatch.setattr(settings, "career_reasoner_model", "fixture:latest")
    monkeypatch.setattr(settings, "career_reasoner_base_url", "http://127.0.0.1:11434")
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"models": [{"name": "fixture:latest"}]})

    transport = httpx.MockTransport(respond)
    client_factory = httpx.AsyncClient
    monkeypatch.setattr(
        "app.integrations.career_ops.reasoner_status.httpx.AsyncClient",
        lambda **kwargs: client_factory(transport=transport, **kwargs),
    )
    status = await probe_local_career_reasoner()
    assert status.capability == CapabilityStatus.SUPPORTED
    assert len(requests) == 1
    assert str(requests[0].url) == "http://127.0.0.1:11434/api/tags"
    assert requests[0].content == b""

    monkeypatch.setattr(settings, "career_reasoner_base_url", "https://example.com")
    assert (await probe_local_career_reasoner()).capability == CapabilityStatus.DISABLED
    assert len(requests) == 1
