# forkOS × Hermes — H1: Safe Actions & Approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build a human-approved, non-destructive semantic write surface (11 H1 mutation tools + 8 H0 read tools = 19 public MCP tools) over existing forkOS operational state and f0rknbrain durable knowledge via Streamable HTTP MCP.

**Architecture:**
Hermes operates as an untrusted client requesting actions over Streamable HTTP MCP (`/mcp` on `127.0.0.1:8000`).
All mutations are routed through canonical domain services (`todo.service`, `project.service`, `opportunity.lifecycle/application`, `bookmark.service`, `obsidian.service`) without raw SQL, generic endpoints, or legacy Notes mutation.
Mutations require optimistic concurrency guards (`expected_updated_at`, `expected_status`, `VaultStaleWriteError`) to prevent applying stale decisions, and return structured, bounded `ActionReceipt` payloads.

**Architecture Diagram:**

```mermaid
flowchart TD
    subgraph Client ["Client (Hermes)"]
        H[Hermes Agent] --> |MCP Tool Call| HTTP["Streamable HTTP (/mcp)"]
        UserAppr["Human Approval UI<br/>(trust: untrusted)"] -.->|Prompts user before tool call| H
    end

    subgraph AgentPackage ["backend/app/integrations/agent/"]
        HTTP --> Tools["tools.py (19 MCP Tools)"]
        Tools --> |8 Reads| Ctx["context.py / knowledge.py (H0)"]
        Tools --> |11 Writes| Actions["actions.py (H1 Semantic Adapters)"]
        Actions --> Precond["Optimistic Preconditions<br/>(expected_status / expected_updated_at / mtime)"]
    end

    subgraph DomainServices ["Canonical Domain Services (Zero Re-implementation)"]
        Precond --> TodoSvc["modules/todo/service.py"]
        Precond --> ProjSvc["modules/project/service.py"]
        Precond --> OppSvc["modules/opportunity/application.py"]
        Precond --> BmSvc["modules/bookmark/service.py"]
        Precond --> ObsSvc["integrations/obsidian/service.py"]
    end

    subgraph Storage ["Durable Storage & Events"]
        TodoSvc --> DB[(PostgreSQL 16)]
        ProjSvc --> DB
        OppSvc --> DB
        BmSvc --> DB
        TodoSvc --> Ev[Domain Events (event table)]
        ProjSvc --> Ev
        OppSvc --> Ev
        BmSvc --> Ev
        ObsSvc --> Vault[f0rknbrain Vault (Filesystem)]
    end
```

**Tech Stack:**
- Python 3.12+ / FastAPI / SQLAlchemy 2.0 (asyncpg) / Pydantic v2
- Model Context Protocol Python SDK 2.x (`MCPServer`, `streamable_http`)
- PostgreSQL 16 (local-only, 127.0.0.1:15433 for testing)
- Obsidian Vault local filesystem storage

**Spec:** User specification for `forkOS × Hermes — H1 Safe Actions & Approval`.

---

## Global Constraints

- **Local-Only:** MCP binds exclusively to localhost (`127.0.0.1`). Zero external network requests (no GitHub API, LinkedIn, RSS refresh, bookmark web fetch/enrichment).
- **Public Surface:** Exactly 19 public MCP tools (8 H0 read tools + 11 H1 write tools).
- **Tool Annotations:** All 11 H1 write tools have `readOnlyHint = False`, `destructiveHint = False`. `idempotentHint` must be accurately set per tool.
- **Zero Deletion:** Absolutely no deletion tools (`delete_todo`, `delete_project`, `delete_bookmark`, `delete_note` are forbidden).
- **Zero Generic Mutation:** No `call_api`, `execute_sql`, `run_command`, `write_file`.
- **Domain Service Reuse:** All writes delegate to canonical domain services (`todo.service`, `project.service`, `opportunity.application`, `bookmark.service`, `obsidian.service`).
- **No Legacy Notes Mutation:** Never write to `note`, `note_folder`, `note_attachment`. Knowledge writes go directly to Obsidian Vault.
- **Stale-State Protection:** Fail closed on mismatched `expected_updated_at`, `expected_status`, or `expected_mtime` with model-readable errors (`STALE_ACTION`, `VAULT_STALE`).
- **Bounded Payloads:** All write inputs have strict Pydantic length/byte bounds. Action receipts contain bounded before/after summaries, never raw dumps or secrets.
- **Client-Side Approval:** forkOS does not build a server-side approval queue. Approval lives in the client (Hermes `trust: untrusted`).
- **No Phase 4 / No LLM / No H2:** No table drops, no local LLM, no hot memory, no embeddings/RAG.

---

### Task 1: H0 Debt Resolution (Vault Error Visibility & Immutability Documentation)

**Files:**
- Modify: `backend/app/integrations/agent/models.py:165-180`
- Modify: `backend/app/integrations/agent/context.py:370-385,503-520`
- Modify: `docs/hermes/h0-brain-interface.md:85-95`
- Test: `backend/tests/test_agent_context.py`

**Interfaces:**
- Consumes: `app.integrations.obsidian.service.resolve_managed_item`, `vault_index`, `VaultConflictError`
- Produces: `KnowledgePointer` in `models.py` with `state: Literal["available", "missing", "unavailable", "conflict"]`, `available: bool`, `forkos_id: str | None`, `relative_path: str | None`, `title: str | None`, `diagnostic: str | None`.

- [x] **Step 1: Write failing tests for Vault resolution states in context**

```python
# In backend/tests/test_agent_context.py
async def test_project_context_knowledge_states(db_session: AsyncSession, monkeypatch):
    proj_id = uuid.uuid4()
    ent = Entity(id=proj_id, type="project", title="State Project", search_text="")
    db_session.add(ent)
    proj = Project(id=proj_id, status="active")
    db_session.add(proj)
    await db_session.commit()

    # 1. Missing managed note
    ctx = await get_project_context(db_session, str(proj_id))
    assert ctx.knowledge["state"] == "missing"
    assert ctx.knowledge["available"] is False

    # 2. Vault conflict
    monkeypatch.setattr(
        "app.integrations.agent.context.resolve_managed_item",
        lambda *a, **k: (_ for _ in ()).throw(VaultConflictError(str(proj_id), ["a.md", "b.md"]))
    )
    ctx = await get_project_context(db_session, str(proj_id))
    assert ctx.knowledge["state"] == "conflict"
    assert ctx.knowledge["available"] is False
    assert "conflict" in ctx.knowledge["diagnostic"].lower()
```

- [x] **Step 2: Run test to verify it fails**

Run: `DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" backend/.venv/bin/pytest backend/tests/test_agent_context.py -k test_project_context_knowledge_states -v`
Expected: FAIL (`KeyError: 'state'`)

- [x] **Step 3: Update `models.py`, `context.py`, and `docs/hermes/h0-brain-interface.md`**

In `backend/app/integrations/agent/models.py`:
Define `KnowledgePointer` schema:
```python
class KnowledgePointer(BaseModel):
    state: Literal["available", "missing", "unavailable", "conflict"] = Field(
        ..., description="Granular availability state of the linked Obsidian knowledge note."
    )
    available: bool = Field(..., description="True if state == 'available'.")
    forkos_id: str | None = Field(default=None, description="Managed forkos_id.")
    relative_path: str | None = Field(default=None, description="Vault-relative path.")
    title: str | None = Field(default=None, description="Note title.")
    diagnostic: str | None = Field(default=None, description="Diagnostic message when unavailable or in conflict.")
```
In `backend/app/integrations/agent/context.py`:
Implement helper `_resolve_knowledge_pointer(forkos_id: uuid.UUID) -> dict[str, Any]` catching `VaultConflictError` -> `"conflict"`, `RuntimeError`/`PermissionError`/`FileNotFoundError` -> `"unavailable"`, `None` -> `"missing"`, found -> `"available"`.
In `docs/hermes/h0-brain-interface.md`:
Correct wording from "veritabanı içeriği baytı baytına %100 korunur" to "deterministic content fingerprint over selected canonical state fields across critical tables".

- [x] **Step 4: Run test to verify it passes**

Run: `DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" backend/.venv/bin/pytest backend/tests/test_agent_context.py -k test_project_context_knowledge_states -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/integrations/agent/models.py backend/app/integrations/agent/context.py docs/hermes/h0-brain-interface.md backend/tests/test_agent_context.py
git commit -m "fix(agent): resolve H0 debt with typed vault knowledge pointer and accurate immutability wording"
```

---

### Task 2: H1 Write Models & Action Receipt Schema

**Files:**
- Create: `backend/app/integrations/agent/write_models.py`
- Create: `backend/tests/test_agent_write_models.py`

**Interfaces:**
- Consumes: Pydantic v2 `BaseModel`, `Field`
- Produces: `ActionReceipt`, `TodoCreateIn`, `TodoUpdateIn`, `TodoPlanIn`, `ProjectUpdateIn`, `OpportunityTransitionIn`, `ApplicationTransitionIn`, `BookmarkCaptureIn`, `BookmarkUpdateIn`, `BrainCaptureIn`, `BrainSaveToEntityIn`

- [x] **Step 1: Write failing tests for write models and receipt validation**

```python
# In backend/tests/test_agent_write_models.py
import pytest
from pydantic import ValidationError
from app.integrations.agent.write_models import (
    ActionReceipt,
    TodoCreateIn,
    ProjectUpdateIn,
    BrainCaptureIn,
)

def test_todo_create_bounds():
    # Valid
    m = TodoCreateIn(title="Buy milk", priority=1)
    assert m.title == "Buy milk"

    # Title empty
    with pytest.raises(ValidationError):
        TodoCreateIn(title="   ")

    # Title too long (> 300 chars)
    with pytest.raises(ValidationError):
        TodoCreateIn(title="x" * 301)

def test_project_update_disallows_rename():
    # Only next_action allowed
    m = ProjectUpdateIn(next_action="Ship H1")
    assert m.next_action == "Ship H1"
    # Title not in schema
    with pytest.raises(ValidationError):
        ProjectUpdateIn(title="Renamed Project")

def test_action_receipt_structure():
    r = ActionReceipt(
        request_id="req-123",
        tool="forkos_todo_create",
        status="executed",
        target_type="todo",
        target_id="11111111-2222-3333-4444-555555555555",
        summary="Created todo: Buy milk",
        changed_fields=["status", "priority"],
        before={},
        after={"title": "Buy milk", "priority": 1},
        warnings=[]
    )
    assert r.status == "executed"
```

- [x] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_agent_write_models.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.integrations.agent.write_models'`)

- [x] **Step 3: Implement `write_models.py`**

In `backend/app/integrations/agent/write_models.py`:
- `ActionReceipt`:
  - `request_id: str | None`
  - `tool: str`
  - `status: Literal["executed", "noop"]`
  - `target_type: str`
  - `target_id: str`
  - `summary: str`
  - `changed_fields: list[str]`
  - `before: dict[str, Any]`
  - `after: dict[str, Any]`
  - `warnings: list[str]`
- `TodoCreateIn`: `title` (1..300 chars, stripped), `description` (max 5000 chars), `priority` (1..4), `due_at`, `reminder_at`, `plan_day`, `project_id`, `milestone_id`, `parent_id`, `tags` (max 20 items), `recur` (`Literal["daily", "weekdays", "weekly", "monthly"] | None`).
- `TodoUpdateIn`: `todo_id` (UUID str), `title` (1..300 chars), `description` (max 5000 chars), `priority` (1..4), `due_at`, `reminder_at`, `tags` (max 20), `recur`, `expected_updated_at` (ISO timestamp).
- `TodoPlanIn`: `todo_id` (UUID str), `day` (YYYY-MM-DD), `start_min` (0..1439 | None), `duration_min` (5..1440 | None).
- `ProjectUpdateIn`: `project_id` (UUID str), `next_action` (max 500 chars | None), `expected_updated_at` (ISO timestamp | None).
- `OpportunityTransitionIn`: `opportunity_id` (UUID str), `expected_status` (str), `to_status` (str), `note` (max 1000 chars | None).
- `ApplicationTransitionIn`: `opportunity_id` (UUID str), `expected_status` (str | None), `to_status` (str), `note` (max 1000 chars | None), `rejection_reason` (str | None).
- `BookmarkCaptureIn`: `url` (valid http/https, max 2048 chars), `title` (max 300 chars | None), `collection` (Literal["inbox", "bookmarks", "archive"]), `tags` (max 20), `note` (max 5000 chars | None).
- `BookmarkUpdateIn`: `bookmark_id` (UUID str), `collection` (str | None), `favorite` (bool | None), `read_status` (Literal["unread", "reading", "read"] | None), `tags` (max 20 | None), `expected_updated_at` (str | None).
- `BrainCaptureIn`: `body` (1..40000 chars), `title` (max 300 chars | None), `relate_to` (UUID str | None), `tags` (max 20 | None).
- `BrainSaveToEntityIn`: `forkos_id` (UUID str), `text` (1..20000 chars), `heading` (max 200 chars | None).

- [x] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_agent_write_models.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/integrations/agent/write_models.py backend/tests/test_agent_write_models.py
git commit -m "feat(agent): define H1 write models and ActionReceipt schemas"
```

---

### Task 3: Todo and Project Semantic Action Adapters

**Files:**
- Create: `backend/app/integrations/agent/actions.py`
- Create: `backend/tests/test_agent_actions_todo_project.py`

**Interfaces:**
- Consumes: `app.modules.todo.service` (`create`, `update`, `complete`, `schedule`, `update_slot`), `app.modules.project.service` (`patch`), `app.integrations.agent.write_models`
- Produces: `create_todo`, `update_todo`, `complete_todo`, `plan_todo`, `update_project` returning `ActionReceipt`.

- [x] **Step 1: Write failing tests for Todo & Project semantic actions**

```python
# In backend/tests/test_agent_actions_todo_project.py
import pytest
import uuid
from datetime import UTC, datetime
from app.integrations.agent.actions import create_todo, update_todo, complete_todo, plan_todo, update_project
from app.integrations.agent.write_models import TodoCreateIn, TodoUpdateIn, TodoPlanIn, ProjectUpdateIn
from app.modules.todo.models import Todo
from app.modules.project.models import Project
from app.core.models import Entity

pytestmark = pytest.mark.anyio

async def test_create_and_complete_todo(db_session):
    # 1. Create todo
    rec = await create_todo(db_session, TodoCreateIn(title="Test Task", priority=1), request_id="r1")
    assert rec.status == "executed"
    todo_id = rec.target_id

    # 2. Complete todo
    c_rec = await complete_todo(db_session, todo_id, request_id="r2")
    assert c_rec.status == "executed"
    assert c_rec.after["status"] == "done"

    # 3. Complete already done is noop
    c_rec2 = await complete_todo(db_session, todo_id, request_id="r3")
    assert c_rec2.status == "noop"
    assert c_rec2.summary == "Todo already completed"

async def test_todo_plan_ambiguity(db_session):
    rec = await create_todo(db_session, TodoCreateIn(title="Plan Task"), request_id="r1")
    # First plan succeeds (0 future slots -> creates 1)
    p1 = await plan_todo(db_session, TodoPlanIn(todo_id=rec.target_id, day="2026-09-25"), request_id="r2")
    assert p1.status == "executed"

async def test_project_update_stale_guard(db_session):
    p_id = uuid.uuid4()
    ent = Entity(id=p_id, type="project", title="Proj", search_text="")
    db_session.add(ent)
    db_session.add(Project(id=p_id, status="active"))
    await db_session.commit()
    await db_session.refresh(ent)

    # Wrong expected_updated_at fails
    with pytest.raises(ValueError, match="STALE_ACTION"):
        await update_project(
            db_session,
            ProjectUpdateIn(project_id=str(p_id), next_action="Ship", expected_updated_at="2020-01-01T00:00:00Z"),
            request_id="r1"
        )
```

- [x] **Step 2: Run test to verify it fails**

Run: `DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" backend/.venv/bin/pytest backend/tests/test_agent_actions_todo_project.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.integrations.agent.actions'`)

- [x] **Step 3: Implement `actions.py` for Todo and Project**

Implement:
- `create_todo`: map `TodoCreateIn` to `TodoIn`, call `todo_service.create(session, todo_in)`. Build `ActionReceipt`.
- `update_todo`: verify `expected_updated_at` against `Entity.updated_at` (raise `ValueError("STALE_ACTION: ...")`). Build `TodoUpdate`, call `todo_service.update(session, todo_id, todo_update)`. Build `ActionReceipt`.
- `complete_todo`: load Todo. If `todo.status == "done"`, return `ActionReceipt(status="noop", ...)`. Call `todo_service.complete(session, todo_id)`. Build `ActionReceipt`.
- `plan_todo`: query future slots `PlanSlot.entity_id == todo_id, PlanSlot.day >= local_today()`.
  - if count == 0: call `todo_service.schedule(session, PlanSlotIn(entity_id=todo_id, day=day, start_min=start_min, duration_min=duration_min))`.
  - if count == 1: call `todo_service.update_slot(session, slot.id, PlanSlotUpdate(day=day, start_min=start_min, duration_min=duration_min))`.
  - if count > 1: raise `ValueError("AMBIGUOUS_PLAN: Multiple future slots exist for this todo. Candidates: ...")`.
- `update_project`: verify `expected_updated_at` against `Entity.updated_at`. Call `project_service.patch(session, project_id, ProjectPatch(next_action=next_action))`. Build `ActionReceipt`.

- [x] **Step 4: Run test to verify it passes**

Run: `DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" backend/.venv/bin/pytest backend/tests/test_agent_actions_todo_project.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/integrations/agent/actions.py backend/tests/test_agent_actions_todo_project.py
git commit -m "feat(agent): implement todo and project semantic mutation adapters"
```

---

### Task 4: Opportunity and Application Lifecycle Action Adapters

**Files:**
- Modify: `backend/app/integrations/agent/actions.py`
- Create: `backend/tests/test_agent_actions_opportunity.py`

**Interfaces:**
- Consumes: `app.modules.opportunity.application.transition_status`, `transition_application`, `apply`, `app.modules.opportunity.lifecycle`
- Produces: `transition_opportunity`, `transition_application`

- [x] **Step 1: Write failing tests for Opportunity and Application transitions**

```python
# In backend/tests/test_agent_actions_opportunity.py
import pytest
import uuid
from app.integrations.agent.actions import transition_opportunity, transition_application
from app.integrations.agent.write_models import OpportunityTransitionIn, ApplicationTransitionIn
from app.modules.opportunity.models import Opportunity, Application
from app.core.models import Entity

pytestmark = pytest.mark.anyio

async def test_opportunity_discovery_transition(db_session):
    opp_id = uuid.uuid4()
    ent = Entity(id=opp_id, type="opportunity", title="Software Eng", search_text="")
    db_session.add(ent)
    opp = Opportunity(id=opp_id, kind="job", status="discovered", title="Software Eng")
    db_session.add(opp)
    await db_session.commit()

    # Stale expected_status fails
    with pytest.raises(ValueError, match="STALE_ACTION"):
        await transition_opportunity(
            db_session,
            OpportunityTransitionIn(opportunity_id=str(opp_id), expected_status="shortlisted", to_status="dismissed"),
            request_id="r1"
        )

    # Valid transition: discovered -> shortlisted
    rec = await transition_opportunity(
        db_session,
        OpportunityTransitionIn(opportunity_id=str(opp_id), expected_status="discovered", to_status="shortlisted"),
        request_id="r2"
    )
    assert rec.status == "executed"
    assert rec.after["status"] == "shortlisted"

async def test_application_transition_first_apply(db_session):
    opp_id = uuid.uuid4()
    ent = Entity(id=opp_id, type="opportunity", title="Backend Lead", search_text="")
    db_session.add(ent)
    opp = Opportunity(id=opp_id, kind="job", status="shortlisted", title="Backend Lead")
    db_session.add(opp)
    await db_session.commit()

    # First apply creates Application
    rec = await transition_application(
        db_session,
        ApplicationTransitionIn(opportunity_id=str(opp_id), expected_status=None, to_status="applied"),
        request_id="r1"
    )
    assert rec.status == "executed"
    assert rec.after["status"] == "applied"
```

- [x] **Step 2: Run test to verify it fails**

Run: `DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" backend/.venv/bin/pytest backend/tests/test_agent_actions_opportunity.py -v`
Expected: FAIL (`ImportError: cannot import name 'transition_opportunity' from 'app.integrations.agent.actions'`)

- [x] **Step 3: Implement `transition_opportunity` and `transition_application` in `actions.py`**

- `transition_opportunity`:
  - Check opportunity exists.
  - Verify `opp.status == data.expected_status` (raise `ValueError("STALE_ACTION: ...")`).
  - Call canonical `opportunity.application.transition_status(session, opp_id, to=data.to_status, note=data.note)`.
  - Return `ActionReceipt`.
- `transition_application`:
  - Check opportunity exists.
  - Query `Application` for this `opportunity_id`.
  - If no `Application`:
    - If `data.to_status == "applied"`: call `opportunity.application.apply(session, opp_id, ApplyIn(note=data.note))`.
    - Else: raise `ValueError("APPLICATION_NOT_FOUND: Application row does not exist; cannot transition to ...")`.
  - If `Application` exists:
    - If `data.expected_status` provided and `app.status != data.expected_status`: raise `ValueError("STALE_ACTION: ...")`.
    - Call canonical `opportunity.application.transition_application(session, opp_id, to=data.to_status, note=data.note, rejection_reason=data.rejection_reason)`.
  - Return `ActionReceipt`.

- [x] **Step 4: Run test to verify it passes**

Run: `DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" backend/.venv/bin/pytest backend/tests/test_agent_actions_opportunity.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/integrations/agent/actions.py backend/tests/test_agent_actions_opportunity.py
git commit -m "feat(agent): implement opportunity and application lifecycle action adapters"
```

---

### Task 5: Bookmark Local Capture & Update Action Adapters

**Files:**
- Modify: `backend/app/integrations/agent/actions.py`
- Create: `backend/tests/test_agent_actions_bookmark.py`

**Interfaces:**
- Consumes: `app.modules.bookmark.service` (`capture`, `update`)
- Produces: `capture_bookmark`, `update_bookmark`

- [x] **Step 1: Write failing tests for Bookmark actions**

```python
# In backend/tests/test_agent_actions_bookmark.py
import pytest
from app.integrations.agent.actions import capture_bookmark, update_bookmark
from app.integrations.agent.write_models import BookmarkCaptureIn, BookmarkUpdateIn

pytestmark = pytest.mark.anyio

async def test_bookmark_capture_and_dedup(db_session):
    url = "https://example.com/article?utm_source=twitter"
    rec1 = await capture_bookmark(db_session, BookmarkCaptureIn(url=url, title="Example"), request_id="r1")
    assert rec1.status == "executed"
    bm_id = rec1.target_id

    # Second capture returns duplicate notice without crashing
    rec2 = await capture_bookmark(db_session, BookmarkCaptureIn(url=url, title="Example 2"), request_id="r2")
    assert rec2.target_id == bm_id
    assert any("duplicate" in w.lower() for w in rec2.warnings)

async def test_bookmark_update(db_session):
    rec = await capture_bookmark(db_session, BookmarkCaptureIn(url="https://example.org/doc", title="Doc"), request_id="r1")
    bm_id = rec.target_id

    up_rec = await update_bookmark(
        db_session,
        BookmarkUpdateIn(bookmark_id=bm_id, favorite=True, read_status="read"),
        request_id="r2"
    )
    assert up_rec.status == "executed"
    assert up_rec.after["favorite"] is True
    assert up_rec.after["read_status"] == "read"
```

- [x] **Step 2: Run test to verify it fails**

Run: `DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" backend/.venv/bin/pytest backend/tests/test_agent_actions_bookmark.py -v`
Expected: FAIL (`ImportError: cannot import name 'capture_bookmark' from 'app.integrations.agent.actions'`)

- [x] **Step 3: Implement `capture_bookmark` and `update_bookmark` in `actions.py`**

- `capture_bookmark`:
  - Call canonical `bookmark_service.capture(session, CaptureIn(url=data.url, title=data.title, collection=data.collection, tags=data.tags, note=data.note))`.
  - Replayed or prior bookmark: include in `warnings=["Existing bookmark matches URL"]`.
  - Zero external network requests (no readability, no HTML fetching).
  - Return `ActionReceipt`.
- `update_bookmark`:
  - Verify `expected_updated_at` against `Entity.updated_at` if provided.
  - Call canonical `bookmark_service.update(session, bm_id, BookmarkUpdate(collection=data.collection, favorite=data.favorite, read_status=data.read_status, tags=data.tags))`.
  - Return `ActionReceipt`.

- [x] **Step 4: Run test to verify it passes**

Run: `DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" backend/.venv/bin/pytest backend/tests/test_agent_actions_bookmark.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/integrations/agent/actions.py backend/tests/test_agent_actions_bookmark.py
git commit -m "feat(agent): implement bookmark local capture and update adapters"
```

---

### Task 6: Obsidian Vault Managed Append & Inbox Capture Adapters

**Files:**
- Modify: `backend/app/integrations/agent/actions.py`
- Create: `backend/tests/test_agent_actions_knowledge.py`

**Interfaces:**
- Consumes: `app.integrations.obsidian.service` (`capture_knowledge_note`, `ensure_entity_knowledge_note`, `read_managed_note_body`, `update_managed_note_body`, `VaultStaleWriteError`, `VaultConflictError`)
- Produces: `capture_brain_note`, `save_to_entity_brain`

- [x] **Step 1: Write failing tests for Vault capture and managed note append**

```python
# In backend/tests/test_agent_actions_knowledge.py
import pytest
import uuid
from app.integrations.agent.actions import capture_brain_note, save_to_entity_brain
from app.integrations.agent.write_models import BrainCaptureIn, BrainSaveToEntityIn
from app.core.models import Entity
from app.modules.project.models import Project
from app.modules.note.models import Note

pytestmark = pytest.mark.anyio

async def test_brain_capture_writes_to_inbox_and_leaves_legacy_notes_untouched(db_session, mock_immutability_vault):
    notes_before = (await db_session.execute(select(func.count(Note.id)))).scalar_one()

    rec = await capture_brain_note(
        db_session,
        BrainCaptureIn(body="Captured meeting note", title="Meeting Note"),
        request_id="r1"
    )
    assert rec.status == "executed"
    assert "00 Inbox" in rec.after["relative_path"]

    # Legacy notes invariant
    notes_after = (await db_session.execute(select(func.count(Note.id)))).scalar_one()
    assert notes_before == notes_after

async def test_brain_save_to_entity_append(db_session, mock_immutability_vault):
    proj_id = uuid.uuid4()
    ent = Entity(id=proj_id, type="project", title="Roadmap Project", search_text="")
    db_session.add(ent)
    db_session.add(Project(id=proj_id, status="active"))
    await db_session.commit()

    # Save to entity
    rec = await save_to_entity_brain(
        db_session,
        BrainSaveToEntityIn(forkos_id=str(proj_id), text="Decided to use Streamable HTTP."),
        request_id="r2"
    )
    assert rec.status == "executed"
    assert rec.target_id == str(proj_id)
```

- [x] **Step 2: Run test to verify it fails**

Run: `DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" backend/.venv/bin/pytest backend/tests/test_agent_actions_knowledge.py -v`
Expected: FAIL (`ImportError: cannot import name 'capture_brain_note' from 'app.integrations.agent.actions'`)

- [x] **Step 3: Implement `capture_brain_note` and `save_to_entity_brain` in `actions.py`**

- `capture_brain_note`:
  - Call canonical `obsidian_service.capture_knowledge_note(session, body=data.body, title=data.title, relate_to=relate_uuid, tags=data.tags)`.
  - Returns `ActionReceipt` with `target_type="vault_note"`, `target_id=item.forkos_id`, `after={"relative_path": item.relative_path, "forkos_id": item.forkos_id, "title": item.title}`.
  - Zero SQL/Entity creation.
- `save_to_entity_brain`:
  - Input MUST be `forkos_id: str` (no `relative_path`).
  - Resolve or ensure note via `obsidian_service.ensure_entity_knowledge_note(session, ent_uuid)`.
  - Read note body via `obsidian_service.read_managed_note_body(forkos_id)`.
  - If `heading` provided:
    - Search for exact heading line `^#{1,6}\s+re.escape(heading)\s*$`.
    - If 0 matches: raise `ValueError(f"HEADING_NOT_FOUND: Heading '{heading}' not found in note.")`.
    - If > 1 matches: raise `ValueError(f"AMBIGUOUS_HEADING: Heading '{heading}' appears multiple times.")`.
    - Insert text under the matching heading section.
  - If `heading` is None:
    - Append text to note body (`f"{body.rstrip()}\n\n{text.strip()}\n"`).
  - Update via `obsidian_service.update_managed_note_body(forkos_id, new_body, expected_mtime=item.mtime)`.
  - Catch `VaultStaleWriteError` -> raise `ValueError("VAULT_STALE: Note was modified since read.")`.
  - Catch `VaultConflictError` -> raise `ValueError("VAULT_CONFLICT: Multiple notes have this forkos_id.")`.
  - Return `ActionReceipt`.

- [x] **Step 4: Run test to verify it passes**

Run: `DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" backend/.venv/bin/pytest backend/tests/test_agent_actions_knowledge.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/integrations/agent/actions.py backend/tests/test_agent_actions_knowledge.py
git commit -m "feat(agent): implement brain_capture and brain_save_to_entity action adapters"
```

---

### Task 7: Public MCP Tool Registration & Thin Handlers

**Files:**
- Modify: `backend/app/integrations/agent/tools.py`
- Modify: `backend/tests/test_agent_tools.py`

**Interfaces:**
- Consumes: `MCPServer`, `Context`, `actions.py`, `write_models.py`
- Produces: 19 public MCP tools (8 H0 read tools + 11 H1 write tools) with exact annotations.

- [x] **Step 1: Write failing tests for 19 MCP tools and annotations**

```python
# In backend/tests/test_agent_tools.py
async def test_mcp_tool_registration_and_metadata():
    tools = await mcp_server.list_tools()
    tool_map = {t.name: t for t in tools}

    expected_reads = [
        "forkos_briefing",
        "forkos_search",
        "forkos_entity_context",
        "forkos_project_context",
        "forkos_recent_activity",
        "brain_status",
        "brain_search",
        "brain_read",
    ]
    expected_writes = [
        "forkos_todo_create",
        "forkos_todo_update",
        "forkos_todo_complete",
        "forkos_todo_plan",
        "forkos_project_update",
        "forkos_opportunity_transition",
        "forkos_application_transition",
        "forkos_bookmark_capture",
        "forkos_bookmark_update",
        "brain_capture",
        "brain_save_to_entity",
    ]
    assert len(tool_map) == 19
    assert sorted(tool_map.keys()) == sorted(expected_reads + expected_writes)

    # Validate read annotations
    for name in expected_reads:
        t = tool_map[name]
        assert t.annotations.read_only_hint is True
        assert t.annotations.destructive_hint is False

    # Validate write annotations
    idempotent_tools = {
        "forkos_todo_update", "forkos_todo_complete", "forkos_todo_plan",
        "forkos_project_update", "forkos_bookmark_update"
    }
    for name in expected_writes:
        t = tool_map[name]
        assert t.annotations.read_only_hint is False
        assert t.annotations.destructive_hint is False
        assert t.annotations.idempotent_hint == (name in idempotent_tools)
```

- [x] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_agent_tools.py -k test_mcp_tool_registration_and_metadata -v`
Expected: FAIL (`assert len(tool_map) == 19` fails with 8)

- [x] **Step 3: Register all 11 H1 tools in `tools.py`**

In `backend/app/integrations/agent/tools.py`:
- Define `WRITE_ANNOTATIONS(idempotent: bool)` producing `ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=idempotent)`.
- Register the 11 tools:
  - `forkos_todo_create` (idempotent=False)
  - `forkos_todo_update` (idempotent=True)
  - `forkos_todo_complete` (idempotent=True, description includes recurrence clause)
  - `forkos_todo_plan` (idempotent=True)
  - `forkos_project_update` (idempotent=True, only next_action)
  - `forkos_opportunity_transition` (idempotent=False)
  - `forkos_application_transition` (idempotent=False)
  - `forkos_bookmark_capture` (idempotent=False)
  - `forkos_bookmark_update` (idempotent=True)
  - `brain_capture` (idempotent=False)
  - `brain_save_to_entity` (idempotent=False)
- Thin handlers take typed inputs + `ctx: Context`, open `async with SessionLocal()`, call corresponding function in `actions.py`, and return `AgentEnvelope[ActionReceipt]`.
- Map domain exceptions to clean `ToolError` codes (`STALE_ACTION`, `AMBIGUOUS_PLAN`, `VAULT_STALE`, `VAULT_CONFLICT`, `VAULT_UNAVAILABLE`, `TARGET_NOT_FOUND`, `INVALID_TRANSITION`, `HEADING_NOT_FOUND`, `AMBIGUOUS_HEADING`).

- [x] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_agent_tools.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/integrations/agent/tools.py backend/tests/test_agent_tools.py
git commit -m "feat(agent): register 11 H1 write tools with accurate annotations and thin handlers"
```

---

### Task 8: Comprehensive Verification & Test Suite

**Files:**
- Create: `backend/tests/test_agent_h1_contract.py`
- Create: `backend/tests/test_agent_h1_mutation_scope.py`
- Create: `backend/tests/test_agent_h1_failure_immutability.py`
- Modify: `backend/tests/test_agent_mcp.py`

**Interfaces:**
- Consumes: All 19 tools across DB and Vault test fixtures
- Produces: Contract tests, mutation scope proofs, failure immutability proofs, Streamable HTTP MCP smoke test.

- [x] **Step 1: Write `test_agent_h1_contract.py`**
  - Verify exact 19 public tools (8 read + 11 write).
  - Verify `destructiveHint` is `False` across all 19 tools.
  - Verify absence of forbidden tools (`call_api`, `execute_sql`, `write_file`, `delete_todo`, etc.).
  - Verify input schema properties and bounds for each tool.

- [x] **Step 2: Write `test_agent_h1_mutation_scope.py`**
  - For each of the 11 tools: execute valid mutation.
  - Verify that only the intended domain tables/Vault files changed.
  - Assert that legacy note tables (`note`, `note_folder`, `note_attachment`) had 0 mutations.

- [x] **Step 3: Write `test_agent_h1_failure_immutability.py`**
  - Capture pre-failure DB content fingerprint (`_capture_db_content_fingerprint`) and pre-failure Vault file tree hash.
  - Execute every failure case:
    - Stale expected_updated_at in `todo_update`, `project_update`, `bookmark_update`
    - Stale expected_status in `opportunity_transition`, `application_transition`
    - Ambiguous plan in `todo_plan`
    - Missing heading / Vault conflict in `brain_save_to_entity`
    - Invalid inputs / non-existent IDs across all tools
  - Capture post-failure DB content fingerprint and Vault file tree hash.
  - Assert that pre and post fingerprints are 100% identical.

- [x] **Step 4: Update `test_agent_mcp.py` for Streamable HTTP smoke test**
  - Initialize session over `http://127.0.0.1/mcp/`.
  - Assert 19 tools returned by `session.list_tools()`.
  - Call H0 read tool (`brain_status`).
  - Call H1 write tool (`forkos_todo_create`), verify `ActionReceipt` response.

- [x] **Step 5: Run full test suite & linters**

Run:
```bash
DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" backend/.venv/bin/pytest backend/tests/test_agent_*.py -v
DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" backend/.venv/bin/pytest backend/tests/test_obsidian_*.py backend/tests/test_todo_*.py backend/tests/test_project_*.py backend/tests/test_opportunity_*.py backend/tests/test_bookmark_*.py backend/tests/test_registry.py -q
backend/.venv/bin/ruff check backend/app/integrations/agent/ backend/tests/
git diff --check
```
Expected: ALL PASS, 0 lint errors, 0 whitespace warnings.

- [x] **Step 6: Commit**

```bash
git add backend/tests/
git commit -m "test(agent): add H1 contract, mutation scope, failure immutability, and mcp streamable http tests"
```

---

### Task 9: Documentation Set & Readiness Gate

**Files:**
- Create: `docs/hermes/h1-safe-actions.md`
- Create: `docs/hermes/h1-tool-contract.md`
- Create: `docs/hermes/h1-setup.md`
- Modify: `docs/hermes/roadmap.md`

- [x] **Step 1: Write `docs/hermes/h1-safe-actions.md`**
  - Document H1 architecture, the client-approval model (`trust: untrusted`), `ActionReceipt` schema, optimistic preconditions, failure semantics, local-only guarantee, and legacy note invariant.

- [x] **Step 2: Write `docs/hermes/h1-tool-contract.md`**
  - Document all 19 tools (8 H0 + 11 H1) with exact schemas, arguments, annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`), and error envelopes.

- [x] **Step 3: Write `docs/hermes/h1-setup.md`**
  - Document Hermes configuration for H1 with untrusted approval, Streamable HTTP MCP url (`http://127.0.0.1:8000/mcp`), and tool allowlist profiles.

- [x] **Step 4: Update `docs/hermes/roadmap.md`**
  - Mark H0 completed, H0.1 completed, H1 completed. Detail H2 hot memory boundary.

- [x] **Step 5: Verify git status and compile final gate report**

Run: `git status --short`
Compile the final report matching Section 145 sections A through Q, ending with `HERMES_READINESS_H1 = YES`.

- [x] **Step 6: Commit**

```bash
git add docs/hermes/
git commit -m "docs(hermes): add H1 safe actions, tool contract, setup, and roadmap documentation"
```

---

## Verification Plan

### Automated Tests
- Agent test suite: `DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" backend/.venv/bin/pytest backend/tests/test_agent_*.py -v`
- Domain regression test suites: `backend/.venv/bin/pytest backend/tests/test_obsidian_*.py backend/tests/test_todo_*.py backend/tests/test_project_*.py backend/tests/test_opportunity_*.py backend/tests/test_bookmark_*.py backend/tests/test_registry.py -q`
- Linter: `backend/.venv/bin/ruff check backend/app/integrations/agent/ backend/tests/`
- Git whitespace check: `git diff --check`

### Manual Verification
- Streamable HTTP MCP client session verification against FastAPI ASGI runtime.
- Pre- and post-failure database and Vault content hashing to verify 100% failure immutability.
- Verification that no external network calls or legacy note table modifications occurred.

---

## Uygulama Notları (H1 tamamlandı)

Plan uygulandı; aşağıdaki noktalarda planın taslak kodunda **gerçek domain
sözleşmesiyle uyuşmayan** varsayımlar düzeltildi:

1. **`Opportunity.title` yoktur.** Başlık `Entity.title`'da yaşar (Opportunity
   modelinde kolon yok). Adaptör ve testler `Entity` üzerinden okur/yazar.
2. **`Collection` sözlüğü** canonical `bookmark.models.COLLECTIONS` ile
   hizalandı: `inbox | read_later | learning | reference | projects | archive`.
   Taslaktaki `"bookmarks"` değeri geçerli bir koleksiyon değildir; sırf bu
   yüzden canonical katmanda 422 verirdi.
3. **`Todo.title` yoktur** — `Todo` modelinde başlık kolonu bulunmaz
   (`Entity.title`). Görev makbuzları `title`'ı dışarıdan alır.
4. **`ApplicationHistory.occurred_at` yoktur** (kolonlar: `id`,
   `opportunity_id`, `from_status`, `to_status`, `scope`).
5. **`pytestmark = pytest.mark.no_database`** taşıma testlerinin tamamına
   uygulanamaz: H1 yazma turu gerçek veritabanı gerektirir. İşaret, yalnızca
   DB gerektirmeyen testlere taşındı.
6. **Altı görev (3–6) tek `actions.py` dosyasında** birleştirildi; ayrı
   dosyalara bölmek yapay olurdu. Testler yine domain başına ayrı dosyalarda.
7. **Ek sertleştirme:** tüm H1 girdi modelleri `extra="forbid"`; idempotent
   araçlar aynı değerde canonical servisi hiç çağırmaz (`status=noop`);
   araç şemalarında girdi sınırları GÖRÜNÜR; H1 test modüllerinde autouse ağ
   koruması vardır.
8. **H0 araç sayısı iddiası güncellendi:** `test_agent_tools.py` artık 19
   toplam araç bekler ve H0 okuma sözleşmesinin zayıflatılmadığını kanıtlar.
