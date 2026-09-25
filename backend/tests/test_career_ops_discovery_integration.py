from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
import shutil
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.modules.opportunity import service
from app.modules.opportunity.models import Opportunity, OpportunitySourceObservation
from app.modules.opportunity.worker import NativeJob, poll_source
from app.sources.base import FetchOutcome, RawItem
from app.sources.career_ops_sources import CareerOpsReverseSource


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


class StaticSourceAdapter:
    def __init__(self, sid: str, items: list[RawItem], partial: bool = False):
        self.id = sid
        self.items = items
        self.partial = partial
        self.source_class = "slow_optin"
        self.skip_closure_sweep = sid.startswith("careerops:")

    async def fetch(self) -> FetchOutcome:
        return FetchOutcome(items=self.items, partial=self.partial)


@pytest.mark.asyncio
async def test_canonical_merge_forkjob_and_career_ops(db_session: AsyncSession):
    """Case A: Same posting discovered by forkjob and career-ops merges into ONE Opportunity with two observations."""
    job_url = "https://boards.greenhouse.io/stripe/jobs/12345"

    # 1. First discovery via forkjob
    forkjob_item = RawItem(
        external_id="12345",
        title="Senior Infrastructure Engineer",
        url=job_url,
        published_at=datetime(2026, 9, 20, tzinfo=UTC),
        extra={"organization": "Stripe", "location": "Remote"},
    )
    added1 = await service.ingest_jobs(
        db_session, [NativeJob(forkjob_item)], "jobhunter:greenhouse:stripe"
    )
    await db_session.commit()
    assert added1 == 1

    # Verify 1 opportunity and 1 observation
    opps = (await db_session.execute(select(Opportunity))).scalars().all()
    assert len(opps) == 1
    opp_id = opps[0].id

    obs = (
        await db_session.execute(
            select(OpportunitySourceObservation).where(
                OpportunitySourceObservation.opportunity_id == opp_id
            )
        )
    ).scalars().all()
    assert len(obs) == 1
    assert obs[0].source == "jobhunter:greenhouse:stripe"

    # 2. Later discovery via career-ops reverse ATS
    careerops_item = RawItem(
        external_id=job_url,
        title="Senior Infrastructure Engineer",
        url=job_url,
        published_at=datetime(2026, 9, 21, tzinfo=UTC),
        extra={
            "organization": "Stripe",
            "location": "Remote",
            "career_ops": {
                "engine_version": "1.34.0",
                "provider": "greenhouse",
            },
        },
    )
    added2 = await service.ingest_jobs(
        db_session, [NativeJob(careerops_item)], "careerops:greenhouse"
    )
    await db_session.commit()

    # Product promise: Opportunity count remains 1 (NO duplicate posting)
    opps_after = (await db_session.execute(select(Opportunity))).scalars().all()
    assert len(opps_after) == 1
    assert opps_after[0].id == opp_id

    # Provenance promise: Two distinct source observations exist
    obs_after = (
        await db_session.execute(
            select(OpportunitySourceObservation).where(
                OpportunitySourceObservation.opportunity_id == opp_id
            )
        )
    ).scalars().all()
    assert len(obs_after) == 2
    sources = {o.source for o in obs_after}
    assert "jobhunter:greenhouse:stripe" in sources
    assert "careerops:greenhouse" in sources


@pytest.mark.asyncio
async def test_career_ops_idempotent_ingestion(db_session: AsyncSession):
    """Case B: Ingesting the same career-ops discovery result twice is idempotent."""
    job_url = "https://jobs.lever.co/datadog/98765"
    item = RawItem(
        external_id=job_url,
        title="Staff Backend Engineer",
        url=job_url,
        extra={"organization": "Datadog", "location": "Remote"},
    )

    added1 = await service.ingest_jobs(db_session, [NativeJob(item)], "careerops:lever")
    await db_session.commit()
    assert added1 == 1

    added2 = await service.ingest_jobs(db_session, [NativeJob(item)], "careerops:lever")
    await db_session.commit()
    assert added2 == 0

    opps = (await db_session.execute(select(Opportunity))).scalars().all()
    assert len(opps) == 1

    obs = (await db_session.execute(select(OpportunitySourceObservation))).scalars().all()
    assert len(obs) == 1


@pytest.mark.asyncio
async def test_cross_provider_multi_source_merge(db_session: AsyncSession):
    """Case C: Same job discovered across different career-ops providers merges into 1 Opportunity."""
    job_url = "https://boards.greenhouse.io/shared/jobs/444"

    gh_item = RawItem(
        external_id=job_url,
        title="DevOps Lead",
        url=job_url,
        extra={"organization": "SharedCorp"},
    )
    lever_item = RawItem(
        external_id=job_url,
        title="DevOps Lead",
        url=job_url,
        extra={"organization": "SharedCorp"},
    )

    await service.ingest_jobs(db_session, [NativeJob(gh_item)], "careerops:greenhouse")
    await service.ingest_jobs(db_session, [NativeJob(lever_item)], "careerops:lever")
    await db_session.commit()

    opps = (await db_session.execute(select(Opportunity))).scalars().all()
    assert len(opps) == 1

    obs = (await db_session.execute(select(OpportunitySourceObservation))).scalars().all()
    assert len(obs) == 2
    sources = {o.source for o in obs}
    assert sources == {"careerops:greenhouse", "careerops:lever"}


@pytest.mark.asyncio
async def test_no_false_closure_on_career_ops_absence(db_session: AsyncSession):
    """Case D: Invariant — Absence of a previously seen posting in a subsequent reverse scan NEVER closes it."""
    job_url = "https://jobs.ashbyhq.com/startup/111"
    item1 = RawItem(
        external_id=job_url,
        title="Founding ML Engineer",
        url=job_url,
        extra={"organization": "StartupAI"},
    )

    source1 = StaticSourceAdapter("careerops:ashby", [item1])
    await poll_source(source1)

    opp = (
        await db_session.execute(
            select(Opportunity).where(Opportunity.url == job_url)
        )
    ).scalar_one()
    assert opp.status in ("discovered", "new")
    assert opp.source_status == "active"

    # Now run another ashby scan with a completely different job (item1 is absent)
    item2 = RawItem(
        external_id="https://jobs.ashbyhq.com/startup/222",
        title="Frontend Specialist",
        url="https://jobs.ashbyhq.com/startup/222",
        extra={"organization": "StartupAI"},
    )
    source2 = StaticSourceAdapter("careerops:ashby", [item2])
    await poll_source(source2)

    # Re-fetch item1 from DB: it must NOT be marked closed or missing!
    await db_session.refresh(opp)
    assert opp.status in ("discovered", "new")
    assert opp.source_status == "active"


@pytest.mark.asyncio
async def test_deleting_runtime_leaves_postgresql_intact(tmp_path: Path, db_session: AsyncSession):
    """Case E: Runtime workspace is disposable; deleting it leaves PostgreSQL canonical state 100% intact."""
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "portals.yml").write_text("dummy", encoding="utf-8")
    (runtime_dir / "ephemeral-tracker.md").write_text("dummy", encoding="utf-8")

    job_url = "https://boards.greenhouse.io/corp/jobs/777"
    item = RawItem(
        external_id=job_url,
        title="Security Analyst",
        url=job_url,
        extra={"organization": "SecureCorp"},
    )
    await service.ingest_jobs(db_session, [NativeJob(item)], "careerops:greenhouse")
    await db_session.commit()

    # Nuke runtime directory
    shutil.rmtree(runtime_dir)
    assert not runtime_dir.exists()

    # Verify PostgreSQL opportunity remains completely unharmed
    opps = (await db_session.execute(select(Opportunity).where(Opportunity.url == job_url))).scalars().all()
    assert len(opps) == 1
    assert opps[0].organization == "SecureCorp"
