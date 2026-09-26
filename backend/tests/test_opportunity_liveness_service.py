from collections.abc import AsyncIterator
import uuid
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity
from app.db import SessionLocal
from app.integrations.career_ops.models import (
    CareerOpsJobExtractionResult,
    CareerOpsLivenessReceipt,
)
from app.modules.opportunity.intelligence import listing_fingerprint
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
    last_seen_at: datetime | None = None,
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
        last_seen_at=last_seen_at or now,
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
    last_seen_at: datetime | None = None,
    enrichment: dict | None = None,
) -> OpportunitySourceObservation:
    now = datetime.now(UTC)
    obs = OpportunitySourceObservation(
        opportunity_id=opportunity_id,
        source=source,
        canonical_url=url,
        source_status=source_status,
        first_seen_at=now,
        last_seen_at=last_seen_at or now,
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
async def test_all_sources_expired_requires_two_step_confirmation_without_force(db_session: AsyncSession):
    """Mandatory test (Finding C & Section 13): closing requires fresh second expired observation WITHOUT force=True."""
    opp = await _seed_opportunity(db_session)
    obs = await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:lever",
        url="https://jobs.lever.co/test/1",
    )

    adapter = MockCareerOpsAdapter()
    t0 = datetime.now(UTC)
    adapter.liveness_responses["https://jobs.lever.co/test/1"] = CareerOpsLivenessReceipt(
        url="https://jobs.lever.co/test/1",
        status="expired",
        code="lever_api_404",
        reason="Posting not found",
        method="api",
        checked_at=t0.isoformat(),
    )

    service = OpportunityListingService(adapter=adapter)

    # 1st check at T0: sets likely_closed (adapter called once)
    s1 = await service.verify_opportunity_liveness(db_session, opp.id, now=t0)
    assert s1["source_status"] == "likely_closed"
    assert opp.source_status == "likely_closed"
    assert obs.source_status == "likely_closed"
    assert opp.closed_at is None
    assert len(adapter.liveness_calls) == 1

    # Check 6 hours later (< 12 hours): cache is used, remains likely_closed, adapter NOT called again
    t_plus_6h = t0 + timedelta(hours=6)
    s2 = await service.verify_opportunity_liveness(db_session, opp.id, now=t_plus_6h)
    assert s2["source_status"] == "likely_closed"
    assert opp.source_status == "likely_closed"
    assert opp.closed_at is None
    assert len(adapter.liveness_calls) == 1

    # 2nd confirmation >= 12h later (13h):
    # CRITICAL INVARIANT: EVEN WITHOUT force=True, closure confirmation forces a fresh adapter invocation!
    t_plus_13h = t0 + timedelta(hours=13)
    adapter.liveness_responses["https://jobs.lever.co/test/1"] = CareerOpsLivenessReceipt(
        url="https://jobs.lever.co/test/1",
        status="expired",
        code="lever_api_404",
        reason="Posting confirmed not found on independent check",
        method="api",
        checked_at=t_plus_13h.isoformat(),
    )
    s3 = await service.verify_opportunity_liveness(db_session, opp.id, now=t_plus_13h)
    assert len(adapter.liveness_calls) == 2  # Fresh network call occurred!
    assert s3["source_status"] == "closed"
    assert opp.source_status == "closed"
    assert obs.source_status == "closed"
    assert opp.closed_at is not None
    assert obs.source_removed_at is not None


@pytest.mark.asyncio
async def test_same_checked_at_receipt_replay_cannot_close_source(db_session: AsyncSession):
    """Replaying the exact same checked_at receipt must NEVER satisfy 2nd confirmation (Finding 10-11)."""
    opp = await _seed_opportunity(db_session)
    obs = await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:lever",
        url="https://jobs.lever.co/test/replay",
    )

    t0 = datetime.now(UTC)
    fixed_receipt = CareerOpsLivenessReceipt(
        url="https://jobs.lever.co/test/replay",
        status="expired",
        code="lever_api_404",
        reason="Posting not found",
        method="api",
        checked_at=t0.isoformat(),  # Fixed timestamp
    )

    adapter = MockCareerOpsAdapter()
    adapter.liveness_responses["https://jobs.lever.co/test/replay"] = fixed_receipt
    service = OpportunityListingService(adapter=adapter)

    # 1st check at T0
    await service.verify_opportunity_liveness(db_session, opp.id, now=t0)
    assert obs.source_status == "likely_closed"

    # 2nd check at T+13h, but adapter returns the same checked_at timestamp (replay)
    t_plus_13h = t0 + timedelta(hours=13)
    await service.verify_opportunity_liveness(db_session, opp.id, force=True, now=t_plus_13h)
    # Must remain likely_closed!
    assert obs.source_status == "likely_closed"
    assert opp.source_status == "likely_closed"
    assert opp.closed_at is None


@pytest.mark.asyncio
async def test_second_check_uncertain_never_closes(db_session: AsyncSession):
    """Second observation returning uncertain must keep opportunity likely_closed (Finding 13)."""
    opp = await _seed_opportunity(db_session)
    obs = await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:ashby",
        url="https://jobs.ashbyhq.com/test/uncertain",
    )

    t0 = datetime.now(UTC)
    adapter = MockCareerOpsAdapter()
    adapter.liveness_responses["https://jobs.ashbyhq.com/test/uncertain"] = CareerOpsLivenessReceipt(
        url="https://jobs.ashbyhq.com/test/uncertain",
        status="expired",
        code="ashby_404",
        reason="Not found",
        method="api",
        checked_at=t0.isoformat(),
    )
    service = OpportunityListingService(adapter=adapter)

    await service.verify_opportunity_liveness(db_session, opp.id, now=t0)
    assert obs.source_status == "likely_closed"

    # Second check at T+13h returns uncertain (e.g. timeout)
    t_plus_13h = t0 + timedelta(hours=13)
    adapter.liveness_responses["https://jobs.ashbyhq.com/test/uncertain"] = CareerOpsLivenessReceipt(
        url="https://jobs.ashbyhq.com/test/uncertain",
        status="uncertain",
        code="timeout",
        reason="Timed out",
        method="bridge",
        checked_at=t_plus_13h.isoformat(),
    )
    await service.verify_opportunity_liveness(db_session, opp.id, force=True, now=t_plus_13h)
    assert obs.source_status == "likely_closed"
    assert opp.source_status == "likely_closed"
    assert opp.closed_at is None


@pytest.mark.asyncio
async def test_second_check_active_reopens_source_and_opportunity(db_session: AsyncSession):
    """When a closed/likely_closed opportunity is observed active, it reopens cleanly (Finding 40)."""
    opp = await _seed_opportunity(db_session, source_status="closed")
    opp.closed_at = datetime.now(UTC) - timedelta(days=2)
    obs = await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:greenhouse",
        url="https://boards.greenhouse.io/test/reopen",
        source_status="closed",
    )
    obs.source_removed_at = datetime.now(UTC) - timedelta(days=2)

    adapter = MockCareerOpsAdapter()
    t_now = datetime.now(UTC)
    adapter.liveness_responses["https://boards.greenhouse.io/test/reopen"] = CareerOpsLivenessReceipt(
        url="https://boards.greenhouse.io/test/reopen",
        status="active",
        code="greenhouse_api_ok",
        reason="Posting is back online",
        method="api",
        checked_at=t_now.isoformat(),
    )
    service = OpportunityListingService(adapter=adapter)

    summary = await service.verify_opportunity_liveness(db_session, opp.id, force=True, now=t_now)
    assert summary["source_status"] == "active"
    assert opp.source_status == "active"
    assert opp.closed_at is None
    assert obs.source_status == "active"
    assert obs.source_removed_at is None


@pytest.mark.asyncio
async def test_liveness_checks_do_not_mutate_discovery_last_seen_timestamps(db_session: AsyncSession):
    """Invariant: Liveness checks are URL health probes, NOT discovery sightings (Finding D & Section 15)."""
    t0 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    opp = await _seed_opportunity(db_session, last_seen_at=t0)
    obs = await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:greenhouse",
        url="https://boards.greenhouse.io/test/ts",
        last_seen_at=t0,
    )

    t_check = t0 + timedelta(days=7)
    adapter = MockCareerOpsAdapter()
    adapter.liveness_responses["https://boards.greenhouse.io/test/ts"] = CareerOpsLivenessReceipt(
        url="https://boards.greenhouse.io/test/ts",
        status="active",
        code="greenhouse_api_ok",
        reason="Live",
        method="api",
        checked_at=t_check.isoformat(),
    )
    service = OpportunityListingService(adapter=adapter)

    await service.verify_opportunity_liveness(db_session, opp.id, now=t_check)

    # Observation and Opportunity last_seen_at MUST remain T0!
    assert obs.last_seen_at == t0
    assert opp.last_seen_at == t0
    # Health check timestamp is stored in enrichment
    assert obs.enrichment["liveness"]["checked_at"] == t_check.isoformat()


@pytest.mark.asyncio
async def test_jd_provenance_attaches_to_exact_extracted_source(db_session: AsyncSession):
    """JD extraction evidence must attach only to the observation corresponding to extracted URL (Finding E)."""
    opp = await _seed_opportunity(db_session, url="https://boards.greenhouse.io/acme/job/123")
    obs_linkedin = await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="forkjob:linkedin",
        url="https://www.linkedin.com/jobs/view/999",
    )
    obs_greenhouse = await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:greenhouse",
        url="https://boards.greenhouse.io/acme/job/123",
    )

    adapter = MockCareerOpsAdapter()
    adapter.extraction_responses["https://boards.greenhouse.io/acme/job/123"] = CareerOpsJobExtractionResult(
        url="https://boards.greenhouse.io/acme/job/123",
        title="Principal Infrastructure Architect",
        text="Substantive job description extracted from Greenhouse with high fidelity and rich requirements. " * 5,
    )

    service = OpportunityListingService(adapter=adapter)
    res = await service.enrich_job_description(db_session, opp.id)

    assert res["promoted"] is True
    assert res["selected_url"] == "https://boards.greenhouse.io/acme/job/123"

    # Evidence MUST be attached to Greenhouse observation, NOT LinkedIn!
    assert "jd_extraction" in (obs_greenhouse.enrichment or {})
    jd_meta = obs_greenhouse.enrichment["jd_extraction"]
    assert jd_meta["source_url"] == "https://boards.greenhouse.io/acme/job/123"
    assert jd_meta["promoted"] is True
    assert jd_meta["jd_text_length"] > 200

    assert "jd_extraction" not in (obs_linkedin.enrichment or {})


@pytest.mark.asyncio
async def test_non_destructive_jd_promotion_preserves_richer_canonical_description(db_session: AsyncSession):
    """force=True means refetch, NOT destructive overwrite of richer canonical description (Finding F)."""
    rich_description = "Extremely detailed description with all team charters, system architecture, tech stack, and benefits. " * 80
    assert len(rich_description) > 5000

    opp = await _seed_opportunity(
        db_session,
        url="https://boards.greenhouse.io/test/rich",
        description=rich_description,
    )
    obs = await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:greenhouse",
        url="https://boards.greenhouse.io/test/rich",
    )

    adapter = MockCareerOpsAdapter()
    # Scraper returned a weaker 400-char stub
    poor_candidate = "Short 400 char summary. We are hiring a developer. Apply online through our portal right now for this position." * 4
    assert 200 < len(poor_candidate) < 1000

    adapter.extraction_responses["https://boards.greenhouse.io/test/rich"] = CareerOpsJobExtractionResult(
        url="https://boards.greenhouse.io/test/rich",
        title="Developer",
        text=poor_candidate,
    )

    service = OpportunityListingService(adapter=adapter)
    res = await service.enrich_job_description(db_session, opp.id, force=True)

    # Refetch happened, but candidate was REJECTED from promotion
    assert res["promoted"] is False
    assert res["promotion_reason"] == "canonical_description_richer"
    # Canonical description must remain untouched!
    assert opp.raw.get("description") == rich_description

    # Source-level extraction evidence is STILL preserved with promoted=False
    assert "jd_extraction" in (obs.enrichment or {})
    assert obs.enrichment["jd_extraction"]["promoted"] is False
    assert obs.enrichment["jd_extraction"]["promotion_reason"] == "canonical_description_richer"


@pytest.mark.asyncio
async def test_jd_promotion_promotes_when_candidate_is_substantially_richer(db_session: AsyncSession):
    """When candidate JD is substantially richer than existing stub, it is promoted (Finding F)."""
    stub_description = "Looking for a Python dev. Send resume."
    opp = await _seed_opportunity(
        db_session,
        url="https://boards.greenhouse.io/test/sub",
        description=stub_description,
    )
    await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:greenhouse",
        url="https://boards.greenhouse.io/test/sub",
    )

    rich_candidate = "Full job description with complete responsibilities, core qualifications, preferred qualifications, and salary info. " * 30

    adapter = MockCareerOpsAdapter()
    adapter.extraction_responses["https://boards.greenhouse.io/test/sub"] = CareerOpsJobExtractionResult(
        url="https://boards.greenhouse.io/test/sub",
        title="Python Engineer",
        text=rich_candidate,
    )

    service = OpportunityListingService(adapter=adapter)
    res = await service.enrich_job_description(db_session, opp.id, force=True)

    assert res["promoted"] is True
    assert opp.raw.get("description") == rich_candidate.strip()


@pytest.mark.asyncio
async def test_same_jd_hash_causes_no_unnecessary_rewrite_or_event(db_session: AsyncSession):
    """Identical JD content (modulo formatting) does not trigger canonical rewrite (Finding F)."""
    base_text = "Senior Software Engineer with extensive Python and distributed systems experience. " * 5
    opp = await _seed_opportunity(
        db_session,
        url="https://boards.greenhouse.io/test/same",
        description=base_text,
    )
    await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:greenhouse",
        url="https://boards.greenhouse.io/test/same",
    )

    # Same text with whitespace/newline variations
    varied_text = "\n\n  " + base_text.replace(" ", "  ") + "  \n\n"
    adapter = MockCareerOpsAdapter()
    adapter.extraction_responses["https://boards.greenhouse.io/test/same"] = CareerOpsJobExtractionResult(
        url="https://boards.greenhouse.io/test/same",
        title="Engineer",
        text=varied_text,
    )

    service = OpportunityListingService(adapter=adapter)
    res = await service.enrich_job_description(db_session, opp.id, force=True)

    assert res["promoted"] is False
    assert res["promotion_reason"] == "identical_content"


@pytest.mark.asyncio
async def test_evaluation_staleness_on_jd_material_change_vs_poorer_source(db_session: AsyncSession):
    """Evaluation fingerprint changes ONLY on material canonical description changes (Finding 28 & 51)."""
    rich_text = "Comprehensive job description with deep tech requirements. " * 40
    opp = await _seed_opportunity(
        db_session,
        url="https://boards.greenhouse.io/test/stale",
        description=rich_text,
    )
    await _seed_observation(
        db_session,
        opportunity_id=opp.id,
        source="careerops:greenhouse",
        url="https://boards.greenhouse.io/test/stale",
    )

    initial_fp = listing_fingerprint(opp, title="Backend Engineer")

    # 1. Poorer source extracted -> not promoted -> fingerprint stays IDENTICAL (no false staleness)
    poor_text = "Short stub of text. " * 15
    adapter = MockCareerOpsAdapter()
    adapter.extraction_responses["https://boards.greenhouse.io/test/stale"] = CareerOpsJobExtractionResult(
        url="https://boards.greenhouse.io/test/stale",
        title="Backend Engineer",
        text=poor_text,
    )
    service = OpportunityListingService(adapter=adapter)
    await service.enrich_job_description(db_session, opp.id, force=True)

    after_poor_fp = listing_fingerprint(opp, title="Backend Engineer")
    assert initial_fp == after_poor_fp

    # 2. Materially richer text extracted -> promoted -> fingerprint CHANGES (real staleness)
    even_richer_text = rich_text + " Extra section on planetary systems. " * 50
    adapter.extraction_responses["https://boards.greenhouse.io/test/stale"] = CareerOpsJobExtractionResult(
        url="https://boards.greenhouse.io/test/stale",
        title="Backend Engineer",
        text=even_richer_text,
    )
    await service.enrich_job_description(db_session, opp.id, force=True)

    after_rich_fp = listing_fingerprint(opp, title="Backend Engineer")
    assert initial_fp != after_rich_fp
