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
