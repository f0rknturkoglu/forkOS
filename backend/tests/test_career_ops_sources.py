from pathlib import Path
import pytest

from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.models import (
    CareerOpsDiscoveredJob,
    CareerOpsDiscoveryResult,
)
from app.sources.base import SourceClass, is_general_refresh_source, source_class
from app.sources.career_ops_sources import (
    CareerOpsReverseSource,
    get_career_ops_sources,
)


class MockDiscoveryAdapter:
    def __init__(self, result: CareerOpsDiscoveryResult):
        self.result = result

    async def reverse_scan(self, provider: str, **kwargs):
        return self.result


@pytest.mark.no_database
def test_career_ops_sources_catalog_and_classification():
    sources = get_career_ops_sources()
    assert len(sources) == 6
    ids = {s.id for s in sources}
    assert ids == {
        "careerops:greenhouse",
        "careerops:lever",
        "careerops:ashby",
        "careerops:workday",
        "careerops:icims",
        "careerops:bamboohr",
    }
    for s in sources:
        assert s.skip_closure_sweep is True
        assert source_class(s) == SourceClass.SLOW_OPTIN
        assert is_general_refresh_source(s) is False


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_career_ops_source_fetch_outcome_mapping():
    mock_result = CareerOpsDiscoveryResult(
        provider="greenhouse",
        is_partial=False,
        partial_detail="",
        offers=[
            CareerOpsDiscoveredJob(
                company="GitHub",
                title="Systems Engineer",
                url="https://boards.greenhouse.io/github/jobs/999",
                location="Remote",
                posted_at="2026-09-24",
                date_status="dated",
                source="greenhouse",
            )
        ],
    )
    adapter = MockDiscoveryAdapter(mock_result)
    source = CareerOpsReverseSource(provider="greenhouse", adapter=adapter)

    outcome = await source.fetch()
    assert outcome.partial is False
    assert len(outcome.items) == 1

    item = outcome.items[0]
    assert item.title == "Systems Engineer"
    assert item.url == "https://boards.greenhouse.io/github/jobs/999"
    assert item.summary is None  # Section 20: unknown description means None
    assert item.extra["organization"] == "GitHub"
    assert item.extra["location"] == "Remote"
    assert item.extra["career_ops"]["provider"] == "greenhouse"
    assert item.extra["career_ops"]["engine_version"] == "1.34.0"
