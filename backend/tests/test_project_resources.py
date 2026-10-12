from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.models import Event, Link
from app.db import SessionLocal
from app.modules.bookmark.models import Bookmark
from app.modules.project import service
from app.modules.project.schemas import ProjectIn, ProjectResourceIn


async def test_project_resources_are_atomic_searchable_and_replayable():
    async with SessionLocal() as db:
        project = await service.create(db, ProjectIn(title="Kaynaklı proje"))
        body = ProjectResourceIn(client_uuid=uuid4(), title="Doküman", url="https://example.com/doc")
        first = await service.add_resource(db, project["id"], body)
        assert await service.add_resource(db, project["id"], body) == first
        second = await service.add_resource(db, project["id"], ProjectResourceIn(
            client_uuid=uuid4(), title="Board", url="https://example.com/board"))
        rows = await service.resources(db, project["id"])
        assert [str(row["id"]) for row in rows] == [first["id"], second["id"]]
        assert await db.scalar(select(func.count()).select_from(Bookmark)) == 2
        assert await db.scalar(select(func.count()).select_from(Link).where(Link.relation == "references")) == 2
        assert await db.scalar(select(func.count()).select_from(Event).where(Event.verb == "link.created")) == 2
        with pytest.raises(HTTPException) as conflict:
            await service.add_resource(db, project["id"], body.model_copy(update={"title": "Değişti"}))
        assert conflict.value.status_code == 409
        await db.rollback()
        assert await service.add_resource(db, uuid4(), body) is None
        assert await service.resources(db, uuid4()) is None


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///tmp/doc", "https://user:secret@example.com", "https://"])
def test_project_resource_urls_are_validated(url):
    with pytest.raises(ValidationError):
        ProjectResourceIn(client_uuid=uuid4(), title="Kaynak", url=url)
