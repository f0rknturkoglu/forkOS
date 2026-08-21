# Opportunity Trash, Sync Status, and Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add recoverable and permanent opportunity deletion, persistent source-sync progress, YLSY/ÖSYM tabs, a simplified detail drawer, and a correctly connected activity timeline.

**Architecture:** Opportunity lifecycle mutations stay in the opportunity service and always update the entity/event layers together. Manual source refreshes are grouped in a persistent operational batch linked from `source_run`; the same API response drives a compact opportunities progress bar and the full sources dashboard. Frontend changes reuse the existing module registry, query invalidation, dialogs, and design tokens.

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL 16, Alembic, React 18, TanStack Query, TypeScript, Tailwind CSS, pytest.

## Global Constraints

- Everything stays local-only and binds to `127.0.0.1`; no external data is sent beyond existing source fetches.
- Opportunity records remain entity-backed and every write uses `app/core/entity.py` helpers.
- `event` is append-only; every trash, restore, permanent delete, and meaningful sync action logs an event.
- Every migration SQL command uses its own `op.execute()` call.
- `source_sync_batch` is an operational support table, documented as the same class of exception as `source_run`.
- Offline mode remains read-only.
- Existing user changes in the dirty worktree must be preserved; stage only files owned by each task.

---

### Task 1: Opportunity trash lifecycle

**Files:**
- Create: `backend/alembic/versions/0018_opportunity_trash_sync.py`
- Modify: `backend/app/core/entity.py`
- Modify: `backend/app/modules/opportunity/models.py`
- Modify: `backend/app/modules/opportunity/schemas.py`
- Modify: `backend/app/modules/opportunity/service.py`
- Modify: `backend/app/modules/opportunity/router.py`
- Test: `backend/tests/test_opportunity_lifecycle.py`

**Interfaces:**
- Produces: `trash_opportunity(session, item_id)`, `restore_opportunity(session, item_id)`, `delete_opportunity(session, item_id)` and `include_trashed`/`trashed_only` list filtering.
- Produces endpoints: `POST /api/opportunities/{id}/trash`, `POST /api/opportunities/{id}/restore`, `DELETE /api/opportunities/{id}`.

- [ ] **Step 1: Write failing lifecycle tests**

Create an opportunity through the API, trash it, assert it disappears from the default list and appears with `trashed_only=true`; restore it and assert the prior status returns. Trash it again, permanently delete it, assert both opportunity and entity disappear while `opportunity.deleted` remains in `/api/activity` with a null entity id.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `docker compose exec -T api pytest -q tests/test_opportunity_lifecycle.py`

Expected: endpoint/schema failures because trash lifecycle is not implemented.

- [ ] **Step 3: Add migration and model fields**

Add separate migration operations for:

```sql
alter table opportunity add column trashed_at timestamptz
alter table opportunity add column trashed_from_status text
create index opportunity_trash_idx on opportunity (trashed_at desc) where trashed_at is not null
```

The same revision also creates the sync tables described by Task 2 so the repository keeps a single next migration revision.

- [ ] **Step 4: Add entity deletion helper and service lifecycle**

Add `delete_entity(session, entity_id)` to load and `session.delete()` the entity. Service methods set `trashed_at`, preserve `trashed_from_status`, touch the entity, log the exact lifecycle event, and commit. Permanent deletion logs and flushes the event before calling `delete_entity`; the event FK becomes null through `ON DELETE SET NULL`.

- [ ] **Step 5: Add dedicated routes and list filters**

Default list query must include `Opportunity.trashed_at.is_(None)`. `trashed_only=true` switches it to `is_not(None)`. General PATCH rejects direct `status=trashed` so lifecycle metadata cannot become inconsistent.

- [ ] **Step 6: Verify GREEN**

Run: `docker compose exec -T api pytest -q tests/test_opportunity_lifecycle.py tests/test_api.py::test_phase3_opportunity_flow`

Expected: all selected tests pass.

### Task 2: Persistent source sync batches

**Files:**
- Modify: `backend/alembic/versions/0018_opportunity_trash_sync.py`
- Modify: `backend/app/core/models.py`
- Create: `backend/app/modules/opportunity/sync.py`
- Modify: `backend/app/modules/opportunity/worker.py`
- Modify: `backend/app/modules/opportunity/router.py`
- Test: `backend/tests/test_source_sync.py`

**Interfaces:**
- Produces: `SourceSyncBatch`, `create_or_extend_batch(session, source_ids)`, `batch_status(session)`, `batch_history(session, limit)`.
- `poll_named_source(source_id, batch_id=None)` and `poll_source(source, batch_id=None)` associate each run and update the batch after completion.
- API `GET /sources/sync` returns `{active, sources}` and `GET /sources/sync/history` returns batch summaries.

- [ ] **Step 1: Write failing batch tests**

Test a three-source batch with one `ok`, one `empty`, and one `error`; assert `progress_pct` advances 0, 33, 66, 100 and final status is `completed_with_errors`. Extend an active batch with overlapping IDs and assert only new IDs increase `total_sources`.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `docker compose exec -T api pytest -q tests/test_source_sync.py`

Expected: missing batch model/helper failures.

- [ ] **Step 3: Create operational schema**

Create `source_sync_batch` with UUID PK, JSONB source list, counters, timestamps, and status. Add nullable `source_run.batch_id` with FK `on delete set null` and an index. Each DDL statement is a separate `op.execute()`.

- [ ] **Step 4: Implement batch state transitions**

Use row locking when extending or completing a batch. Calculate `progress_pct` from completed/total in the output serializer. A source completion increments exactly one of ok/empty/error and adds `items_found`; the final source sets `finished_at` and final status.

- [ ] **Step 5: Wire refresh orchestration**

`POST /sources/refresh` resolves and deduplicates IDs, creates or extends the active batch, schedules only newly added source IDs, and returns `batch_id`, `queued`, and `total_sources`. Individual refresh can remain synchronous but participates in a one-source batch for consistent visibility.

- [ ] **Step 6: Verify GREEN and regression safety**

Run: `docker compose exec -T api pytest -q tests/test_source_sync.py tests/test_migrations.py`

Expected: batch and migration tests pass.

### Task 3: Opportunity tabs, trash controls, and compact sync bar

**Files:**
- Modify: `frontend/src/core/types.ts`
- Modify: `frontend/src/modules/opportunity/OpportunityPage.tsx`
- Create: `frontend/src/modules/opportunity/SyncProgress.tsx`
- Modify: `frontend/src/modules/opportunity/SourcePicker.tsx`
- Modify: `frontend/src/modules/opportunity/labels.ts`

**Interfaces:**
- Produces frontend types `SourceSyncBatch`, `SourceSyncStatus`, and opportunity trash fields.
- `SyncProgress({ compact?: boolean })` consumes `/sources/sync` and links to `/sources` on errors.

- [ ] **Step 1: Add tab classification helpers and types**

Define the exact tabs `jobs`, `ylsy`, `osym`, `announcements`, `trash`. Jobs match `kind === "job"`; YLSY and ÖSYM match source; other announcements exclude all three; trash matches `trashed_at != null`.

- [ ] **Step 2: Add mutation controls with confirmation**

Normal cards call `confirmDialog` then `POST /opportunities/{id}/trash`. Trash cards expose restore and permanent delete; permanent delete shows the title and calls DELETE only after explicit confirmation. Success invalidates opportunities and activity.

- [ ] **Step 3: Add compact progress component**

Poll every two seconds while active and every 15 seconds otherwise. Render a token-based progress bar, exact percent, completed/total, running count, found count, and linked error count. Preserve the last completed result briefly through query data rather than local persistence.

- [ ] **Step 4: Update picker response handling**

Use the new refresh response type and keep selected-count behavior. Invalidate `source-sync`, `source-sync-history`, `source-runs`, and opportunities after queueing.

- [ ] **Step 5: Build frontend**

Run: `docker compose exec -T web npm run build`

Expected: TypeScript and Vite production build succeed.

### Task 4: Full source status dashboard

**Files:**
- Modify: `frontend/src/modules/opportunity/SourceHealthPage.tsx`
- Reuse: `frontend/src/modules/opportunity/SyncProgress.tsx`

**Interfaces:**
- Consumes `SourceSyncStatus` and `/sources/sync/history`.
- Preserves existing source selection, filtering, health badges, and refresh controls.

- [ ] **Step 1: Add active batch summary**

Render the expanded progress component above the source table with duration, ok/empty/error counters, items found, and active source names.

- [ ] **Step 2: Add per-source batch state**

Merge active batch source states with latest `source_run` data. Running sources spin, finished sources show their exact batch status, and errors expose the error text without hiding the source row.

- [ ] **Step 3: Add recent batch history**

Fetch the last ten batches and render created time, duration, total sources, final status, found count, and error count in a compact history panel.

- [ ] **Step 4: Verify production build**

Run: `docker compose exec -T web npm run build`

Expected: build succeeds with no TypeScript errors.

### Task 5: Simplify opportunity detail and repair timeline

**Files:**
- Modify: `frontend/src/modules/opportunity/OpportunityDetail.tsx`
- Modify: `frontend/src/modules/activity/ActivityPage.tsx`
- Modify: `frontend/src/modules/activity/verbs.ts`

**Interfaces:**
- Detail retains score, identity, status, external URL, requirements/document binding, and notes.
- Timeline renders first/middle/last connectors without changing activity API data.

- [ ] **Step 1: Remove application-step UI**

Remove Todo imports, todo query, step state, addTodo mutation, application-step list, and form. Keep requirement mutation and document binding intact.

- [ ] **Step 2: Implement timeline rows**

Each row uses a fixed-width rail. Draw a top half-line unless it is the first event and a bottom half-line unless it is the last event. Center a surface-ringed dot over both line halves. Keep day heading outside the rail while preserving alignment.

- [ ] **Step 3: Add lifecycle and sync verb labels**

Add Turkish labels for `opportunity.trashed`, `opportunity.restored`, `opportunity.deleted`, `source_sync.started`, `source_sync.sources_added`, and `source_sync.completed`; mark completed-with-errors activity as alert through payload-aware styling or a dedicated error verb.

- [ ] **Step 4: Verify build**

Run: `docker compose exec -T web npm run build`

Expected: production build succeeds and no Başvuru adımları string remains in `OpportunityDetail.tsx`.

### Task 6: End-to-end verification

**Files:**
- Test: all files changed in Tasks 1-5

- [ ] **Step 1: Apply migration in the running local stack**

Run: `docker compose exec -T api alembic upgrade head`

Expected: revision `0018` applies without asyncpg multi-command errors.

- [ ] **Step 2: Run backend suites**

Run: `docker compose exec -T api pytest -q tests/test_opportunity_lifecycle.py tests/test_source_sync.py tests/test_api.py tests/test_migrations.py`

Expected: zero failures.

- [ ] **Step 3: Run frontend build**

Run: `docker compose exec -T web npm run build`

Expected: TypeScript and Vite exit 0.

- [ ] **Step 4: Verify services and hygiene**

Run: `docker compose ps && curl -fsS http://127.0.0.1:8787/health && git diff --check`

Expected: db/api/worker/web are up, health is `ok`, and diff check emits no errors.

- [ ] **Step 5: Review the final diff without staging unrelated work**

Use `git status --short` and path-limited diffs. Do not create an implementation commit that accidentally includes the user's pre-existing opportunity/frontend changes.
