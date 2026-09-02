"""Milestone entity-backed olunca: deadline hatti + CRUD entity tutarliligi.

0036_milestone_entity migration'ina bagli: milestone id'leri entity id'leriyle
ayni; /api/deadlines milestone son tarihlerini gorur; title Entity.title'da
yasar; silme entity'yi de temizler.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import ASGITransport, AsyncClient

from app.db import SessionLocal
from app.main import app
from app.modules.project.models import Milestone


async def _client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _create_project(client: AsyncClient, marker: str) -> str:
    response = await client.post("/api/projects", json={"title": f"Proje {marker}"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_milestone_deadline_appears_in_api_deadlines():
    async for client in _client():
        marker = uuid.uuid4().hex[:8]
        project_id = await _create_project(client, marker)
        due = datetime.now(UTC) + timedelta(days=5)
        response = await client.post(
            f"/api/projects/{project_id}/milestones",
            json={"title": f"Milestone {marker}", "due_at": due.isoformat()},
        )
        assert response.status_code == 201, response.text
        milestone_id = response.json()["id"]

        try:
            # Entity satiri ayni id'de var (kural 1: PK -> entity.id FK).
            async with SessionLocal() as session:
                row = await session.get(Milestone, uuid.UUID(milestone_id))
                assert row is not None
                from app.core.models import Entity

                entity = await session.get(Entity, uuid.UUID(milestone_id))
                assert entity is not None
                assert entity.type == "milestone"
                assert entity.title == f"Milestone {marker}"

            # Deadline hatti: /api/deadlines milestone'u gorur.
            deadlines = (await client.get("/api/deadlines")).json()
            match = [d for d in deadlines if d["type"] == "milestone" and d["entity_id"] == milestone_id]
            assert len(match) == 1, deadlines
            assert match[0]["module"] == "project"
            assert match[0]["title"] == f"Milestone {marker}"
        finally:
            await client.delete(f"/api/milestones/{milestone_id}")
            await client.delete(f"/api/projects/{project_id}")


async def test_milestone_title_lives_in_entity_and_delete_cleans_entity():
    async for client in _client():
        marker = uuid.uuid4().hex[:8]
        project_id = await _create_project(client, marker)
        response = await client.post(
            f"/api/projects/{project_id}/milestones",
            json={"title": f"Eski {marker}"},
        )
        milestone_id = response.json()["id"]
        try:
            renamed = await client.patch(
                f"/api/milestones/{milestone_id}", json={"title": f"Yeni {marker}"}
            )
            assert renamed.status_code == 200, renamed.text
            async with SessionLocal() as session:
                from app.core.models import Entity

                entity = await session.get(Entity, uuid.UUID(milestone_id))
                assert entity is not None
                assert entity.title == f"Yeni {marker}"

            deleted = await client.delete(f"/api/milestones/{milestone_id}")
            assert deleted.status_code == 204
            async with SessionLocal() as session:
                from app.core.models import Entity

                assert await session.get(Entity, uuid.UUID(milestone_id)) is None
                assert await session.get(Milestone, uuid.UUID(milestone_id)) is None
        finally:
            await client.delete(f"/api/projects/{project_id}")


async def test_markdown_export_works_without_project_notes_column():
    """p.notes kolonu 0029'da drop edildi; export note tablosundan toplar."""
    async for client in _client():
        marker = uuid.uuid4().hex[:8]
        project_id = await _create_project(client, marker)
        try:
            response = await client.get("/api/export/markdown")
            assert response.status_code == 200, response.text
            assert f"Proje {marker}" in response.text
        finally:
            await client.delete(f"/api/projects/{project_id}")
