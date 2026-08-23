# forkOS Core Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make forkOS safe to test, correct at Istanbul day boundaries, durable under process restarts, consistently offline-read-only, and cheaper to evolve across backend, frontend, extension, and source modules.

**Architecture:** Keep the existing entity/event/module registries intact. Operational source work stays in the existing `source_sync_batch` and `source_run` support tables; the worker becomes the only executor. Cross-module concerns move into small shared primitives: backend local-time helpers, frontend mutation policy, generated API contracts, and lazy module routes.

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL 16, APScheduler, React 18, TanStack Query, Vite/PWA, Vitest, Chrome MV3, Docker/Podman Compose.

## Global Constraints

- The app remains single-user, local-only, and bound to `127.0.0.1` by default.
- Production writes always use entity helpers and append events; the `event` table is never updated or deleted.
- Tests never connect to the `lifeos` database and must refuse a database name without a `_test` suffix.
- All user-day boundaries use configured `Europe/Istanbul`; UTC remains the storage/transport format for instants.
- Offline frontend behavior is read-only. Every POST, PUT, PATCH, DELETE, and upload is rejected before fetch.
- No new entity exception or source queue table is introduced.
- Every behavior change follows RED → GREEN → REFACTOR and receives a regression test.

---

### Task 1: Isolated Test Database

**Files:**
- Create: `compose.test.yaml`
- Create: `backend/app/core/test_guard.py`
- Modify: `backend/tests/conftest.py`
- Modify: `Makefile`
- Test: `backend/tests/test_test_guard.py`

**Interfaces:**
- Produces: `assert_safe_test_database(database_url: str) -> None`.
- Produces: `make test` backed by `forkos_test`, never the running `lifeos` database.

- [ ] Write tests proving `lifeos` and malformed URLs are rejected while `forkos_test` is accepted.
- [ ] Run `pytest tests/test_test_guard.py -q`; expect failures because the guard does not exist.
- [ ] Implement URL parsing with SQLAlchemy `make_url()` and require database name ending `_test`.
- [ ] Add a session-scoped schema migration fixture and per-test `TRUNCATE ... RESTART IDENTITY CASCADE` fixture in the isolated database.
- [ ] Add `test-db` and `backend-test` services in `compose.test.yaml`; expose no host DB port.
- [ ] Change `make test` to `$(CO) -f compose.yaml -f compose.test.yaml run --rm backend-test pytest -q`.
- [ ] Run the guard tests, then the full backend suite twice; expect deterministic passes and zero changes in the live DB event count.
- [ ] Commit as `test: isolate backend suite from personal database`.

### Task 2: Routine Review and Shared Local Time

**Files:**
- Create: `backend/app/core/time.py`
- Modify: `backend/app/modules/review/service.py`
- Modify: `backend/app/modules/review/schemas.py`
- Modify: `frontend/src/modules/review/ReviewPage.tsx`
- Modify: `frontend/src/core/types.ts`
- Test: `backend/tests/test_review.py`
- Test: `frontend/src/modules/review/ReviewPage.test.tsx`

**Interfaces:**
- Produces: `local_zone()`, `local_now()`, `local_today()`, `local_day_bounds(day)`, and `local_datetime(day, minute)`.
- Review returns recurring Todo completions and legacy Habit checks under the existing `habits` wire field for compatibility; UI labels it `Rutin`.

- [ ] Add a failing test with one `habit.checked`, one recurring `todo.completed`, and one normal Todo completion around Istanbul midnight.
- [ ] Verify the test fails because Review counts only legacy habits and UTC boundaries.
- [ ] Implement the shared time helpers and change Review aggregation to classify recurring Todo events from payload `recur` or the current Todo row.
- [ ] Add a failing frontend copy/render test for the `Rutin` label, then update the page.
- [ ] Run focused backend/frontend tests and commit as `fix: align reviews with routine todos`.

### Task 3: Istanbul Day-Boundary Migration

**Files:**
- Modify: `backend/app/modules/calendar/service.py`
- Modify: `backend/app/modules/rss/service.py`
- Modify: `backend/app/modules/bookmark/service.py`
- Modify: `backend/app/modules/pomodoro/service.py`
- Modify: `backend/app/modules/finance/router.py`
- Modify: `backend/app/modules/finance/service.py`
- Modify: `backend/app/modules/habit/service.py`
- Modify: `backend/app/modules/learning/service.py`
- Modify: `backend/app/modules/todo/service.py`
- Modify: `backend/app/worker/digest.py`
- Create: `frontend/src/lib/date.ts`
- Modify: `frontend/src/modules/review/ReviewPage.tsx`
- Modify: `frontend/src/modules/todo/WeeklyPlannerPage.tsx`
- Modify: `frontend/src/modules/activity/DayPage.tsx`
- Modify: `frontend/src/modules/finance/FinancePage.tsx`
- Test: `backend/tests/test_local_time.py`
- Test: `frontend/src/lib/date.test.ts`

**Interfaces:**
- `local_datetime(day, minute)` returns an Istanbul-aware datetime; callers convert to UTC only when an external API requires an instant.
- `localDateKey(date: Date) -> YYYY-MM-DD` uses browser-local calendar fields, not `toISOString()`.

- [ ] Write failing tests for 00:30 Istanbul day classification, a 09:00 plan slot Google payload, month rollover defaults, and browser-local date keys.
- [ ] Replace scattered `date.today()`, UTC-midnight, and `toISOString().slice(0, 10)` calendar-day logic with shared helpers.
- [ ] Ensure Google Calendar payload contains `+03:00` for local plan slots and external-event storage remains UTC-capable.
- [ ] Run focused tests plus `rg` to ensure no user-day UTC patterns remain; commit as `fix: centralize Istanbul calendar boundaries`.

### Task 4: Complete Backup and Restore Coverage

**Files:**
- Modify: `backend/app/modules/system/export.py`
- Modify: `backend/app/modules/system/restore.py`
- Modify: `backend/app/modules/system/backup.py`
- Create: `backend/tests/test_backup_restore.py`

**Interfaces:**
- Produces: `BACKUP_TABLES`, derived from metadata with an explicit denylist for `oauth_token` and documented transient tables.
- Restore order includes `saved_view`, `notification`, `source_sync_batch`, and `source_run` with FK-safe ordering.

- [ ] Write a failing coverage test asserting every metadata table is either backed up or explicitly denied.
- [ ] Write a failing round-trip test that seeds saved views, notifications, source batches/runs, tags, links, settings, and module entities in the isolated DB.
- [ ] Replace the hand-maintained incomplete export list with a metadata-checked table policy and extend restore order.
- [ ] Restore into a freshly truncated test DB and compare normalized rows while preserving append-only events.
- [ ] Run backup/restore and migration tests; commit as `fix: make backup coverage explicit and restorable`.

### Task 5: Durable Source Queue, Heartbeat, and Due Scheduling

**Files:**
- Modify: `backend/app/modules/opportunity/sync.py`
- Modify: `backend/app/modules/opportunity/router.py`
- Modify: `backend/app/modules/opportunity/worker.py`
- Modify: `backend/app/worker/jobs.py`
- Modify: `backend/app/worker/main.py`
- Modify: `backend/app/modules/system/router.py`
- Test: `backend/tests/test_source_sync.py`
- Create: `backend/tests/test_opportunity_scheduler.py`

**Interfaces:**
- Produces: `claim_pending_batch(session) -> SourceSyncBatch | None` using row locking.
- Produces: `pending_source_ids(session, batch) -> list[str]` from batch IDs minus terminal `source_run` rows.
- Produces: `reconcile_stale_runs(session, older_than) -> int` that marks stale operational runs as error, then leaves their source retryable.
- Produces: `consume_source_sync_batches(limit=4) -> int`, called by APScheduler every minute.
- System status includes a worker heartbeat timestamp written as a setting/event-safe operational value.

- [ ] Write failing tests proving an API refresh only queues work, a worker consumes it after an API restart, stale running rows recover, and counters are not doubled.
- [ ] Remove `asyncio.create_task()` and make both single/multi refresh endpoints return queued batch state.
- [ ] Add worker consumption, heartbeat, and stale-batch reconciliation jobs.
- [ ] Write failing due-scheduling tests using each adapter's `interval_minutes`; update automatic polling to select due sources, with concurrency four, rather than a fixed stale slice.
- [ ] Run sync/scheduler tests; commit as `fix: make source synchronization durable`.

### Task 6: Scraper Contract and Fixture Tests

**Files:**
- Create: `backend/tests/sources/fixtures/`
- Create: `backend/tests/sources/test_source_contract.py`
- Create: `backend/tests/sources/test_forkjob_parsers.py`
- Modify: `backend/pyproject.toml`
- Modify: selected files under `backend/app/sources/forkjob_core/` only when a fixture reveals a real defect.

**Interfaces:**
- Every enabled source must expose non-empty `id`, positive `interval_minutes`, and return normalized `SourceItem` values.
- Representative portal/ATS parsers run entirely against local HTML/JSON fixtures.

- [ ] Add failing catalog contract tests, including disabled-source exclusion from automatic runs.
- [ ] Add representative fixtures for at least one native announcement, one ATS, and the high-risk portal parser paths.
- [ ] Remove the blanket Ruff exclusion and replace it with only justified per-file rules.
- [ ] Fix surfaced parser/lint defects without network tests.
- [ ] Run source tests and Ruff; commit as `test: cover source adapters and parsers`.

### Task 7: CI, Dependency Security, and Reproducible Containers

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `backend/requirements.lock`
- Modify: `backend/pyproject.toml`
- Modify: `backend/Dockerfile`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/Dockerfile`
- Modify: `compose.yaml`
- Modify: `Makefile`

**Interfaces:**
- CI runs backend isolated tests/migrations/Ruff, frontend test/build/audit, and extension tests.
- Containers install exact frontend lock data with `npm ci` and exact backend constraints.

- [ ] Capture failing `npm audit` and repo-wide Ruff output as the RED evidence.
- [ ] Upgrade Vite/Vitest/PWA and compatible plugins to versions with no known audit findings; adjust tests/config only for documented breaking changes.
- [ ] Generate and commit a Python lock/constraints file; install it in the backend image.
- [ ] Add api/worker/web health checks and restart policies while retaining `127.0.0.1` defaults.
- [ ] Add CI and local `make verify`; run audit, Ruff, tests, and builds; commit as `build: add reproducible verified toolchain`.

### Task 8: Central Offline Mutation Policy

**Files:**
- Modify: `frontend/src/core/api.ts`
- Modify: `frontend/src/core/queryClient.ts`
- Modify: `frontend/src/core/ui.tsx`
- Modify: mutation-owning pages under `frontend/src/modules/`
- Create: `frontend/src/core/api.test.ts`
- Create: `frontend/src/core/mutationPolicy.test.tsx`

**Interfaces:**
- Produces: `OfflineWriteError` and `assertOnlineWrite()`; all write methods invoke it before `fetch`.
- TanStack MutationCache emits one Turkish error toast for unhandled errors; per-mutation handlers can override it through `meta.silentError`.

- [ ] Write failing API tests proving GET remains available offline while every write method and upload avoids `fetch`.
- [ ] Implement the central write guard.
- [ ] Write a failing MutationCache error-notification test and add the global toast bridge.
- [ ] Add `useOnline()` and disabled states to remaining visible write controls in Calendar, Finance, Learning, Study, Documents, Settings, Review, and source health pages.
- [ ] Run frontend tests and commit as `fix: enforce offline read-only mutations`.

### Task 9: Document Folder Provenance and Extension Runtime Configuration

**Files:**
- Create: `backend/alembic/versions/0020_document_folder_source.py`
- Modify: `backend/app/modules/document/models.py`
- Modify: `backend/app/modules/document/service.py`
- Create: `backend/tests/test_documents.py`
- Modify: `extension/manifest.json`
- Modify: `extension/config.js`
- Modify: `extension/outbox.js`
- Modify: `extension/popup/popup.html`
- Modify: `extension/popup/popup.js`
- Create: `extension/options/options.html`
- Create: `extension/options/options.js`
- Modify: `extension/tests/outbox.test.mjs`

**Interfaces:**
- `Document.folder_id` records Drive provenance; sync archives only records matching both category and folder.
- Extension config resolves `apiBase` from `chrome.storage.local`, defaulting to `http://127.0.0.1:8787/api`, validates HTTP(S), and requests optional origin permission.
- Popup exposes pending/failed counts with retry and clear controls.

- [ ] Add failing two-folder document sync test, then add reviewed migration and scoped archive query.
- [ ] Add failing extension tests for custom Podman VM origins, invalid schemes, failed queue listing, retry, and clear.
- [ ] Add MV3 options UI and optional host permissions without broad `<all_urls>` access.
- [ ] Run migration/document/extension tests; commit as `fix: preserve document and extension source provenance`.

### Task 10: Backend-Owned Today News Sources

**Files:**
- Create: `backend/app/sources/news.py`
- Modify: `backend/app/modules/system/news.py`
- Modify: `backend/app/modules/system/router.py`
- Modify: `frontend/src/modules/today/widgets/FeedStreamWidget.tsx`
- Create: `backend/tests/test_news_sources.py`
- Modify: `frontend/src/modules/today/TodayPage.test.tsx`

**Interfaces:**
- Produces `GET /api/news/hacker-news` and `GET /api/news/github-trending`.
- Both adapters implement `SourceAdapter`, record `source_run`, surface errors, and use a bounded in-process TTL cache; PWA caches successful GET responses for offline reading.

- [ ] Write failing adapter/router tests with local response fixtures and source-run assertions.
- [ ] Implement Hacker News and GitHub adapters with explicit timeouts/status checking.
- [ ] Replace browser cross-origin fetches with `api.get()` calls and visible error states.
- [ ] Add frontend registration/query tests; commit as `feat: route Today news through source health`.

### Task 11: Generated Contracts, Lazy Routes, and Frontend Decomposition

**Files:**
- Create: `frontend/scripts/generate-api.mjs`
- Create: `frontend/src/generated/api-schema.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/src/core/types.ts`
- Modify: `frontend/src/core/registry.ts`
- Modify: every `frontend/src/modules/*/index.ts`
- Split: `frontend/src/modules/rss/RssPage.tsx`
- Split: `frontend/src/modules/opportunity/OpportunityPage.tsx`
- Modify: `frontend/vite.config.ts`
- Create: `frontend/src/core/lazyRoutes.test.ts`

**Interfaces:**
- `npm run api:generate` reads a checked-in OpenAPI JSON snapshot produced by FastAPI and deterministically emits TypeScript interfaces.
- `ModuleSpec.routes[].element` remains a component type but modules register `lazy(() => import(...))` components, producing route chunks.
- RSS and Opportunity pages delegate state-independent panels/rows to focused components without changing URLs or mutation behavior.

- [ ] Write a failing schema freshness test and generate typed Today/Review/source-sync contracts first; alias existing high-risk handwritten types to generated names.
- [ ] Write a failing lazy-route build/test assertion, then convert module page imports to `React.lazy` with a shared Suspense fallback.
- [ ] Split RSS and Opportunity sections behind existing props, adding render tests before moving code.
- [ ] Add a build-size assertion that no application entry chunk exceeds 500 KB.
- [ ] Run frontend tests, typecheck, production build, and `git diff --check`; commit as `refactor: generate contracts and split frontend routes`.

### Task 12: Final Verification and Integration

**Files:**
- Modify: `README.md`
- Modify: `forkOS-PLAN.md`

- [ ] Update test, Windows/Podman extension, sync queue, backup, and timezone documentation.
- [ ] Run `make verify` from the isolated worktree with the isolated DB.
- [ ] Run frontend audit, production build, extension tests, repo-wide Ruff, migration chain, and `git diff --check` separately and read full outputs.
- [ ] Confirm main worktree and personal DB event count were untouched by the isolated verification.
- [ ] Review commits and diff, then use `finishing-a-development-branch` before offering merge/push options.

## Self-Review

- All selected items 1, 2, 3, 4, 5, 7, 8, 9, 10, 14, and 15 map to Tasks 1–11.
- Media and Learning/Study/Finance product completion remain explicitly out of scope except cross-cutting offline/time fixes.
- No placeholder implementation steps, new queue table, event mutation, or unreviewed migration is included.
- Generated names and shared helper signatures are used consistently by later tasks.
