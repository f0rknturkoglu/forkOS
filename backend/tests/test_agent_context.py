import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity, Event, Link
from app.db import SessionLocal
from app.integrations.agent.context import (
    get_briefing_context,
    get_entity_context,
    get_project_context,
    get_recent_activity_context,
    search_operational_context,
)
from app.modules.opportunity.models import Application, Opportunity
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

    # 4. Create a Link from todo to project (canonical: todo belongs_to project)
    link = Link(
        from_id=todo_id,
        to_id=proj_id,
        relation="belongs_to",
    )
    db_session.add(link)

    # 5. Create an Event for the project with potentially sensitive payload
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

    # 5b. Create an Event for the linked todo (should be included in project timeline)
    todo_event = Event(
        entity_id=todo_id,
        entity_type="todo",
        verb="todo.created",
        payload={"title": "Write AST tests"},
    )
    db_session.add(todo_event)

    # 6. Create a legacy note entity (should be excluded from operational search)
    note_id = uuid.uuid4()
    note_entity = Entity(
        id=note_id,
        type="note",
        title="Old Legacy Meeting Note",
        search_text="frozen legacy note",
    )
    db_session.add(note_entity)

    # 7. Create a link between legacy note and project (must be excluded from related_entities in agent context)
    note_link = Link(
        from_id=note_id,
        to_id=proj_id,
        relation="notes_about",
    )
    db_session.add(note_link)

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
    note_id = str(sample_operational_data["note_id"])
    ctx = await get_entity_context(db_session, proj_id)
    assert ctx.id == proj_id
    assert ctx.type == "project"
    assert ctx.title == "RepoLens"
    # Related entities should include the todo
    related_types = [r["type"] for r in ctx.related_entities]
    assert "todo" in related_types
    # Legacy notes must strictly NOT appear in operational related_entities
    assert "note" not in related_types
    assert all(r["id"] != note_id for r in ctx.related_entities)
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
    # Recent activity must include project and linked todo events via project_service.timeline
    assert len(pkg.recent_activity) >= 2
    activity_verbs = [a["verb"] for a in pkg.recent_activity]
    assert "project.updated" in activity_verbs
    assert "todo.created" in activity_verbs


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


async def test_project_context_cold_vault_resolution(
    db_session: AsyncSession,
    tmp_path,
    monkeypatch,
):
    from app.integrations.obsidian.service import vault_index

    # 1. Create a project
    proj_id = uuid.uuid4()
    p_ent = Entity(id=proj_id, type="project", title="Cold Vault Project", search_text="")
    db_session.add(p_ent)
    proj = Project(id=proj_id, status="active")
    db_session.add(proj)
    await db_session.commit()

    # 2. Setup mock vault with project file
    v_dir = tmp_path / "ColdVault"
    v_dir.mkdir()
    (v_dir / "20 Projects").mkdir()
    note_content = f"""---
forkos_id: {proj_id}
forkos_type: project
---
# Cold Vault Project
"""
    (v_dir / "20 Projects" / "Cold.md").write_text(note_content, encoding="utf-8")

    monkeypatch.setattr(settings, "obsidian_vault_path", str(v_dir))
    monkeypatch.setattr(settings, "obsidian_vault_name", "ColdVault")

    # Reset vault_index to simulate a cold fresh process
    vault_index._last_scanned = None
    vault_index._items.clear()
    vault_index._conflicts.clear()
    vault_index._invalid_files.clear()
    assert vault_index.is_scanned is False

    # 3. Call get_project_context without calling brain_status or refresh_vault_index first
    pkg = await get_project_context(db_session, str(proj_id))
    assert pkg.knowledge["available"] is True
    assert pkg.knowledge["forkos_id"] == str(proj_id)
    assert pkg.knowledge["relative_path"] == "20 Projects/Cold.md"


async def test_get_briefing_context_deadlines(db_session: AsyncSession):
    todo_id = uuid.uuid4()
    todo_ent = Entity(id=todo_id, type="todo", title="Fix parser crash", search_text="")
    db_session.add(todo_ent)
    due = datetime.now(UTC) + timedelta(days=2)
    todo = Todo(id=todo_id, status="open", priority=1, due_at=due)
    db_session.add(todo)
    await db_session.commit()

    briefing = await get_briefing_context(db_session)
    assert len(briefing.deadlines) >= 1
    found = [d for d in briefing.deadlines if d["id"] == str(todo_id)]
    assert len(found) == 1
    assert found[0]["title"] == "Fix parser crash"
    assert found[0]["entity_type"] == "todo"
    assert found[0]["due_at"] is not None


async def test_get_briefing_context_invalid_date(db_session: AsyncSession):
    with pytest.raises(ValueError, match="INVALID_DATE"):
        await get_briefing_context(db_session, day="2026-99-99")


async def test_opportunity_attention_lifecycle(db_session: AsyncSession):
    # 1. Active job application (status="applied") -> MUST appear
    job1_id = uuid.uuid4()
    db_session.add(Entity(id=job1_id, type="opportunity", title="Senior Backend Engineer", search_text=""))
    opp1 = Opportunity(id=job1_id, kind="job", organization="Acme Corp", found_at=datetime.now(UTC))
    db_session.add(opp1)
    app1 = Application(opportunity_id=job1_id, status="applied")
    db_session.add(app1)

    # 2. Active job application (status="interview") -> MUST appear
    job2_id = uuid.uuid4()
    db_session.add(Entity(id=job2_id, type="opportunity", title="Lead Systems Architect", search_text=""))
    opp2 = Opportunity(id=job2_id, kind="job", organization="Beta LLC", found_at=datetime.now(UTC))
    db_session.add(opp2)
    app2 = Application(opportunity_id=job2_id, status="interview")
    db_session.add(app2)

    # 3. Terminal job application (status="rejected") -> MUST NOT appear
    job3_id = uuid.uuid4()
    db_session.add(Entity(id=job3_id, type="opportunity", title="Junior Dev", search_text=""))
    opp3 = Opportunity(id=job3_id, kind="job", organization="Gamma Co", found_at=datetime.now(UTC))
    db_session.add(opp3)
    app3 = Application(opportunity_id=job3_id, status="rejected")
    db_session.add(app3)

    # 4. Active announcement (status="action_required") -> MUST appear
    ann1_id = uuid.uuid4()
    db_session.add(Entity(id=ann1_id, type="opportunity", title="TÜBİTAK 2219 Grant", search_text=""))
    opp4 = Opportunity(id=ann1_id, kind="grant", organization="TÜBİTAK", status="action_required", found_at=datetime.now(UTC))
    db_session.add(opp4)

    # 5. Completed announcement (status="completed") -> MUST NOT appear
    ann2_id = uuid.uuid4()
    db_session.add(Entity(id=ann2_id, type="opportunity", title="YLSY Scholarship", search_text=""))
    opp5 = Opportunity(id=ann2_id, kind="scholarship", organization="MEB", status="completed", found_at=datetime.now(UTC))
    db_session.add(opp5)

    await db_session.commit()

    briefing = await get_briefing_context(db_session)
    att_ids = [item["id"] for item in briefing.opportunity_attention]
    assert str(job1_id) in att_ids
    assert str(job2_id) in att_ids
    assert str(ann1_id) in att_ids
    assert str(job3_id) not in att_ids
    assert str(ann2_id) not in att_ids

    # Check fields of job application
    job_item = next(item for item in briefing.opportunity_attention if item["id"] == str(job1_id))
    assert job_item["title"] == "Senior Backend Engineer"
    assert job_item["status"] == "applied"
    assert job_item["organization"] == "Acme Corp"


