# A1.1b + A2.1 Correctness & Completeness Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strengthen the A1.1 no-mutation invariant test to full row-content state fingerprinting, and complete the A2.1 contracts (bounded source fingerprinting, scope invalidation, deterministic topic compatibility, bounded f0rknbrain integration, hot-path walk removal, hard 4000-char budget, zero prompt logging, universal escaping, ephemeral pruning, UI semantics, and plugin isolation) on the `main` branch.

**Architecture:** Single orchestration entrypoint (`POST /api/agent/lifecycle/turn`) called from Hermes `pre_llm_call` that atomically records A1 lifecycle observation first (committed independently), then composes A2 bounded bootstrap context (read-only against canonical sources) with strict budgets, prompt injection defense, and ephemeral source continuity tracking (`agent_session_context`, `agent_session_source`). `on_session_finalize` uses existing `/api/agent/lifecycle/event`.

**Architecture Diagram:**

```mermaid
graph TD
    subgraph "Hermes Agent (Local)"
        H_PRE["pre_llm_call Hook"]
        H_FIN["on_session_finalize Hook"]
    end

    subgraph "forkOS API Gateway"
        TURN_EP["POST /api/agent/lifecycle/turn"]
        EVENT_EP["POST /api/agent/lifecycle/event"]
    end

    subgraph "A1 Lifecycle Service"
        A1_OBS["observe(session_start | turn_seen)"]
        A1_FIN["observe(session_finalize)"]
        A1_DB[("agent_session\nagent_session_turn")]
    end

    subgraph "A2 Context Service"
        A2_COMPOSE["compose(first_turn vs later_turn)"]
        A2_BUDGET["Field Sanitization & Hard 4000-Char Cap"]
        A2_RENDER["html.escape + Path Redaction"]
        A2_DB[("agent_session_context\nagent_session_source")]
    end

    subgraph "Canonical Sources (Read-Only)"
        F0RK_VAULT["f0rknbrain Vault (fast check, no os.walk)"]
        H2_HOT["H2 Hot Memory (revision hash)"]
        H5_CONT["H5 Continuity"]
        FORK_DB[("forkOS Operational DB (payload fingerprint)")]
    end

    H_PRE -->|Single HTTP POST| TURN_EP
    H_FIN -->|Single HTTP POST| EVENT_EP

    TURN_EP -->|1. Independent Commit| A1_OBS
    A1_OBS --> A1_DB

    TURN_EP -->|2. Read-Only Compose| A2_COMPOSE
    A2_COMPOSE --> F0RK_VAULT
    A2_COMPOSE --> H2_HOT
    A2_COMPOSE --> H5_CONT
    A2_COMPOSE --> FORK_DB
    A2_COMPOSE --> A2_BUDGET
    A2_BUDGET --> A2_RENDER
    A2_COMPOSE -->|Support State Transaction| A2_DB

    EVENT_EP --> A1_FIN
    A1_FIN --> A1_DB
```

**Tech Stack:** FastAPI, SQLAlchemy 2.0 Async, PostgreSQL 16 (asyncpg), Alembic, Pydantic v2, Vite / React / TypeScript, Hermes CLI v0.21.3.

**Spec:** [`docs/superpowers/specs/2026-09-22-a1-1b-a2-1-correctness-pass-design.md`](../specs/2026-09-22-a1-1b-a2-1-correctness-pass-design.md)

## Global Constraints

- Strictly local-only: loopback `127.0.0.1`, `localhost`, `::1`; zero external network calls.
- Zero mutation of canonical `entity`, `event`, `link`, `todo`, `project`, `opportunity`, `notification`, `proactivity_run`, `execution_plan` or Vault files by lifecycle or context composition.
- A3 (episodic), A4 (cross-day), A5 (answer judge) are strictly EXCLUDED.
- Ephemeral raw user prompts are never persisted in Postgres, logged, or saved to Vault.
- Absolute host paths are strictly forbidden in persistent metadata, diagnostics, responses, and prompt context (`vault:<relative_path>`, `entity:<uuid>`).
- All tests run against test DB: `DATABASE_URL=postgresql+asyncpg://lifeos:lifeos@127.0.0.1:5433/lifeos_test`.

---

## Tasks

### Task 1: A1.1b Full State Fingerprint Invariant Test & Negative Proofs

**Files:**
- Modify: `backend/tests/test_agent_lifecycle_invariants.py`

- [ ] **Step 1: Write state fingerprint serialization helper**
  Query all 18 DOMAIN_MODELS ordered by primary key, serialize all column values into stable string tuples, and compute SHA-256 digest per table.
- [ ] **Step 2: Add negative verification unit tests**
  Verify that a simulated row UPDATE on `todo`, row INSERT on `project`, row DELETE on `entity`, or file mutation in Vault fails the invariant check.
- [ ] **Step 3: Run invariant test and negative proofs**
  Run: `PATH="$PWD/backend/.venv/bin:$PATH" DATABASE_URL=postgresql+asyncpg://lifeos:lifeos@127.0.0.1:5433/lifeos_test backend/.venv/bin/pytest backend/tests/test_agent_lifecycle_invariants.py -v`
- [ ] **Step 4: Commit**
  `git commit -m "test(lifecycle): strengthen A1.1b invariant to full state fingerprint with negative proofs"`

---

### Task 2: Fast Vault Availability Check (Remove `os.walk` from First-Turn Hot Path)

**Files:**
- Modify: `backend/app/integrations/agent/knowledge.py`
- Modify: `backend/app/modules/agent_continuity/service.py`
- Modify: `backend/tests/test_agent_continuity_service.py`

- [ ] **Step 1: Add fast availability helper**
  Define `is_vault_accessible() -> bool` in `knowledge.py` checking existence, directory check, and read permissions without `os.walk`.
- [ ] **Step 2: Replace `get_brain_status()` in `service.py`**
  In `compose_first_turn_bootstrap`, use `is_vault_accessible()` instead of `get_brain_status()`.
- [ ] **Step 3: Write test asserting `os.walk` is not called**
  Monkeypatch `os.walk` with an assertion that it is never called during `compose_first_turn_bootstrap`.
- [ ] **Step 4: Verify test passes**
  Run: `backend/.venv/bin/pytest backend/tests/test_agent_continuity_service.py -v`
- [ ] **Step 5: Commit**
  `git commit -m "perf(continuity): remove full vault walk from first-turn bootstrap hot path"`

---

### Task 3: Operational & Vault Source Payload Fingerprinting & Stale Detection

**Files:**
- Modify: `backend/app/modules/agent_continuity/service.py`
- Modify: `backend/tests/test_agent_continuity_continuity.py`

- [ ] **Step 1: Implement `compute_source_version` for all source types**
  - Project: `sha256(f"{title}|{status}|{next_action or ''}|{last_activity_at or ''}")`
  - Todo/Deadline: `sha256(f"{title}|{due_at or ''}|{status}")`
  - Decision: `sha256(f"{summary}|{status}|{revision}")`
  - Hot Memory: `item.revision`
  - Vault note: `sha256(note_bytes)`
- [ ] **Step 2: Check source version on ambiguous continuation**
  If stored `source_version` does not match live payload fingerprint, mark source stale (`SOURCE_STALE`), do NOT reuse, trigger fresh bounded retrieval.
- [ ] **Step 3: Write unit test for stale source detection**
  Deliver project source v1 $\rightarrow$ mutate `project.next_action` $\rightarrow$ verify ambiguous continuation does NOT reuse stale v1.
- [ ] **Step 4: Verify test passes**
  Run: `backend/.venv/bin/pytest backend/tests/test_agent_continuity_continuity.py -v`
- [ ] **Step 5: Commit**
  `git commit -m "feat(continuity): implement deterministic source payload fingerprinting and stale detection"`

---

### Task 4: `scope_project` Real Invalidation Boundary

**Files:**
- Modify: `backend/app/modules/agent_continuity/models.py`
- Create: `backend/alembic/versions/0065_agent_continuity_scope_project.py`
- Modify: `backend/app/modules/agent_continuity/service.py`
- Modify: `backend/tests/test_agent_continuity_continuity.py`

- [ ] **Step 1: Add `scope_project` to `AgentSessionContext` model and migration**
  Add nullable `scope_project` column in migration `0065_agent_continuity_scope_project.py`.
- [ ] **Step 2: Implement scope transition matrix in `compose_later_turn_context`**
  - $A \rightarrow A$: reuse valid sources.
  - $A \rightarrow B$: invalidate old sources.
  - $A \rightarrow \text{None}$: clear project sources, keep general sources.
  - $\text{None} \rightarrow B$: focus on $B$ sources.
- [ ] **Step 3: Write unit tests covering all 4 scope transitions**
  Verify each transition in `test_agent_continuity_continuity.py`.
- [ ] **Step 4: Run migration and tests**
  Run: `backend/.venv/bin/alembic upgrade head && backend/.venv/bin/pytest backend/tests/test_agent_continuity_continuity.py -v`
- [ ] **Step 5: Commit**
  `git commit -m "feat(continuity): implement scope_project invalidation boundary with migration 0065"`

---

### Task 5: Deterministic Topic Compatibility (Option A)

**Files:**
- Modify: `backend/app/modules/agent_continuity/service.py`
- Modify: `backend/tests/test_agent_continuity_continuity.py`

- [ ] **Step 1: Implement `derive_topic_signature` and `is_topic_compatible`**
  Extract normalized keyword tokens from active sources. If prompt tokens overlap with active source titles/entities or match scope, treat as same topic.
- [ ] **Step 2: Update `compose_later_turn_context`**
  Non-ambiguous prompt on the same topic preserves existing sources; only confirmed shift invalidates.
- [ ] **Step 3: Write unit test for same-topic direct follow-up**
  Verify continuity is preserved for prompt 2 when discussing the same topic.
- [ ] **Step 4: Run tests**
  Run: `backend/.venv/bin/pytest backend/tests/test_agent_continuity_continuity.py -v`
- [ ] **Step 5: Commit**
  `git commit -m "feat(continuity): implement deterministic topic compatibility without remote models"`

---

### Task 6: f0rknbrain as a Bounded A2 Source

**Files:**
- Modify: `backend/app/modules/agent_continuity/service.py`
- Modify: `backend/tests/test_agent_continuity_service.py`
- Modify: `backend/tests/test_agent_continuity_continuity.py`

- [ ] **Step 1: Add bounded f0rknbrain knowledge retrieval in first-turn and later-turn**
  Fetch durable preferences/corrections from `90 Agent/` or linked project notes (max 2-3 notes, $\le 250$ chars each).
  Provenance: `source_type="vault_note"`, `source_id="vault:<relative_path>"`, `source_version="sha256"`.
- [ ] **Step 2: Graceful fallback**
  Fail-open with `VAULT_UNAVAILABLE` on vault error; search miss continues with knowledge absent.
- [ ] **Step 3: Write tests for bounded vault source inclusion and fallback**
- [ ] **Step 4: Run tests**
  Run: `backend/.venv/bin/pytest backend/tests/test_agent_continuity_service.py -v`
- [ ] **Step 5: Commit**
  `git commit -m "feat(continuity): add bounded f0rknbrain knowledge source integration"`

---

### Task 7: Universal Escaping & True Hard 4000-Character Budget

**Files:**
- Modify: `backend/app/modules/agent_continuity/renderer.py`
- Modify: `backend/app/modules/agent_continuity/service.py`
- Modify: `backend/tests/test_agent_continuity_renderer.py`

- [ ] **Step 1: Universal untrusted data escaping**
  In `renderer.py`, use `html.escape(text, quote=True)` and `redact_absolute_paths`.
- [ ] **Step 2: Field sanitization and safe hard-ceiling cap**
  Sanitize individual field lengths; if rendered context still exceeds 4000 chars, truncate trailing section lines while preserving the closing `</forkos-context>` intact.
- [ ] **Step 3: Write adversarial tests**
  Test huge inputs (10k char deadline, 10k char H2 note, adversarial XML tags `</forkos-context>`, `<system>`, `<tool>`). Assert `len(rendered) <= 4000` and closing tag intact.
- [ ] **Step 4: Run tests**
  Run: `backend/.venv/bin/pytest backend/tests/test_agent_continuity_renderer.py -v`
- [ ] **Step 5: Commit**
  `git commit -m "feat(continuity): implement universal XML escaping and true hard 4000-char budget"`

---

### Task 8: Privacy: Zero Prompt Logging

**Files:**
- Modify: `backend/app/modules/agent_continuity/service.py`
- Modify: `backend/app/modules/agent_lifecycle/router.py`
- Modify: `backend/tests/test_agent_continuity_continuity.py`

- [ ] **Step 1: Scrub all prompt/candidate query strings from logger calls**
  Replace `candidate` or `exc` string logging with `type(exc).__name__`.
- [ ] **Step 2: Write test asserting prompt secret marker never appears in logs**
  Send prompt with `SECRET_PROMPT_MARKER_XYZ` and assert marker is absent from captured log records.
- [ ] **Step 3: Run tests**
  Run: `backend/.venv/bin/pytest backend/tests/test_agent_continuity_continuity.py -k "log" -v`
- [ ] **Step 4: Commit**
  `git commit -m "fix(privacy): ensure raw prompt and query strings are never logged"`

---

### Task 9: Bounded Ephemeral Retention & Cleanup

**Files:**
- Modify: `backend/app/modules/agent_continuity/service.py`
- Modify: `backend/tests/test_agent_continuity_service.py`

- [ ] **Step 1: Implement opportunistic pruning**
  Delete expired sources (`expires_at < now()`) and retain latest 50 context rows per session.
- [ ] **Step 2: Write test for pruning**
  Verify that expired sources and old context rows are pruned during support commit.
- [ ] **Step 3: Run tests**
  Run: `backend/.venv/bin/pytest backend/tests/test_agent_continuity_service.py -v`
- [ ] **Step 4: Commit**
  `git commit -m "feat(continuity): add opportunistic pruning for ephemeral storage"`

---

### Task 10: Outer `/turn` Transaction Isolation & Explicit Rollback

**Files:**
- Modify: `backend/app/modules/agent_lifecycle/router.py`
- Modify: `backend/tests/test_agent_lifecycle_turn_endpoint.py`

- [ ] **Step 1: Ensure explicit rollback of A2 support transaction on failure**
  In the `except Exception` handler of `turn` endpoint, explicitly rollback the A2 support session while preserving A1 commit.
- [ ] **Step 2: Write test verifying A1 isolation when A2 fails**
  Assert A1 turn is persisted even when A2 raises an error.
- [ ] **Step 3: Run tests**
  Run: `backend/.venv/bin/pytest backend/tests/test_agent_lifecycle_turn_endpoint.py -v`
- [ ] **Step 4: Commit**
  `git commit -m "fix(lifecycle): enforce explicit A2 transaction rollback with A1 commit isolation"`

---

### Task 11: Diagnostics & UI Semantics

**Files:**
- Modify: `backend/app/modules/agent_continuity/schemas.py`
- Modify: `backend/app/modules/agent_continuity/service.py`
- Modify: `frontend/src/core/agentContinuity.ts`
- Modify: `frontend/src/modules/settings/BrainAgentSection.tsx`
- Modify: `frontend/src/modules/settings/BrainAgentSection.test.tsx`

- [ ] **Step 1: Add `last_context_at` to `ContinuityStatusOut`**
  Update schema and service to populate `last_context_at` and scope `active_source_count` to latest session.
- [ ] **Step 2: Update UI in `BrainAgentSection.tsx`**
  Differentiate "Başlangıç bağlamı" (`last_bootstrap_at`) from "Son bağlam" (`last_context_at`).
- [ ] **Step 3: Update frontend test**
  Run: `cd frontend && npm test -- src/modules/settings/BrainAgentSection.test.tsx --run`
- [ ] **Step 4: Commit**
  `git commit -m "feat(ui): refine continuity diagnostics with last_context_at and session-scoped sources"`

---

### Task 12: Plugin Cleanup & Contract Sync

**Files:**
- Modify: `tools/hermes/forkos-lifecycle/__init__.py`
- Generate: `backend/openapi.json`
- Generate: `frontend/src/generated/api-schema.ts`
- Modify: `frontend/scripts/check-endpoint-coverage.mjs`

- [ ] **Step 1: Update plugin docstring and define `MAX_PLUGIN_USER_MESSAGE_CHARS = 500`**
- [ ] **Step 2: Install plugin to `~/.hermes/plugins/forkos-lifecycle`**
- [ ] **Step 3: Regenerate OpenAPI and TypeScript types**
  Run `npm run generate-api` and check coverage.
- [ ] **Step 4: Commit**
  `git commit -m "chore(api): sync openapi.json and plugin cleanup"`

---

### Task 13: Full Regression, Live Hermes Benchmark & Documentation

**Files:**
- Modify: `docs/hermes/a2-bootstrap-continuity.md`
- Modify: `docs/hermes/README.md`
- Update: `walkthrough.md`

- [ ] **Step 1: Run full test suites**
  Run backend and frontend suites.
- [ ] **Step 2: Run live Hermes benchmark**
  Measure latencies: first-turn, ambiguous, same-topic, topic-shift.
- [ ] **Step 3: Update documentation with truthful epistemics**
- [ ] **Step 4: Commit and push to `origin/main`**
  `git commit -m "docs(hermes): update A2.1 documentation with benchmark and epistemics"`
