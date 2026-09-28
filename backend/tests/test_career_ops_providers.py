import json
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal
from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.errors import CareerOpsInvalidOutputError, CareerOpsSecurityError
from app.integrations.career_ops.models import CareerOpsProviderScanReceipt
from app.integrations.career_ops.provider_targets import (
    build_provider_targets,
    project_provider_targets,
)
from app.integrations.career_ops.runner import ExecutionResult
from app.modules.opportunity import service
from app.modules.opportunity.models import Opportunity, OpportunitySourceObservation
from app.modules.opportunity.worker import NativeJob
from app.sources.base import RawItem, SourceClass, is_general_refresh_source, source_class
from app.sources.career_ops_sources import CareerOpsProviderSource, get_career_ops_provider_sources
from app.sources.forkjob_core.registry import Registry


@pytest.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session


@pytest.mark.no_database
def test_provider_targets_project_canonical_sources_without_relevance_filters(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text("scoring:\n  role_terms: [Backend Engineer]\n", encoding="utf-8")
    targets = build_provider_targets(
        registry=Registry.load(), config_path=config, extra_path=tmp_path / "none.user"
    )
    assert {board["provider"] for board in targets["job_boards"]} >= {
        "4dayweek",
        "arbeitnow",
        "remoteok",
        "arbeitsagentur",
        "himalayas",
        "jobicy",
        "jobspresso",
        "landingjobs",
        "remotive",
        "thehub",
        "weworkremotely",
        "workingnomads",
    }
    assert any(company["provider"] == "smartrecruiters" for company in targets["tracked_companies"])
    assert all(
        company["careers_url"].startswith("https://job-boards.greenhouse.io/")
        for company in targets["tracked_companies"]
        if company["provider"] == "greenhouse"
    )
    projected = project_provider_targets(tmp_path, targets, 7)
    content = json.loads(projected.read_text(encoding="utf-8"))
    assert "title_filter" not in content
    assert "location_filter" not in content
    assert content["tracked_companies"] and content["job_boards"]


@pytest.mark.no_database
def test_provider_source_registration_is_grouped():
    sources = get_career_ops_provider_sources()
    assert [source.id for source in sources] == ["careerops:boards", "careerops:companies"]
    assert all(source.skip_closure_sweep for source in sources)
    assert source_class(sources[0]) == SourceClass.NORMAL
    assert is_general_refresh_source(sources[0])
    assert source_class(sources[1]) == SourceClass.SLOW_OPTIN


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_provider_inventory_matches_pinned_registry(tmp_path: Path):
    checkout = settings.resolved_career_ops_root
    if not checkout.exists():
        pytest.skip("Pinned career-ops checkout is not installed")
    adapter = CareerOpsAdapter(enabled=True, checkout_dir=checkout, runtime_dir=tmp_path)
    inventory = await adapter.provider_inventory()
    expected = list((checkout / "providers").glob("[!_]*.mjs"))
    assert inventory.files == len(expected) == len(inventory.providers)
    assert len({provider.id for provider in inventory.providers}) == len(expected)
    assert {plugin.id for plugin in inventory.plugins} >= {
        "apify",
        "gmail",
        "h1b-sponsor",
        "notion",
    }
    assert all(plugin.status == "unconfigured" for plugin in inventory.plugins)


class FakeRunner:
    def __init__(self, stdout: str):
        self.stdout = stdout

    async def run_script(self, script_name, args, **kwargs):
        assert script_name == "bridges/provider-scan.mjs"
        assert args[0] == "scan"
        return ExecutionResult(script_name, 0, self.stdout, "")


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_provider_scan_rejects_malformed_receipt(tmp_path: Path, monkeypatch):
    adapter = CareerOpsAdapter(
        enabled=True, runtime_dir=tmp_path, runner=FakeRunner('{"offers": []}')
    )
    monkeypatch.setattr(adapter.guard, "ensure_ready", lambda **kwargs: None)
    with pytest.raises(CareerOpsInvalidOutputError):
        await adapter.provider_scan(targets={"tracked_companies": [], "job_boards": []})
    assert not list(tmp_path.glob("provider-portals-*.yml"))


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_provider_scan_rejects_private_target_before_network(tmp_path: Path, monkeypatch):
    adapter = CareerOpsAdapter(enabled=True, runtime_dir=tmp_path, runner=FakeRunner("{}"))
    monkeypatch.setattr(adapter.guard, "ensure_ready", lambda **kwargs: None)
    with pytest.raises(CareerOpsSecurityError):
        await adapter.provider_scan(
            targets={
                "tracked_companies": [],
                "job_boards": [
                    {"name": "local", "provider": "custom", "url": "http://127.0.0.1:8787/"}
                ],
            }
        )
    assert not list(tmp_path.glob("provider-portals-*.yml"))


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_provider_source_maps_provenance_and_partial(monkeypatch):
    receipt = CareerOpsProviderScanReceipt.model_validate(
        {
            "version": "forkos.careerops.scan@1",
            "providers_loaded": 89,
            "targets_scanned": 1,
            "boards_scanned": 1,
            "companies_scanned": 0,
            "offers": [
                {
                    "company": "Example",
                    "title": "Backend Engineer",
                    "url": "https://4dayweek.io/job/example",
                    "location": "Remote",
                    "description": "Full description",
                    "salary": None,
                    "posted_at": "2026-09-28T10:00:00Z",
                    "provider": "4dayweek",
                    "target": "4 Day Week",
                    "kind": "board",
                }
            ],
            "errors": [],
            "target_results": [
                {"target": "4 Day Week", "provider": "4dayweek", "status": "ok", "found": 1}
            ],
            "partial": False,
        }
    )

    class Adapter:
        async def provider_scan(self, **kwargs):
            return receipt

    monkeypatch.setattr(
        "app.sources.career_ops_sources.build_provider_targets",
        lambda: {
            "tracked_companies": [],
            "job_boards": [{"name": "4 Day Week", "provider": "4dayweek"}],
        },
    )
    source = CareerOpsProviderSource("boards", adapter=Adapter())
    outcome = await source.fetch()
    assert outcome.partial is False
    assert outcome.items[0].extra["career_ops"]["provider"] == "4dayweek"
    assert outcome.items[0].extra["description"] == "Full description"


@pytest.mark.asyncio
async def test_provider_overlap_prefers_career_ops_without_losing_richer_data(
    db_session: AsyncSession,
):
    url = "https://www.arbeitnow.com/jobs/companies/example/backend-123"
    original = RawItem(
        external_id=url,
        title="Backend Engineer",
        url=url,
        summary="A" * 1000,
        extra={"organization": "Example", "location": "Remote", "description": "A" * 1000},
    )
    provider = RawItem(
        external_id=url,
        title="Backend Engineer",
        url=url,
        summary="Short",
        extra={
            "organization": "Example",
            "location": "Remote",
            "description": "Short",
            "career_ops": {"provider": "arbeitnow", "engine_version": "1.34.0"},
        },
    )
    assert await service.ingest_jobs(db_session, [NativeJob(original)], "jobhunter:arbeitnow") == 1
    assert await service.ingest_jobs(db_session, [NativeJob(provider)], "careerops:boards") == 0
    await db_session.commit()
    opportunities = list((await db_session.execute(select(Opportunity))).scalars())
    observations = list((await db_session.execute(select(OpportunitySourceObservation))).scalars())
    assert len(opportunities) == 1
    assert len(observations) == 2
    assert opportunities[0].source == "careerops:boards"
    assert opportunities[0].raw["description"] == "A" * 1000
    assert opportunities[0].raw["career_ops"]["provider"] == "arbeitnow"
