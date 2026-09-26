from pathlib import Path
import pytest
from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.models import CareerOpsStatusEnum


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_live_pinned_career_ops_runtime():
    repo_root = Path(__file__).resolve().parent.parent.parent
    vendor_dir = repo_root / ".vendor" / "career-ops"

    if not vendor_dir.exists():
        pytest.skip(".vendor/career-ops not provisioned; run 'make career-ops-setup'")

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=vendor_dir,
    )
    result = await adapter.doctor()
    assert result.status == CareerOpsStatusEnum.READY
    assert result.expected_identity.version == "1.34.0"
    assert result.actual_identity is not None
    assert result.actual_identity.version == "1.34.0"
    assert result.actual_identity.commit == "6326eb5d3804e8cb20d28acd5701a4e603a301f9"
    assert result.canonical_state_owner == "forkOS PostgreSQL"
    assert result.runtime.node_compatible is True
    assert result.upstream_onboarding is not None
    assert isinstance(result.upstream_onboarding.onboarding_needed, bool)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_live_liveness_and_extraction_smoke():
    repo_root = Path(__file__).resolve().parent.parent.parent
    vendor_dir = repo_root / ".vendor" / "career-ops"

    if not vendor_dir.exists():
        pytest.skip(".vendor/career-ops not provisioned; run 'make career-ops-setup'")

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=vendor_dir,
    )

    # 1. ATS API liveness smoke
    url_ats = "https://boards.greenhouse.io/gitlab/jobs/4279007005"
    receipt_ats = await adapter.check_liveness(url_ats)
    assert receipt_ats.url == url_ats
    assert receipt_ats.method == "api"
    assert receipt_ats.status in ("active", "expired", "uncertain")
    assert receipt_ats.checked_at != ""

    # 2. Browser fallback liveness smoke
    url_fallback = "https://example.com"
    receipt_fallback = await adapter.check_liveness(url_fallback)
    assert receipt_fallback.url == url_fallback
    assert receipt_fallback.method == "browser"
    assert receipt_fallback.status in ("active", "expired", "uncertain")
    assert receipt_fallback.checked_at != ""

    # 3. Real JD extraction smoke & C3.2 Finding A seal:
    # Expired GitLab job redirects to Greenhouse index with ?error=true.
    # Must be positively recognized as invalid_non_job to prevent polluting canonical listing.
    extract_res = await adapter.extract_job(url_ats)
    assert extract_res.requested_url == url_ats
    assert "error=true" in extract_res.final_url
    assert extract_res.job_identity_status == "invalid_non_job"
    assert extract_res.identity_reason == "provider_error_redirect"
    assert extract_res.title != ""
