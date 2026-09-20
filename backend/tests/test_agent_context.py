import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, Event, Link
from app.db import SessionLocal
from app.integrations.agent.context import (
    get_briefing_context,
    get_entity_context,
    get_project_context,
    get_recent_activity_context,
    search_operational_context,
)
from app.modules.project.models import Milestone, Project
from app.modules.todo.models import Todo


@pytest.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session


@pytest.fixture
async def sample_operational_data(db_session: AsyncSession):
    # 1. Create a Project entity
    proj_id = uuid.uuid4()
    proj_entity = Entity(
        id=proj_id,
        type="project",
        title="RepoLens",
        search_text="git repository analytics tool",
    )
    db_session.add(proj_entity)

    proj = Project(
        id=proj_id,
        status="active",
        github_repo="f0rknturkoglu/repolens",
        stack=["TypeScript", "React"],
        next_action="Implement AST parsing",
    )
    db_session.add(proj)
    await db_session.flush()

    # 2. Create a Milestone under this Project
    ms_id = uuid.uuid4()
    ms_entity = Entity(id=ms_id, type="milestone", title="Alpha Release", search_text="")
    db_session.add(ms_entity)
    ms = Milestone(
        id=ms_id,
        project_id=proj_id,
        title="Alpha Release",
        due_at=datetime.now(UTC) + timedelta(days=3),
    )
    db_session.add(ms)

    # 3. Create a Todo
    todo_id = uuid.uuid4()
    todo_entity = Entity(id=todo_id, type="todo", title="Write AST tests", search_text="")
    db_session.add(todo_entity)
    todo = Todo(
        id=todo_id,
        status="open",
        priority=1,
        milestone_id=ms_id,
    )
    db_session.add(todo)

    # 4. Create a Link between project and todo
    link = Link(
        from_id=proj_id,
        to_id=todo_id,
        relation="task",
    )
    db_session.add(link)

    # 5. Create an Event with potentially sensitive payload to test sanitization
    event = Event(
        entity_id=proj_id,
        entity_type="project",
        verb="project.updated",
        payload={
            "field": "next_action",
            "github_token": "ghp_secret12345",
            "info": "Updated next action",
        },
    )
    db_session.add(event)

    # 6. Create a legacy note entity (should be excluded from operational search)
    note_id = uuid.uuid4()
    note_entity = Entity(
        id=note_id,
        type="note",
        title="Old Legacy Meeting Note",
        search_text="frozen legacy note",
    )
    db_session.add(note_entity)

    await db_session.commit()

    return {
        "proj_id": proj_id,
        "todo_id": todo_id,
        "ms_id": ms_id,
        "note_id": note_id,
    }


async def test_get_briefing_context(db_session: AsyncSession, sample_operational_data):
    briefing = await get_briefing_context(db_session)
    assert briefing.day is not None
    assert len(briefing.active_projects) >= 1
    assert any(p["id"] == str(sample_operational_data["proj_id"]) for p in briefing.active_projects)
    assert len(briefing.open_todos) >= 1
    assert any(t["id"] == str(sample_operational_data["todo_id"]) for t in briefing.open_todos)


async def test_search_operational_context_excludes_legacy_notes(db_session: AsyncSession, sample_operational_data):
    # Search for "RepoLens"
    results = await search_operational_context(db_session, "RepoLens")
    assert len(results) >= 1
    assert results[0].type == "project"
    assert results[0].title == "RepoLens"

    # Search for "Legacy Meeting" should NOT return the legacy note
    note_results = await search_operational_context(db_session, "Legacy Meeting")
    assert len(note_results) == 0


async def test_get_entity_context(db_session: AsyncSession, sample_operational_data):
    proj_id = str(sample_operational_data["proj_id"])
    ctx = await get_entity_context(db_session, proj_id)
    assert ctx.id == proj_id
    assert ctx.type == "project"
    assert ctx.title == "RepoLens"
    assert len(ctx.related_entities) >= 1
    assert len(ctx.recent_events) >= 1
    # Check that credentials in event payload were sanitized
    assert ctx.recent_events[0]["payload"]["github_token"] == "[REDACTED]"


async def test_get_entity_context_legacy_note(db_session: AsyncSession, sample_operational_data):
    note_id = str(sample_operational_data["note_id"])
    ctx = await get_entity_context(db_session, note_id)
    assert ctx.id == note_id
    assert ctx.type == "note"
    assert "frozen legacy" in ctx.details.get("status", "").lower()


async def test_get_project_context(db_session: AsyncSession, sample_operational_data):
    proj_id = str(sample_operational_data["proj_id"])
    pkg = await get_project_context(db_session, proj_id)
    assert pkg.project["id"] == proj_id
    assert pkg.project["title"] == "RepoLens"
    assert pkg.project["status"] == "active"
    assert len(pkg.milestones) == 1
    assert pkg.milestones[0]["title"] == "Alpha Release"
    assert len(pkg.todos) == 1
    assert pkg.todos[0]["title"] == "Write AST tests"
    assert len(pkg.recent_activity) >= 1


async def test_get_project_context_not_found(db_session: AsyncSession):
    random_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="PROJECT_NOT_FOUND"):
        await get_project_context(db_session, random_id)


async def test_get_recent_activity_context_sanitizes_secrets(db_session: AsyncSession, sample_operational_data):
    events = await get_recent_activity_context(db_session, limit=10)
    assert len(events) >= 1
    found = [e for e in events if e.verb == "project.updated"]
    assert len(found) >= 1
    assert found[0].payload["github_token"] == "[REDACTED]"
    assert found[0].payload["info"] == "Updated next action"
