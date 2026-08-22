# Cross-Module Integration Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the real integration breaks between Today, Todos, Planner, Calendar, Projects, milestones, Pomodoro, RSS, and Finance without changing Media behavior.

**Architecture:** Todo creation becomes the backend transaction boundary for project and milestone context. Parent and recurring-task context is inherited in `todo.service`, while project activity and timeline are derived from existing entity/link/event data. Frontend widgets share canonical TanStack Query prefixes so detail-page mutations refresh Today immediately.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL 16, Pytest, React 18, TypeScript 5.5, TanStack Query 5, Vitest, Vite.

## Global Constraints

- Do not modify Media behavior or integrate Media with Today, Review, or the heatmap.
- Do not add a table or Alembic migration.
- Use `app/core/entity.py` helpers for every entity write.
- Keep `event` append-only and call `log_event()` for every meaningful action.
- Keep milestone completion manual.
- Keep todos when a project is deleted; only cascading links are removed.
- Keep all services local-only.
- Follow TDD: add one failing regression test, observe the expected failure, then write minimal production code.

## File Map

- `backend/app/modules/todo/schemas.py`: accepts optional project context.
- `backend/app/modules/todo/service.py`: validates, inherits, writes, and copies context.
- `backend/app/modules/project/service.py`: computes activity and expands timeline sources.
- `backend/app/modules/project/router.py`: delegates milestone deletion to the service.
- `backend/app/modules/pomodoro/service.py`: records context IDs in events.
- `backend/tests/test_api.py`: real-Postgres integration regressions.
- `frontend/src/modules/projects/ProjectTodos.tsx`: sends one atomic request.
- `frontend/src/modules/projects/Milestones.tsx`: invalidates every project consumer.
- `frontend/src/modules/calendar/TodayScheduleWidget.tsx`: canonical calendar prefix.
- `frontend/src/modules/finance/RecurringWidget.tsx`: canonical recurring prefix.
- `frontend/src/modules/rss/RssPage.tsx`: refreshes bookmark statistics.

---

### Task 1: Atomic Todo Project and Milestone Context

**Files:**
- Modify: `backend/app/modules/todo/schemas.py:13-24`
- Modify: `backend/app/modules/todo/service.py:26-142`
- Modify: `backend/app/modules/todo/router.py:23-43`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: `link(session, from_id, to_id, relation)` and `Milestone.project_id`.
- Produces: `TodoIn.project_id: UUID | None` and `_resolve_context(...) -> tuple[UUID | None, UUID | None]`.

- [ ] **Step 1: Write the failing atomic-link test**

Append this test to `backend/tests/test_api.py`:

```python
async def test_todo_creation_atomically_links_project_and_milestone(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post("/api/projects", json={"title": f"Atomic {suffix}"})).json()
    milestone = (await client.post(
        f"/api/projects/{project['id']}/milestones", json={"title": "Release"}
    )).json()
    response = await client.post("/api/todos", json={
        "title": f"Ship {suffix}", "project_id": project["id"],
        "milestone_id": milestone["id"],
    })
    assert response.status_code == 201
    todo = response.json()
    assert todo["project_id"] == project["id"]
    assert todo["milestone_id"] == milestone["id"]
    linked = (await client.get(f"/api/projects/{project['id']}/todos")).json()
    assert todo["id"] in {item["id"] for item in linked}
    await client.delete(f"/api/todos/{todo['id']}")
    await client.delete(f"/api/projects/{project['id']}")
```

- [ ] **Step 2: Run the test and observe RED**

```bash
docker compose exec -T api pytest -q tests/test_api.py::test_todo_creation_atomically_links_project_and_milestone
```

Expected: FAIL because `project_id` is ignored.

- [ ] **Step 3: Write the failing mismatch rollback test**

```python
async def test_todo_rejects_cross_project_milestone_without_a_record(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    first = (await client.post("/api/projects", json={"title": f"First {suffix}"})).json()
    second = (await client.post("/api/projects", json={"title": f"Second {suffix}"})).json()
    milestone = (await client.post(
        f"/api/projects/{first['id']}/milestones", json={"title": "First only"}
    )).json()
    title = f"Rollback {suffix}"
    response = await client.post("/api/todos", json={
        "title": title, "project_id": second["id"], "milestone_id": milestone["id"],
    })
    assert response.status_code == 400
    todos = (await client.get("/api/todos", params={"limit": 500})).json()
    assert title not in {item["title"] for item in todos}
    await client.delete(f"/api/projects/{first['id']}")
    await client.delete(f"/api/projects/{second['id']}")
```

- [ ] **Step 4: Run the rollback test and observe RED**

```bash
docker compose exec -T api pytest -q tests/test_api.py::test_todo_rejects_cross_project_milestone_without_a_record
```

Expected: FAIL because the current API accepts the mismatch.

- [ ] **Step 5: Implement project context on `TodoIn`**

Add this field before `milestone_id`:

```python
project_id: uuid.UUID | None = None
```

- [ ] **Step 6: Implement `_resolve_context()` before entity creation**

Add a helper in `todo.service` that:

```python
async def _resolve_context(
    session: AsyncSession, *, parent_id: uuid.UUID | None,
    project_id: uuid.UUID | None, milestone_id: uuid.UUID | None,
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    inherited_project = None
    inherited_milestone = None
    if parent_id:
        parent = await session.get(Todo, parent_id)
        if parent is None:
            raise ValueError("ust gorev bulunamadi")
        inherited_project = (await session.execute(
            select(Link.to_id).join(Entity, Entity.id == Link.to_id).where(
                Link.from_id == parent_id, Link.relation == "belongs_to",
                Entity.type == "project",
            )
        )).scalar_one_or_none()
        inherited_milestone = parent.milestone_id
    if project_id and inherited_project and project_id != inherited_project:
        raise ValueError("alt gorev farkli projeye baglanamaz")
    if milestone_id and inherited_milestone and milestone_id != inherited_milestone:
        raise ValueError("alt gorev farkli kilometre tasina baglanamaz")
    resolved_project = project_id or inherited_project
    resolved_milestone = milestone_id or inherited_milestone
    if resolved_project:
        entity = await session.get(Entity, resolved_project)
        if entity is None or entity.type != "project":
            raise ValueError("proje bulunamadi")
    if resolved_milestone:
        from app.modules.project.models import Milestone
        milestone = await session.get(Milestone, resolved_milestone)
        if milestone is None:
            raise ValueError("kilometre tasi bulunamadi")
        if resolved_project and milestone.project_id != resolved_project:
            raise ValueError("kilometre tasi bu projeye ait degil")
        resolved_project = resolved_project or milestone.project_id
    return resolved_project, resolved_milestone
```

Call the helper before `create_entity()`. Store the resolved milestone, add one `belongs_to` link before commit, and return `_todo_out()` with `project_id`, `project_title`, `milestone_id`, and `milestone_title` context. Preserve the router's `ValueError -> 400` mapping.

- [ ] **Step 7: Run both tests and observe GREEN**

```bash
docker compose exec -T api pytest -q \
  tests/test_api.py::test_todo_creation_atomically_links_project_and_milestone \
  tests/test_api.py::test_todo_rejects_cross_project_milestone_without_a_record
```

Expected: `2 passed`.

- [ ] **Step 8: Commit Task 1**

```bash
git add backend/app/modules/todo/schemas.py backend/app/modules/todo/service.py \
  backend/app/modules/todo/router.py backend/tests/test_api.py
git commit -m "Fix atomic todo project context"
```

---

### Task 2: Parent and Recurring Todo Context Inheritance

**Files:**
- Modify: `backend/app/modules/todo/service.py:342-394`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: `_resolve_context()` and the `belongs_to` relation from Task 1.
- Produces: `_copy_project_links(session, source_id, target_id) -> list[UUID]`.

- [ ] **Step 1: Write the failing subtask test**

```python
async def test_subtask_inherits_parent_project_and_milestone(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post("/api/projects", json={"title": f"Parent {suffix}"})).json()
    milestone = (await client.post(
        f"/api/projects/{project['id']}/milestones", json={"title": "Inherited"}
    )).json()
    parent = (await client.post("/api/todos", json={
        "title": f"Parent todo {suffix}", "project_id": project["id"],
        "milestone_id": milestone["id"],
    })).json()
    child = (await client.post("/api/todos", json={
        "title": f"Child {suffix}", "parent_id": parent["id"],
    })).json()
    assert child["project_id"] == project["id"]
    assert child["milestone_id"] == milestone["id"]
    linked = (await client.get(f"/api/projects/{project['id']}/todos")).json()
    assert child["id"] in {item["id"] for item in linked}
    await client.delete(f"/api/todos/{parent['id']}")
    await client.delete(f"/api/projects/{project['id']}")


async def test_subtask_rejects_conflicting_project_context(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    first = (await client.post("/api/projects", json={"title": f"Parent {suffix}"})).json()
    second = (await client.post("/api/projects", json={"title": f"Other {suffix}"})).json()
    parent = (await client.post("/api/todos", json={
        "title": f"Parent {suffix}", "project_id": first["id"],
    })).json()
    response = await client.post("/api/todos", json={
        "title": f"Conflicting child {suffix}", "parent_id": parent["id"],
        "project_id": second["id"],
    })
    assert response.status_code == 400
    await client.delete(f"/api/todos/{parent['id']}")
    await client.delete(f"/api/projects/{first['id']}")
    await client.delete(f"/api/projects/{second['id']}")
```

- [ ] **Step 2: Run the subtask test and observe RED**

```bash
docker compose exec -T api pytest -q \
  tests/test_api.py::test_subtask_inherits_parent_project_and_milestone \
  tests/test_api.py::test_subtask_rejects_conflicting_project_context
```

Expected: both tests FAIL because inherited context is not implemented.

- [ ] **Step 3: Write the failing recurring-task test**

```python
async def test_recurring_todo_keeps_project_and_milestone(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post("/api/projects", json={"title": f"Routine {suffix}"})).json()
    milestone = (await client.post(
        f"/api/projects/{project['id']}/milestones", json={"title": "Routine target"}
    )).json()
    title = f"Recurring {suffix}"
    original = (await client.post("/api/todos", json={
        "title": title, "project_id": project["id"], "milestone_id": milestone["id"],
        "recur": "daily", "due_at": "2026-08-23T09:00:00Z",
    })).json()
    await client.post(f"/api/todos/{original['id']}/complete")
    open_todos = (await client.get("/api/todos", params={"status": "open", "limit": 500})).json()
    generated = next(item for item in open_todos if item["title"] == title)
    assert generated["project_id"] == project["id"]
    assert generated["milestone_id"] == milestone["id"]
    await client.delete(f"/api/todos/{generated['id']}")
    await client.delete(f"/api/todos/{original['id']}")
    await client.delete(f"/api/projects/{project['id']}")
```

- [ ] **Step 4: Run the recurring test and observe RED**

```bash
docker compose exec -T api pytest -q tests/test_api.py::test_recurring_todo_keeps_project_and_milestone
```

Expected: FAIL because the generated todo loses both contexts.

- [ ] **Step 5: Implement reusable link copying**

```python
async def _copy_project_links(
    session: AsyncSession, source_id: uuid.UUID, target_id: uuid.UUID
) -> list[uuid.UUID]:
    project_ids = list((await session.execute(
        select(Link.to_id).join(Entity, Entity.id == Link.to_id).where(
            Link.from_id == source_id, Link.relation == "belongs_to",
            Entity.type == "project",
        )
    )).scalars())
    for project_id in project_ids:
        await link(session, target_id, project_id, "belongs_to")
    return project_ids
```

Use resolved context for subtasks. In `_spawn_next_occurrence()`, set `milestone_id=done.milestone_id` and call `_copy_project_links()` before the event write.

- [ ] **Step 6: Run inheritance tests plus the existing productivity flow**

```bash
docker compose exec -T api pytest -q \
  tests/test_api.py::test_subtask_inherits_parent_project_and_milestone \
  tests/test_api.py::test_subtask_rejects_conflicting_project_context \
  tests/test_api.py::test_recurring_todo_keeps_project_and_milestone \
  tests/test_api.py::test_phase2_productivity_flow
```

Expected: `4 passed`.

- [ ] **Step 7: Commit Task 2**

```bash
git add backend/app/modules/todo/service.py backend/tests/test_api.py
git commit -m "Preserve project context across todo generations"
```

---

### Task 3: Project Activity, Milestone Events, and Focus Timeline

**Files:**
- Modify: `backend/app/modules/project/service.py:20-258`
- Modify: `backend/app/modules/project/router.py:49-88`
- Modify: `backend/app/modules/pomodoro/service.py:90-125,185-227`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: append-only `Event`, todo `belongs_to` links, and Pomodoro context IDs.
- Produces: derived `last_activity_at`, milestone event verbs, context-bearing Pomodoro payloads, and focus events in project timeline.

- [ ] **Step 1: Write failing project activity and milestone-event tests**

```python
async def test_project_last_activity_follows_linked_todo_updates(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post("/api/projects", json={"title": f"Active {suffix}"})).json()
    todo = (await client.post("/api/todos", json={
        "title": f"Work {suffix}", "project_id": project["id"],
    })).json()
    current = next(item for item in (await client.get("/api/projects")).json()
                   if item["id"] == project["id"])
    assert current["last_activity_at"] is not None
    before = datetime.fromisoformat(current["last_activity_at"])
    await client.patch(f"/api/todos/{todo['id']}", json={"title": f"Updated {suffix}"})
    refreshed = next(item for item in (await client.get("/api/projects")).json()
                     if item["id"] == project["id"])
    assert datetime.fromisoformat(refreshed["last_activity_at"]) > before
    await client.delete(f"/api/todos/{todo['id']}")
    await client.delete(f"/api/projects/{project['id']}")


async def test_project_timeline_records_milestone_actions(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post("/api/projects", json={"title": f"Milestone {suffix}"})).json()
    milestone = (await client.post(
        f"/api/projects/{project['id']}/milestones", json={"title": "Visible event"}
    )).json()
    await client.patch(f"/api/milestones/{milestone['id']}", json={"completed": True})
    await client.delete(f"/api/milestones/{milestone['id']}")
    timeline = (await client.get(f"/api/projects/{project['id']}/timeline")).json()
    verbs = {item["verb"] for item in timeline}
    assert {
        "project.milestone_added", "project.milestone_updated", "project.milestone_deleted",
    } <= verbs
    await client.delete(f"/api/projects/{project['id']}")
```

Also add `datetime` to the existing datetime import in the test file.

- [ ] **Step 2: Run the test and observe RED**

```bash
docker compose exec -T api pytest -q \
  tests/test_api.py::test_project_last_activity_follows_linked_todo_updates \
  tests/test_api.py::test_project_timeline_records_milestone_actions
```

Expected: both tests FAIL for their named missing behaviors.

- [ ] **Step 3: Write a failing contextual Pomodoro test**

```python
async def test_project_timeline_includes_pomodoro_for_linked_todo(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post("/api/projects", json={"title": f"Focus {suffix}"})).json()
    todo = (await client.post("/api/todos", json={
        "title": f"Focus todo {suffix}", "project_id": project["id"],
    })).json()
    pomo = (await client.post("/api/pomodoro/start", json={
        "planned_min": 1, "context_entity_id": todo["id"],
    })).json()
    await client.post(f"/api/pomodoro/{pomo['id']}/stop", json={"interrupted": False})
    timeline = (await client.get(f"/api/projects/{project['id']}/timeline")).json()
    focus = [item for item in timeline if item["verb"] == "pomodoro.completed"]
    assert focus
    assert focus[0]["payload"]["context_entity_id"] == todo["id"]
    await client.delete(f"/api/pomodoro/{pomo['id']}")
    await client.delete(f"/api/todos/{todo['id']}")
    await client.delete(f"/api/projects/{project['id']}")
```

- [ ] **Step 4: Run the focus test and observe RED**

```bash
docker compose exec -T api pytest -q tests/test_api.py::test_project_timeline_includes_pomodoro_for_linked_todo
```

Expected: FAIL because Pomodoro events lack context IDs and the timeline ignores them.

- [ ] **Step 5: Implement project activity as a grouped query**

```python
async def _todo_activity_by_project(
    session: AsyncSession, project_ids: list[uuid.UUID]
) -> dict[uuid.UUID, datetime]:
    rows = (await session.execute(
        select(Link.to_id, func.max(Entity.updated_at))
        .join(Entity, Entity.id == Link.from_id)
        .where(Link.to_id.in_(project_ids), Link.relation == "belongs_to",
               Entity.type == "todo")
        .group_by(Link.to_id)
    )).all()
    return {project_id: changed_at for project_id, changed_at in rows}
```

Change `project_out()` to accept the project entity timestamp and optional todo timestamp. Return the maximum of entity time, stored GitHub time, and todo time. `list_projects()` obtains all todo maxima once and passes them into each serializer.

- [ ] **Step 6: Log milestone events and move deletion into the service**

Use `project.milestone_added`, `project.milestone_updated`, and `project.milestone_deleted`. Every event uses `entity_id=item.project_id`, `entity_type="project"`, and a payload containing `milestone_id`, title, and changed fields. Implement:

```python
async def delete_milestone(session: AsyncSession, milestone_id: uuid.UUID) -> bool:
    item = await session.get(Milestone, milestone_id)
    if item is None:
        return False
    await log_event(session, verb="project.milestone_deleted",
                    entity_id=item.project_id, entity_type="project",
                    payload={"milestone_id": str(item.id), "title": item.title})
    await session.delete(item)
    await session.commit()
    return True
```

Delegate the router endpoint to this service function and retain its `404` response.

- [ ] **Step 7: Add context IDs to Pomodoro events and timeline conditions**

Include these fields in completed, interrupted, and manual event payloads:

```python
"context_entity_id": str(pomo.context_entity_id) if pomo.context_entity_id else None,
"context_type": context.type if context else None,
```

In project timeline, include Pomodoro events whose JSON `context_entity_id` is one of the project's linked todo IDs. Add `cast` and `Text` to the SQLAlchemy imports and use this condition:

```python
todo_ids_text = select(cast(Link.from_id, Text)).where(
    Link.to_id == project_id, Link.relation == "belongs_to"
)
conditions.append(
    Event.verb.in_(("pomodoro.completed", "pomodoro.interrupted"))
    & Event.payload["context_entity_id"].astext.in_(todo_ids_text)
)
```

Keep `Event.entity_id` attached to the Pomodoro entity.

- [ ] **Step 8: Run Task 3 tests and observe GREEN**

```bash
docker compose exec -T api pytest -q \
  tests/test_api.py::test_project_last_activity_follows_linked_todo_updates \
  tests/test_api.py::test_project_timeline_records_milestone_actions \
  tests/test_api.py::test_project_timeline_includes_pomodoro_for_linked_todo
```

Expected: `3 passed`.

- [ ] **Step 9: Commit Task 3**

```bash
git add backend/app/modules/project/service.py backend/app/modules/project/router.py \
  backend/app/modules/pomodoro/service.py backend/tests/test_api.py
git commit -m "Integrate project activity and focus timeline"
```

---

### Task 4: Frontend Atomic Requests and Shared Query Prefixes

**Files:**
- Modify: `frontend/src/modules/projects/ProjectTodos.tsx:14-38`
- Modify: `frontend/src/modules/projects/Milestones.tsx:10-28`
- Modify: `frontend/src/modules/calendar/TodayScheduleWidget.tsx:6-9`
- Modify: `frontend/src/modules/finance/RecurringWidget.tsx:1-5`
- Modify: `frontend/src/modules/rss/RssPage.tsx:451-459`
- Create: `frontend/src/modules/projects/ProjectTodos.test.tsx`
- Create: `frontend/src/modules/today/integrationKeys.test.ts`

**Interfaces:**
- Consumes: `TodoIn.project_id` from Task 1 and prefix invalidation in `useInvalidate()`.
- Produces: `createProjectTodo`, `PROJECT_REFRESH_KEYS`, `TODAY_CALENDAR_KEY`, `RECURRING_WIDGET_KEY`, and `RSS_SAVE_REFRESH_KEYS`.

- [ ] **Step 1: Write the failing atomic request test**

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/core/api";
import { createProjectTodo } from "./ProjectTodos";

vi.mock("@/core/api", () => ({ api: { post: vi.fn() } }));

describe("project todo integration", () => {
  beforeEach(() => vi.clearAllMocks());
  it("creates and links a project todo in one request", async () => {
    vi.mocked(api.post).mockResolvedValue({ id: "todo-1" });
    await createProjectTodo("project-1", "Görevi bitir", "milestone-1");
    expect(api.post).toHaveBeenCalledTimes(1);
    expect(api.post).toHaveBeenCalledWith("/todos", {
      title: "Görevi bitir", project_id: "project-1", milestone_id: "milestone-1",
    });
  });
});
```

- [ ] **Step 2: Run the test and observe RED**

```bash
cd frontend && npm test -- src/modules/projects/ProjectTodos.test.tsx
```

Expected: FAIL because `createProjectTodo` is absent.

- [ ] **Step 3: Implement one-request creation and shared project refresh keys**

```tsx
export const PROJECT_REFRESH_KEYS = [
  "projects", "project-todos", "project-timeline", "todos", "activity",
] as const;

export function createProjectTodo(projectId: string, title: string, milestoneId: string) {
  return api.post<Todo>("/todos", {
    title: title.trim(), project_id: projectId, milestone_id: milestoneId || undefined,
  });
}
```

Use the helper in the mutation and remove the second project-link request. Refresh with `invalidate(...PROJECT_REFRESH_KEYS)` after project todo and milestone writes.

- [ ] **Step 4: Write failing canonical-key tests**

```ts
import { describe, expect, it } from "vitest";
import { TODAY_CALENDAR_KEY } from "@/modules/calendar/TodayScheduleWidget";
import { RECURRING_WIDGET_KEY } from "@/modules/finance/RecurringWidget";
import { RSS_SAVE_REFRESH_KEYS } from "@/modules/rss/RssPage";
import { PROJECT_REFRESH_KEYS } from "@/modules/projects/ProjectTodos";

describe("cross-page query integration", () => {
  it("uses detail-page prefixes in Today widgets", () => {
    expect(TODAY_CALENDAR_KEY[0]).toBe("calendar-events");
    expect(RECURRING_WIDGET_KEY[0]).toBe("recurring");
  });
  it("refreshes every linked consumer", () => {
    expect(RSS_SAVE_REFRESH_KEYS).toContain("bookmark-stats");
    expect(PROJECT_REFRESH_KEYS).toContain("project-timeline");
    expect(PROJECT_REFRESH_KEYS).toContain("projects");
  });
});
```

- [ ] **Step 5: Run key tests and observe RED**

```bash
cd frontend && npm test -- src/modules/today/integrationKeys.test.ts
```

Expected: FAIL because the constants and canonical prefixes are absent.

- [ ] **Step 6: Implement exact canonical constants**

```ts
export const TODAY_CALENDAR_KEY = ["calendar-events", "today"] as const;
export const RECURRING_WIDGET_KEY = ["recurring", "widget"] as const;
export const RSS_SAVE_REFRESH_KEYS = [
  "rss-item", "items", "feeds", "rss-stats", "bookmarks", "bookmark-stats", "activity",
] as const;
```

Use these constants in the corresponding `queryKey` and `invalidate` calls. Keep UI output and API endpoints unchanged.

- [ ] **Step 7: Run all new frontend tests and observe GREEN**

```bash
cd frontend && npm test -- \
  src/modules/projects/ProjectTodos.test.tsx \
  src/modules/today/integrationKeys.test.ts
```

Expected: both test files pass.

- [ ] **Step 8: Commit Task 4**

```bash
git add frontend/src/modules/projects/ProjectTodos.tsx \
  frontend/src/modules/projects/Milestones.tsx \
  frontend/src/modules/calendar/TodayScheduleWidget.tsx \
  frontend/src/modules/finance/RecurringWidget.tsx frontend/src/modules/rss/RssPage.tsx \
  frontend/src/modules/projects/ProjectTodos.test.tsx \
  frontend/src/modules/today/integrationKeys.test.ts
git commit -m "Synchronize Today and project consumers"
```

---

### Task 5: Full Regression Verification

**Files:**
- Verify: all files changed in Tasks 1-4
- Verify: `docs/superpowers/specs/2026-08-23-cross-module-integration-repair-design.md`

**Interfaces:**
- Consumes: all Task 1-4 deliverables.
- Produces: fresh test, build, lint, migration, and whitespace evidence.

- [ ] **Step 1: Run the complete backend suite**

```bash
docker compose exec -T api pytest -q
```

Expected: all backend tests pass with zero failures.

- [ ] **Step 2: Run Ruff on every modified backend file**

```bash
docker compose exec -T api ruff check \
  app/modules/todo/schemas.py app/modules/todo/service.py app/modules/todo/router.py \
  app/modules/project/service.py app/modules/project/router.py \
  app/modules/pomodoro/service.py tests/test_api.py
```

Expected: `All checks passed!`

- [ ] **Step 3: Record the repository-wide Ruff baseline without changing Media**

```bash
docker compose exec -T api ruff check app tests
```

Expected baseline: ten existing findings in Media/RSS/System files. Confirm Step 2 reports no finding in an integration file; do not edit Media for this unrelated baseline.

- [ ] **Step 4: Run frontend tests and build**

```bash
cd frontend && npm test && npm run build
```

Expected: tests and TypeScript/Vite exit with status `0`; the existing chunk-size warning is allowed.

- [ ] **Step 5: Verify migration head and whitespace**

```bash
docker compose exec -T api alembic current
docker compose exec -T api alembic heads
git -c core.whitespace=cr-at-eol diff --check
```

Expected: both Alembic commands report `0024_todo_milestone (head)` and diff check prints nothing.

- [ ] **Step 6: Review final scope**

```bash
git diff --stat HEAD~4..HEAD
git status --short
```

Expected: only planned integration/test files and this plan are present; no Media behavior file is modified.
