from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import engine
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def test_opportunity_trash_restore_and_permanent_delete(client: AsyncClient):
    title = f"Trash lifecycle {uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/opportunities",
        json={"title": title, "kind": "job", "status": "shortlisted"},
    )
    assert created.status_code == 201
    item = created.json()
    assert item["category"] == "other"
    assert item["published_at"] is None
    assert item["status"] == "shortlisted"

    trashed = await client.post(f"/api/opportunities/{item['id']}/trash")
    assert trashed.status_code == 200
    assert trashed.json()["status"] == "dismissed"
    assert trashed.json()["trashed_at"] is not None

    normal = (await client.get("/api/opportunities", params={"limit": 2000})).json()
    assert all(row["id"] != item["id"] for row in normal)
    trash = (
        await client.get(
            "/api/opportunities", params={"limit": 2000, "trashed_only": "true"}
        )
    ).json()
    assert any(row["id"] == item["id"] for row in trash)

    restored = await client.post(f"/api/opportunities/{item['id']}/restore")
    assert restored.status_code == 200
    assert restored.json()["status"] == "shortlisted"
    assert restored.json()["trashed_at"] is None

    assert (await client.post(f"/api/opportunities/{item['id']}/trash")).status_code == 200
    deleted = await client.delete(f"/api/opportunities/{item['id']}")
    assert deleted.status_code == 204
    assert (await client.get(f"/api/opportunities/{item['id']}")).status_code == 404

    events = (await client.get("/api/activity", params={"limit": 200})).json()
    matching = [
        event
        for event in events
        if event["verb"] == "opportunity.deleted"
        and event["payload"].get("opportunity_id") == item["id"]
    ]
    assert matching
    assert matching[0]["entity_id"] is None


async def test_general_patch_cannot_bypass_trash_lifecycle(client: AsyncClient):
    created = (
        await client.post(
            "/api/opportunities",
            json={"title": f"No bypass {uuid.uuid4().hex[:8]}", "kind": "job"},
        )
    ).json()
    try:
        response = await client.patch(
            f"/api/opportunities/{created['id']}", json={"status": "trashed"}
        )
        assert response.status_code == 422
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("delete from entity where id = cast(:id as uuid)"), {"id": created["id"]}
            )


async def test_permanent_delete_requires_trash_first(client: AsyncClient):
    created = (
        await client.post(
            "/api/opportunities",
            json={"title": f"Safe delete {uuid.uuid4().hex[:8]}", "kind": "job"},
        )
    ).json()
    try:
        response = await client.delete(f"/api/opportunities/{created['id']}")
        assert response.status_code == 409
        assert (await client.get(f"/api/opportunities/{created['id']}")).status_code == 200
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("delete from entity where id = cast(:id as uuid)"), {"id": created["id"]}
            )


# ---------------------------------------------------------------------------
# Faz 2: cok kaynakli yasam dongusu
# ---------------------------------------------------------------------------


def _job(tag: str, *, url: str | None = None, title: str = "Backend Developer"):
    from app.modules.opportunity.worker import NativeJob
    from app.sources.base import RawItem

    return NativeJob(
        RawItem(
            external_id=f"multi-{tag}",
            title=title,
            url=url or f"https://example.invalid/jobs/{tag}",
            summary="python backend",
            extra={"organization": "Acme", "location": "Remote", "remote": "remote", "kind": "job"},
        )
    )


async def test_one_source_staying_active_keeps_the_listing_open():
    """Bir kaynak ilanı bıraksa da başka kaynak görüyorsa ilan kapanmaz."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.modules.opportunity import service
    from app.modules.opportunity.models import Opportunity

    tag = uuid.uuid4().hex[:8]
    url = f"https://example.invalid/multi/{tag}"
    first, second = f"src-a-{tag}", f"src-b-{tag}"

    async with SessionLocal() as session:
        await service.ingest_jobs(session, [_job(tag, url=url)], source_label=first)
        await service.ingest_jobs(session, [_job(tag, url=url)], source_label=second)
        await session.commit()
        opportunity_id = (
            await session.execute(select(Opportunity.id).where(Opportunity.url == url))
        ).scalar_one()

    # A kaynagi ilani birakti: gozlem `missing` olur ama B hala aktif.
    async with SessionLocal() as session:
        result = await service.sweep_missing_opportunities(
            session, source_label=first, seen_opportunity_ids=[], grace_days=1
        )
        assert result == {"missing": 0, "likely_closed": 0, "closed": 0}
        opportunity = await session.get(Opportunity, opportunity_id)

    assert opportunity.source_status == "active"
    assert opportunity.status == "discovered"
    assert opportunity.missing_since is None


async def test_listing_closes_only_when_every_source_lets_it_go():
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.modules.opportunity import service
    from app.modules.opportunity.models import Opportunity

    tag = uuid.uuid4().hex[:8]
    url = f"https://example.invalid/multi/{tag}"
    first, second = f"src-a-{tag}", f"src-b-{tag}"

    async with SessionLocal() as session:
        await service.ingest_jobs(session, [_job(tag, url=url)], source_label=first)
        await service.ingest_jobs(session, [_job(tag, url=url)], source_label=second)
        await session.commit()
        opportunity_id = (
            await session.execute(select(Opportunity.id).where(Opportunity.url == url))
        ).scalar_one()

    later = datetime.now(UTC) + timedelta(days=10)
    for source in (first, second):
        async with SessionLocal() as session:
            await service.sweep_missing_opportunities(
                session, source_label=source, seen_opportunity_ids=[], grace_days=1, now=later
            )
        # Ikinci kademe: missing -> likely_closed
        async with SessionLocal() as session:
            await service.sweep_missing_opportunities(
                session,
                source_label=source,
                seen_opportunity_ids=[],
                grace_days=1,
                now=later + timedelta(days=2),
            )
        # Ucuncu kademe: likely_closed -> closed
        async with SessionLocal() as session:
            await service.sweep_missing_opportunities(
                session,
                source_label=source,
                seen_opportunity_ids=[],
                grace_days=1,
                now=later + timedelta(days=4),
            )

    async with SessionLocal() as session:
        opportunity = await session.get(Opportunity, opportunity_id)
    assert opportunity.source_status == "closed"
    assert opportunity.status == "closed"
    assert opportunity.closed_at is not None


async def test_user_shortlist_survives_a_source_close():
    """Kullanıcının shortlist'i kaynak kapanınca EZİLMEZ."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.modules.opportunity import service
    from app.modules.opportunity.models import Opportunity

    tag = uuid.uuid4().hex[:8]
    url = f"https://example.invalid/multi/{tag}"
    source = f"src-a-{tag}"

    async with SessionLocal() as session:
        await service.ingest_jobs(session, [_job(tag, url=url)], source_label=source)
        await session.commit()
        opportunity = (
            await session.execute(select(Opportunity).where(Opportunity.url == url))
        ).scalar_one()
        opportunity.status = "shortlisted"
        await session.commit()
        opportunity_id = opportunity.id

    later = datetime.now(UTC) + timedelta(days=10)
    for moment in (later, later + timedelta(days=2), later + timedelta(days=4)):
        async with SessionLocal() as session:
            await service.sweep_missing_opportunities(
                session, source_label=source, seen_opportunity_ids=[], grace_days=1, now=moment
            )

    async with SessionLocal() as session:
        opportunity = await session.get(Opportunity, opportunity_id)
    assert opportunity.status == "shortlisted", "kullanici durumu korunmali"
    assert opportunity.source_status == "closed"
    assert opportunity.closed_at is not None


async def test_applied_listing_stays_reachable_after_source_loss():
    """/api/applications kaynak durumundan bağımsız kalır."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.modules.opportunity import service
    from app.modules.opportunity.models import Opportunity

    tag = uuid.uuid4().hex[:8]
    url = f"https://example.invalid/multi/{tag}"
    source = f"src-a-{tag}"

    async with SessionLocal() as session:
        await service.ingest_jobs(session, [_job(tag, url=url)], source_label=source)
        await session.commit()
        opportunity_id = (
            await session.execute(select(Opportunity.id).where(Opportunity.url == url))
        ).scalar_one()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        created = await http.post(
            f"/api/opportunities/{opportunity_id}/apply",
            json={"status": "applied"},
        )
        assert created.status_code in (200, 201), created.text

    later = datetime.now(UTC) + timedelta(days=10)
    for moment in (later, later + timedelta(days=2), later + timedelta(days=4)):
        async with SessionLocal() as session:
            await service.sweep_missing_opportunities(
                session, source_label=source, seen_opportunity_ids=[], grace_days=1, now=moment
            )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        applications = (await http.get("/api/applications")).json()
    rows = applications if isinstance(applications, list) else applications.get("items", [])
    assert any(str(row["id"]) == str(opportunity_id) for row in rows)


async def test_reopen_restores_discovery_status_and_clears_the_close():
    """Kaynakta tekrar görünen ilan yeniden açılır ve olay yazılır."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.modules.opportunity import service
    from app.modules.opportunity.models import Opportunity, OpportunitySourceObservation

    tag = uuid.uuid4().hex[:8]
    url = f"https://example.invalid/multi/{tag}"
    source = f"src-a-{tag}"

    async with SessionLocal() as session:
        await service.ingest_jobs(session, [_job(tag, url=url)], source_label=source)
        await session.commit()
        opportunity_id = (
            await session.execute(select(Opportunity.id).where(Opportunity.url == url))
        ).scalar_one()

    later = datetime.now(UTC) + timedelta(days=10)
    for moment in (later, later + timedelta(days=2), later + timedelta(days=4)):
        async with SessionLocal() as session:
            await service.sweep_missing_opportunities(
                session, source_label=source, seen_opportunity_ids=[], grace_days=1, now=moment
            )

    async with SessionLocal() as session:
        assert (await session.get(Opportunity, opportunity_id)).status == "closed"

    async with SessionLocal() as session:
        await service.ingest_jobs(session, [_job(tag, url=url)], source_label=source)
        await session.commit()
        opportunity = await session.get(Opportunity, opportunity_id)
        observation = (
            await session.execute(
                select(OpportunitySourceObservation).where(
                    OpportunitySourceObservation.opportunity_id == opportunity_id
                )
            )
        ).scalar_one()

    assert opportunity.status == "discovered"
    assert opportunity.source_status == "active"
    assert opportunity.closed_at is None
    assert observation.source_status == "active"


async def test_default_browse_hides_stale_listings_but_a_filter_reaches_them():
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.modules.opportunity import service
    from app.modules.opportunity.models import Opportunity

    tag = uuid.uuid4().hex[:8]
    url = f"https://example.invalid/stale/{tag}"
    source = f"src-stale-{tag}"

    async with SessionLocal() as session:
        await service.ingest_jobs(session, [_job(tag, url=url)], source_label=source)
        await session.commit()
        opportunity = (
            await session.execute(select(Opportunity).where(Opportunity.url == url))
        ).scalar_one()
        opportunity.source_status = "missing"
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        default_ids = {
            row["id"]
            for row in (
                await http.get("/api/opportunities/browse", params={"limit": 120})
            ).json()["items"]
        }
        stale_ids = {
            row["id"]
            for row in (
                await http.get(
                    "/api/opportunities/browse",
                    params={"limit": 120, "source_status": "stale"},
                )
            ).json()["items"]
        }
        all_ids = {
            row["id"]
            for row in (
                await http.get(
                    "/api/opportunities/browse",
                    params={"limit": 120, "source_status": "all"},
                )
            ).json()["items"]
        }

    assert str(opportunity.id) not in default_ids
    assert str(opportunity.id) in stale_ids
    assert str(opportunity.id) in all_ids
