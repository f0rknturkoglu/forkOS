from collections.abc import AsyncIterator
import uuid
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity
from app.db import SessionLocal
from app.integrations.career_ops.models import (
    CareerOpsJobExtractionResult,
    CareerOpsLivenessReceipt,
)
from app.modules.opportunity.listing_service import OpportunityListingService
from app.modules.opportunity.models import Opportunity, OpportunitySourceObservation


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


class MockCareerOpsAdapter:
    def __init__(self):
        self.liveness_responses: dict[str, CareerOpsLivenessReceipt] = {}
        self.extraction_responses: dict[str, CareerOpsJobExtractionResult] = {}
        self.liveness_calls: list[str] = []
        self.extraction_calls: list[str] = []

    async def check_liveness(self, url: str, **kwargs) -> CareerOpsLivenessReceipt:
        self.liveness_calls.append(url)
        if url in self.liveness_responses:
            return self.liveness_responses[url]
        return CareerOpsLivenessReceipt(
            url=url,
            status="active",
            code="test_ok",
            reason="Live in mock",
            method="api",
            checked_at=datetime.now(UTC).isoformat(),
        )

    async def extract_job(self, url: str, **kwargs) -> CareerOpsJobExtractionResult:
        self.extraction_calls.append(url)
        if url in self.extraction_responses:
            return self.extraction_responses[url]
        return CareerOpsJobExtractionResult(
            url=url,
            title="Senior Test Engineer",
            text="This is a substantive job description that exceeds two hundred characters in length. " * 3,
        )


async def _seed_opportunity(
    session: AsyncSession,
    *,
    title: str = "Backend Engineer",
    company: str = "TestCorp",
    url: str = "https://example.com/job/1",
    description: str = "",
    status: str = "discovered",
    source_status: str = "active",
) -> Opportunity:
    entity = await create_entity(session, type="opportunity", title=title)
    now = datetime.now(UTC)
    opp = Opportunity(
        id=entity.id,
        kind="job",
        organization=company,
        url=url,
        status=status,
        source_status=source_status,
        found_at=now,
        raw={"description": description} if description else {},
    )
    session.add(opp)
    await session.flush()
    return opp


async def _seed_observation(
    session: AsyncSession,
    *,
    opportunity_id: uuid.UUID,
    source: str,
    url: str,
    source_status: str = "active",
    enrichment: dict | None = None,
) -> OpportunitySourceObservation:
    now = datetime.now(UTC)
    obs = OpportunitySourceObservation(
        opportunity_id=opportunity_id,
        source=source,
        canonical_url=url,
        source_status=source_status,
        first_seen_at=now,
        last_seen_at=now,
        enrichment=enrichment or {},
    )
    session.add(obs)
    await session.flush()
    return obs


@pytest.mark.asyncio
async def test_one_active_source_keeps_canonical_opportunity_active(db_session: AsyncSession):
    opp = await _seed_opportunity(db_session)
    await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:greenhouse",
        url="https://boards.greenhouse.io/test/1",
    )
    await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="forkjob:rss",
        url="https://example.com/rss/1",
    )

    adapter = MockCareerOpsAdapter()
    adapter.liveness_responses["https://boards.greenhouse.io/test/1"] = CareerOpsLivenessReceipt(
        url="https://boards.greenhouse.io/test/1",
        status="expired",
        code="ats_404",
        reason="Posting not found",
        method="api",
        checked_at=datetime.now(UTC).isoformat(),
    )
    adapter.liveness_responses["https://example.com/rss/1"] = CareerOpsLivenessReceipt(
        url="https://example.com/rss/1",
        status="active",
        code="http_200",
        reason="Live",
        method="browser",
        checked_at=datetime.now(UTC).isoformat(),
    )

    service = OpportunityListingService(adapter=adapter)
    summary = await service.verify_opportunity_liveness(db_session, opp.id)

    assert summary["source_status"] == "active"
    assert opp.source_status == "active"
    assert opp.closed_at is None


@pytest.mark.asyncio
async def test_all_sources_expired_requires_two_step_confirmation(db_session: AsyncSession):
    opp = await _seed_opportunity(db_session)
    obs = await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:lever",
        url="https://jobs.lever.co/test/1",
    )

    adapter = MockCareerOpsAdapter()
    adapter.liveness_responses["https://jobs.lever.co/test/1"] = CareerOpsLivenessReceipt(
        url="https://jobs.lever.co/test/1",
        status="expired",
        code="lever_api_404",
        reason="Posting not found",
        method="api",
        checked_at=datetime.now(UTC).isoformat(),
    )

    service = OpportunityListingService(adapter=adapter)
    t0 = datetime.now(UTC)

    # 1st check: sets likely_closed
    s1 = await service.verify_opportunity_liveness(db_session, opp.id, now=t0)
    assert s1["source_status"] == "likely_closed"
    assert opp.source_status == "likely_closed"
    assert obs.source_status == "likely_closed"
    assert opp.closed_at is None

    # Check 6 hours later: still likely_closed (< 12 hours)
    t_plus_6h = t0 + timedelta(hours=6)
    s2 = await service.verify_opportunity_liveness(db_session, opp.id, force=True, now=t_plus_6h)
    assert s2["source_status"] == "likely_closed"
    assert opp.source_status == "likely_closed"
    assert opp.closed_at is None

    # 2nd confirmation >= 12h later (13h): sets closed
    t_plus_13h = t0 + timedelta(hours=13)
    s3 = await service.verify_opportunity_liveness(db_session, opp.id, force=True, now=t_plus_13h)
    assert s3["source_status"] == "closed"
    assert opp.source_status == "closed"
    assert obs.source_status == "closed"
    assert opp.closed_at is not None
    assert obs.source_removed_at is not None


@pytest.mark.asyncio
async def test_uncertain_liveness_never_closes_opportunity(db_session: AsyncSession):
    opp = await _seed_opportunity(db_session)
    await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:workday",
        url="https://workday.example.com/job/1",
    )

    adapter = MockCareerOpsAdapter()
    adapter.liveness_responses["https://workday.example.com/job/1"] = CareerOpsLivenessReceipt(
        url="https://workday.example.com/job/1",
        status="uncertain",
        code="timeout",
        reason="Connection timed out",
        method="bridge",
        checked_at=datetime.now(UTC).isoformat(),
    )

    service = OpportunityListingService(adapter=adapter)
    summary = await service.verify_opportunity_liveness(db_session, opp.id)

    assert summary["source_status"] == "active"
    assert opp.source_status == "active"
    assert opp.closed_at is None


@pytest.mark.asyncio
async def test_liveness_check_uses_24h_cache_unless_forced(db_session: AsyncSession):
    opp = await _seed_opportunity(db_session)
    t0 = datetime.now(UTC)
    await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:ashby",
        url="https://jobs.ashbyhq.com/test/1",
        enrichment={
            "liveness": {
                "url": "https://jobs.ashbyhq.com/test/1",
                "status": "active",
                "code": "ashby_api_ok",
                "reason": "Cached",
                "method": "api",
                "checked_at": t0.isoformat(),
            }
        },
    )

    adapter = MockCareerOpsAdapter()
    service = OpportunityListingService(adapter=adapter)

    # Within 24h (e.g. 5 hours later): should NOT call adapter
    await service.verify_opportunity_liveness(db_session, opp.id, now=t0 + timedelta(hours=5))
    assert len(adapter.liveness_calls) == 0

    # Forced: should call adapter
    await service.verify_opportunity_liveness(db_session, opp.id, force=True, now=t0 + timedelta(hours=5))
    assert len(adapter.liveness_calls) == 1


@pytest.mark.asyncio
async def test_jd_enrichment_promotes_text_and_touches_search_text(db_session: AsyncSession):
    opp = await _seed_opportunity(
        db_session,
        url="https://boards.greenhouse.io/test/1",
        description="Short stub",
    )
    await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:greenhouse",
        url="https://boards.greenhouse.io/test/1",
    )

    adapter = MockCareerOpsAdapter()
    long_jd = "We are seeking a Staff Infrastructure Engineer to design, build and operate our planetary-scale cloud infrastructure. " * 5
    adapter.extraction_responses["https://boards.greenhouse.io/test/1"] = CareerOpsJobExtractionResult(
        url="https://boards.greenhouse.io/test/1",
        title="Staff Infrastructure Engineer",
        text=long_jd,
    )

    service = OpportunityListingService(adapter=adapter)
    res = await service.enrich_job_description(db_session, opp.id)

    assert res["promoted"] is True
    assert opp.raw.get("description") == long_jd.strip()
    assert "planetary-scale" in opp.raw.get("description", "")


@pytest.mark.asyncio
async def test_jd_enrichment_skips_when_substantive_description_already_exists(db_session: AsyncSession):
    substantive = "Existing description already has way more than two hundred characters. " * 5
    opp = await _seed_opportunity(db_session, description=substantive)
    await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:greenhouse",
        url="https://boards.greenhouse.io/test/1",
    )

    adapter = MockCareerOpsAdapter()
    service = OpportunityListingService(adapter=adapter)
    res = await service.enrich_job_description(db_session, opp.id)

    assert res["promoted"] is False
    assert len(adapter.extraction_calls) == 0
