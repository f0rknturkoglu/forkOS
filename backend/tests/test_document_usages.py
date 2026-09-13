from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.entity import create_entity
from app.db import SessionLocal
from app.main import app
from app.modules.document.models import Document
from app.modules.opportunity.models import (
    Application,
    Opportunity,
    OpportunityRequirement,
)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _seed_document(session, title: str):
    entity = await create_entity(session, type="document", title=title, search_text="cv")
    session.add(
        Document(
            id=entity.id,
            drive_file_id=f"seed:{entity.id}",
            folder_id="seed",
            category="cv",
            synced_at=datetime.now(UTC),
        )
    )
    await session.flush()
    return entity.id


async def _seed_opportunity(
    session, title: str, *, found_at: datetime, status: str = "discovered", kind: str = "job"
):
    entity = await create_entity(session, type="opportunity", title=title, search_text=title)
    opp = Opportunity(id=entity.id, kind=kind, status=status, found_at=found_at)
    session.add(opp)
    await session.flush()
    return opp


async def test_document_usages_cv_requirement_and_skips_trashed(client: AsyncClient):
    async with SessionLocal() as session:
        doc_cv = await _seed_document(session, "CV 2026")
        doc_req = await _seed_document(session, "Talepname")
        doc_unused = await _seed_document(session, "Boşta kalan belge")

        opp_cv = await _seed_opportunity(
            session,
            "Kıdemli Frontend",
            kind="job",
            # 'applied' artik application.status'tadir; kesif durumu shortlisted.
            status="shortlisted",
            found_at=datetime(2026, 8, 10, tzinfo=UTC),
        )
        opp_req = await _seed_opportunity(
            session,
            "Stajyer Veri",
            kind="internship",
            status="discovered",
            found_at=datetime(2026, 8, 1, tzinfo=UTC),
        )
        opp_trashed = await _seed_opportunity(
            session,
            "Çöpe atılmış ilan",
            kind="job",
            status="discovered",
            found_at=datetime(2026, 8, 20, tzinfo=UTC),
        )
        # CV bağı (1:1 application) + gereksinim belgesi bağı (requirement).
        session.add(Application(opportunity_id=opp_cv.id, cv_document_id=doc_cv))
        session.add(
            OpportunityRequirement(
                id=uuid.uuid4(),
                opportunity_id=opp_req.id,
                name="Talepname",
                document_entity_id=doc_req,
                position=0,
            )
        )
        # Çöpe atılmış fırsat da CV bağı taşıyor — usages'a girmemeli.
        session.add(Application(opportunity_id=opp_trashed.id, cv_document_id=doc_cv))
        opp_trashed.trashed_at = datetime.now(UTC)
        await session.commit()

    response = await client.get("/api/documents/usages")
    assert response.status_code == 200
    body = response.json()
    rows = {row["document_id"]: row["usages"] for row in body}

    assert str(doc_cv) in rows
    assert str(doc_req) in rows
    # Bağı olmayan belge hiçbir satırda yer almaz (boş kullanım).
    assert str(doc_unused) not in rows

    cv_usages = rows[str(doc_cv)]
    assert {(u["opportunity_id"], u["relation"]) for u in cv_usages} == {(str(opp_cv.id), "cv")}
    assert cv_usages[0]["title"] == "Kıdemli Frontend"
    assert cv_usages[0]["status"] == "applied"
    assert cv_usages[0]["kind"] == "job"

    req_usages = rows[str(doc_req)]
    assert [(u["opportunity_id"], u["relation"]) for u in req_usages] == [
        (str(opp_req.id), "requirement")
    ]

    # Çöpe atılmış fırsat hiçbir belgenin usages'ında görünmez.
    all_usage_opps = [u["opportunity_id"] for row in body for u in row["usages"]]
    assert str(opp_trashed.id) not in all_usage_opps


async def test_document_usages_empty_when_no_links(client: AsyncClient):
    async with SessionLocal() as session:
        await _seed_document(session, "Bağsız belge")
        opp = await _seed_opportunity(
            session,
            "Bağsız ilan",
            found_at=datetime(2026, 8, 5, tzinfo=UTC),
        )
        # Fırsat duruyor ama ne application (cv) ne requirement bağı kurulmuş.
        assert opp.id is not None
        await session.commit()

    response = await client.get("/api/documents/usages")
    assert response.status_code == 200
    assert response.json() == []
