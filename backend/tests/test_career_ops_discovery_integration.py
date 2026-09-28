import shutil
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.modules.opportunity import service
from app.modules.opportunity.models import Opportunity, OpportunitySourceObservation
from app.modules.opportunity.worker import NativeJob, poll_source
from app.sources.base import FetchOutcome, RawItem
from app.sources.forkjob_core.models import cluster_key as compute_cluster_key
from app.worker import jobs as worker_jobs
from app.worker.jobs import _lease_map, _source_catalog


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
        db_session, [NativeJob(forkjob_item)], "forkjob_core:greenhouse:stripe"
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
    assert obs[0].source == "forkjob_core:greenhouse:stripe"

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
    await service.ingest_jobs(
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
    assert "forkjob_core:greenhouse:stripe" in sources
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


@pytest.mark.asyncio
async def test_cross_url_cluster_does_not_merge_without_strong_evidence(db_session: AsyncSession):
    """A coarse cluster alone cannot prove that two ATS URLs are one requisition."""
    ckey = compute_cluster_key("ClusterCorp", "Senior Infrastructure Engineer", "Remote")
    url_gh = "https://boards.greenhouse.io/clustercorp/jobs/111"
    url_wd = "https://clustercorp.wd1.myworkdayjobs.com/careers/job/222"

    gh_item = RawItem(
        external_id=url_gh,
        title="Senior Infrastructure Engineer",
        url=url_gh,
        extra={
            "organization": "ClusterCorp",
            "location": "Remote",
            "cluster_key": ckey,
            "forkjob": {"cluster_key": ckey},
            "career_ops": {"provider": "greenhouse"},
        },
    )
    added1 = await service.ingest_jobs(db_session, [NativeJob(gh_item)], "careerops:greenhouse")
    await db_session.commit()
    assert added1 == 1

    wd_item = RawItem(
        external_id=url_wd,
        title="Senior Infrastructure Engineer",
        url=url_wd,
        extra={
            "organization": "ClusterCorp",
            "location": "Remote",
            "cluster_key": ckey,
            "forkjob": {"cluster_key": ckey},
            "career_ops": {"provider": "workday"},
        },
    )
    added2 = await service.ingest_jobs(db_session, [NativeJob(wd_item)], "careerops:workday")
    await db_session.commit()
    assert added2 == 1

    opps = (
        await db_session.execute(
            select(Opportunity).where(Opportunity.organization == "ClusterCorp")
        )
    ).scalars().all()
    assert len(opps) == 2

    obs = (
        await db_session.execute(
            select(OpportunitySourceObservation).where(
                OpportunitySourceObservation.opportunity_id.in_([opp.id for opp in opps])
            )
        )
    ).scalars().all()
    assert len(obs) == 2
    sources = {o.source for o in obs}
    assert sources == {"careerops:greenhouse", "careerops:workday"}
    assert len({o.opportunity_id for o in obs}) == 2


@pytest.mark.asyncio
async def test_distinct_roles_remain_separate_opportunities(db_session: AsyncSession):
    """Different roles produce different cluster keys and separate Opportunities."""
    ckey1 = compute_cluster_key("DistinctCorp", "Senior Infrastructure Engineer", "Remote")
    ckey2 = compute_cluster_key("DistinctCorp", "Senior Product Designer", "Remote")

    item1 = RawItem(
        external_id="https://boards.greenhouse.io/distinctcorp/jobs/infra-1",
        title="Senior Infrastructure Engineer",
        url="https://boards.greenhouse.io/distinctcorp/jobs/infra-1",
        extra={
            "organization": "DistinctCorp",
            "location": "Remote",
            "cluster_key": ckey1,
            "forkjob": {"cluster_key": ckey1},
        },
    )
    item2 = RawItem(
        external_id="https://boards.greenhouse.io/distinctcorp/jobs/design-1",
        title="Senior Product Designer",
        url="https://boards.greenhouse.io/distinctcorp/jobs/design-1",
        extra={
            "organization": "DistinctCorp",
            "location": "Remote",
            "cluster_key": ckey2,
            "forkjob": {"cluster_key": ckey2},
        },
    )

    await service.ingest_jobs(db_session, [NativeJob(item1)], "careerops:greenhouse")
    await service.ingest_jobs(db_session, [NativeJob(item2)], "careerops:greenhouse")
    await db_session.commit()

    opps = (
        await db_session.execute(
            select(Opportunity).where(Opportunity.organization == "DistinctCorp")
        )
    ).scalars().all()
    assert len(opps) == 2


@pytest.mark.asyncio
async def test_non_destructive_refresh_rich_forkjob_then_sparse_careerops(db_session: AsyncSession):
    """Rich forkjob discovery is NOT degraded when later seen by sparse career-ops scan."""
    ckey = compute_cluster_key("RichCorp", "Principal Python Architect", "Remote")

    rich_item = RawItem(
        external_id="rich-1",
        title="Principal Python Architect",
        url="https://jobs.richcorp.com/roles/1",
        summary="Extensive python and asyncpg expertise required.",
        published_at=datetime(2026, 9, 21, tzinfo=UTC),
        extra={
            "organization": "RichCorp",
            "location": "Remote",
            "description": "Extensive python and asyncpg expertise required.",
            "remote": "hybrid",
            "compensation": "$200,000 - $250,000",
            "cluster_key": ckey,
            "forkjob": {
                "cluster_key": ckey,
                "country": "TR",
                "region": "EMEA",
                "score": 88.0,
                "custom_rich_signal": "verified",
            },
        },
    )
    added1 = await service.ingest_jobs(
        db_session, [NativeJob(rich_item)], "forkjob_core:greenhouse:richcorp"
    )
    await db_session.commit()
    assert added1 == 1

    opp = (
        await db_session.execute(
            select(Opportunity).where(Opportunity.organization == "RichCorp")
        )
    ).scalar_one()
    assert opp.remote == "hybrid"
    assert opp.compensation == "$200,000 - $250,000"
    assert opp.country == "TR"
    assert opp.region == "EMEA"
    assert opp.score is not None
    assert opp.score_source == "forkjob_core-candidate-fit-v2"

    # Ingest sparse career-ops item
    sparse_item = RawItem(
        external_id="https://jobs.richcorp.com/roles/1/?utm_source=careerops",
        title="Principal Python Architect",
        url="https://jobs.richcorp.com/roles/1/?utm_source=careerops",
        summary=None,
        published_at=None,
        extra={
            "organization": "RichCorp",
            "location": "Remote",
            "cluster_key": ckey,
            "forkjob": {"cluster_key": ckey},
            "career_ops": {
                "engine_version": "1.34.0",
                "provider": "greenhouse",
                "date_status": "none",
            },
        },
    )
    added2 = await service.ingest_jobs(
        db_session, [NativeJob(sparse_item)], "careerops:greenhouse"
    )
    await db_session.commit()
    assert added2 == 0

    await db_session.refresh(opp)
    assert opp.remote == "hybrid"
    assert opp.compensation == "$200,000 - $250,000"
    assert opp.country == "TR"
    assert opp.region == "EMEA"
    assert opp.score is not None
    assert opp.score_source == "forkjob_core-candidate-fit-v2"
    assert (opp.raw or {}).get("description") == "Extensive python and asyncpg expertise required."
    assert (opp.raw or {}).get("forkjob", {}).get("custom_rich_signal") == "verified"
    assert (opp.raw or {}).get("career_ops", {}).get("provider") == "greenhouse"
    assert set((opp.raw or {}).get("sources", [])) == {
        "forkjob_core:greenhouse:richcorp",
        "careerops:greenhouse",
    }


@pytest.mark.asyncio
async def test_non_destructive_refresh_sparse_careerops_then_rich_forkjob(db_session: AsyncSession):
    """Sparse career-ops discovery is cleanly upgraded when later seen by rich forkjob scan."""
    ckey = compute_cluster_key("SparseCorp", "Staff Systems Engineer", "Remote")

    sparse_item = RawItem(
        external_id="https://jobs.lever.co/sparsecorp/111",
        title="Staff Systems Engineer",
        url="https://jobs.lever.co/sparsecorp/111",
        extra={
            "organization": "SparseCorp",
            "location": "Remote",
            "cluster_key": ckey,
            "forkjob": {"cluster_key": ckey},
            "career_ops": {
                "engine_version": "1.34.0",
                "provider": "lever",
            },
        },
    )
    added1 = await service.ingest_jobs(
        db_session, [NativeJob(sparse_item)], "careerops:lever"
    )
    await db_session.commit()
    assert added1 == 1

    rich_item = RawItem(
        external_id="sparse-rich-222",
        title="Staff Systems Engineer",
        url="https://jobs.lever.co/sparsecorp/111?utm_source=forkjob",
        summary="Deep distributed systems and Rust experience required.",
        published_at=datetime(2026, 9, 22, tzinfo=UTC),
        extra={
            "organization": "SparseCorp",
            "location": "Remote",
            "description": "Deep distributed systems and Rust experience required.",
            "remote": "remote",
            "compensation": "$220,000",
            "cluster_key": ckey,
            "forkjob": {
                "cluster_key": ckey,
                "country": "US",
                "region": "AMER",
                "score": 92.0,
            },
        },
    )
    added2 = await service.ingest_jobs(
        db_session, [NativeJob(rich_item)], "forkjob_core:lever:sparsecorp"
    )
    await db_session.commit()
    assert added2 == 0

    opp = (
        await db_session.execute(
            select(Opportunity).where(Opportunity.organization == "SparseCorp")
        )
    ).scalar_one()
    assert opp.remote == "remote"
    assert opp.compensation == "$220,000"
    assert opp.country == "US"
    assert opp.region == "AMER"
    assert opp.score is not None
    assert opp.score_source == "forkjob_core-candidate-fit-v2"
    assert (opp.raw or {}).get("description") == "Deep distributed systems and Rust experience required."
    assert (opp.raw or {}).get("career_ops", {}).get("provider") == "lever"
    assert (opp.raw or {}).get("forkjob", {}).get("score") == 92.0


def test_worker_lease_catalog_includes_career_ops(monkeypatch: pytest.MonkeyPatch):
    """Worker source catalog and lease map include career-ops reverse sources when enabled."""
    from app.config import settings

    # Default disabled: career-ops sources not in catalog
    monkeypatch.setattr(settings, "career_ops_enabled", False)
    worker_jobs._LEASE_CACHE = None
    catalog = _source_catalog()
    catalog_ids = {s.id for s in catalog}
    assert "careerops:greenhouse" not in catalog_ids

    # Enabled: career-ops sources in catalog and lease >= 300s
    monkeypatch.setattr(settings, "career_ops_enabled", True)
    monkeypatch.setattr(settings, "career_ops_discovery_enabled", True)
    worker_jobs._LEASE_CACHE = None
    catalog = _source_catalog()
    catalog_ids = {s.id for s in catalog}
    assert "careerops:greenhouse" in catalog_ids
    assert "careerops:lever" in catalog_ids
    assert "careerops:workday" in catalog_ids
    assert {"careerops:boards", "careerops:companies"} <= catalog_ids

    lease_map = _lease_map()
    assert "careerops:greenhouse" in lease_map
    assert lease_map["careerops:greenhouse"] >= timedelta(seconds=300)
    assert {"careerops:boards", "careerops:companies"} <= set(lease_map)
