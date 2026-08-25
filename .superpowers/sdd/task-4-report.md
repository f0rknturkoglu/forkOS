# Task 4 report — Today, plan, activity and query integrations

## Commit

- `e83d59c8af830269ee0e713ffc2274ca53a00890` — `Integrate media with Today and activity`

## RED evidence

### Backend

Command:

```bash
docker compose -p forkos-task4-red -f compose.yaml -f compose.test.yaml \
  run --build --rm backend-test \
  sh -c 'alembic upgrade head && pytest -q tests/test_media_today_integration.py'
```

Result: `4 failed` for the expected missing Task 4 behavior:

- planned media fell through as `kind=calendar`, `read_only=true`, with no media metadata/action;
- completed planned media was not in the completed bucket;
- `suggestions.media` did not exist;
- `media.consumed` was absent from contribution kinds.

### Frontend

Command:

```bash
npm test -- --run \
  src/core/mediaRouting.test.ts \
  src/modules/media/integrationKeys.test.ts \
  src/modules/today/TodayAgendaWidget.test.tsx \
  src/core/apiSchema.test.ts
```

Result: `6 failed` for the expected missing routes, scoped sync helpers, media refresh keys,
and planned-media Today link. A later focused RED also proved the default opportunity sync
query key would be split without an explicit compatibility helper:

```bash
npm test -- --run src/core/mediaRouting.test.ts
# 1 failed: sourceSyncQueryKey is not a function
```

## GREEN evidence

- Focused backend integration suite: `4 passed in 0.40s`.
- Focused frontend Task 4 suite: `4 files passed`, `8 tests passed`.
- Scoped/default routing regression: `src/core/mediaRouting.test.ts`, `3 passed`.
- Full backend Docker suite: `182 passed in 21.19s`.
- Full frontend Vitest: `21 files passed`, `45 tests passed`.
- `npm run api:check`: passed.
- `npm run build`: TypeScript, Vite production build, PWA generation and bundle check passed.
- `.venv/bin/ruff check app tests scripts`: passed.
- `.venv/bin/python -m compileall -q app tests scripts`: passed.
- `git diff --check`: passed before commit.

## Behavior and files

- `backend/app/modules/today/schemas.py`
  - Added `media` agenda kind and `log_media` action.
  - Added optional `media_kind`, `media_status`, `progress_label`, and `cover_url`.
  - Added typed `suggestions.media` collection.
- `backend/app/modules/today/service.py`
  - Resolves planned media before generic plan rows, preserving slot time/duration and preventing duplicates.
  - Uses local `/api/media/assets/...` cover when available, otherwise the remote cover.
  - Keeps completed planned media intelligible and excludes archived media.
  - Returns at most four non-archived `in_progress` items ordered by `entity.updated_at DESC, id DESC`.
  - Does not write plan rows while producing continuation data.
- `backend/app/core/contributions.py`
  - Counts only positive `media.consumed` payloads under `media` / `medya`.
  - Correction, release, sync, reopen, zero-consumption and unrelated events remain non-contributions.
  - Existing Istanbul day boundaries remain in both heatmap and day detail and are covered at local 00:30.
- Frontend routing/query integration
  - Global search and notifications route `media_item`, `media_unit`, and media notification kinds to media targets.
  - Source sync helpers preserve the old opportunity URL/query key and add explicit media scope URLs/keys.
  - `/sources?scope=media` shows media-scoped progress/history without opportunity controls.
  - Media mutations invalidate media dashboard and Today agenda data; Today refreshes media queries.
  - Planned media agenda rows link to their progress target and are not treated as todo completion.

## Scope and concerns

- No migration was added.
- The full responsive `Devam et` widget and media detail UI remain Task 5 work; Task 4 only exposes typed data and safe links.
- Checked-in generated OpenAPI files were intentionally not swept here because regenerating them also pulled in thousands of unrelated Task 2–3 contract lines. Runtime schemas and handwritten frontend Today types are integrated; the planned full schema regeneration remains Task 6.

---

## Review remediation (2026-08-23)

The concern above is superseded: the canonical OpenAPI snapshot and generated TypeScript
are now regenerated and committed together with the Task 2–4 media contracts.

### Commit

- `f22ed171f6bc1062fe1b46f7dd12e4d834cf5765` — `Harden media Today integration contracts`

### RED evidence

Backend command:

```bash
docker compose -p forkos-task4-review-red -f compose.yaml -f compose.test.yaml \
  run --build --rm backend-test \
  sh -c 'alembic upgrade head && pytest -q tests/test_media_today_integration.py'
```

Initial result: `4 failed, 7 passed`. Three failures represented the review gaps:

- dropped media was writable and still exposed `log_media`;
- large Decimal progress rendered as `1.23457e+09 / 1e+10`;
- a non-object JSON payload caused day detail to raise `AttributeError` while heatmap
  safely excluded it.

The fourth failure caught a test-fixture issue: positive progress deliberately transitions a
new `planned` item to `in_progress`. The fixture was corrected to use zero progress so the
planned-state assertion exercises a real persisted planned item.

Frontend command:

```bash
npm test -- --run \
  src/core/mediaRouting.test.ts \
  src/modules/media/MediaPageFocus.test.tsx \
  src/modules/opportunity/SourceHealthPageScope.test.tsx
```

Result: `4 failed, 2 passed`. The failures proved that media-unit links advertised an
unhandled query, the media list still assumed the retired array response, no detail lookup
opened a focused item outside the current page, and no scroll/focus receiver existed. The
media-scoped source status/history component test passed as a characterization of the
already-present scoped rendering.

### GREEN and full verification

- Focused backend Docker suite: `11 passed in 0.86s`.
- Focused frontend suite: `3 files passed`, `6 tests passed`.
- Full backend Docker suite: `189 passed in 19.73s`.
- Full frontend Vitest: `23 files passed`, `48 tests passed`.
- `npm run api:check`: passed; it now checks the FastAPI runtime export first and the
  generated TypeScript second.
- `npm run build`: TypeScript build, Vite/PWA production build, and bundle check passed.
- `.venv/bin/ruff check app tests scripts`: passed.
- `.venv/bin/python -m compileall -q app tests scripts`: passed.
- `git diff --check`: passed.

### Remediated behavior and files

- `backend/app/core/contributions.py`
  - Heatmap and day detail use the same PostgreSQL predicate: the payload must be a JSON
    object whose `amount` is a JSON number greater than zero.
  - Numeric strings, booleans, null, missing/scalar payloads, zero/negative values, and the
    feasible JSON `"NaN"` representation neither count nor raise.
  - The integration test compares both endpoints at Istanbul local 00:30, preserving the
    existing timezone boundary behavior.
- `backend/app/modules/today/service.py`
  - Decimal progress is formatted directly in fixed-point notation without a float roundtrip.
  - Planned, in-progress, and paused sessions expose `log_media`; completed and dropped
    sessions are read-only with no action.
  - Continuation media remains available when `today.auto_suggestions=false`: it describes
    current in-progress state, not an auto-generated recommendation, although the additive
    compatibility contract remains under `suggestions.media`.
- `frontend/src/modules/media/MediaPage.tsx`
  - Consumes the canonical paginated media response.
  - `?focus=<media_item_id>` fetches detail when necessary, inserts the item into the current
    view, opens its editor, centers its row, and moves keyboard focus to its title control.
- `frontend/src/core/GlobalSearch.tsx` and `NotificationPanel.tsx`
  - Media items keep the working focus route; unresolved media-unit targets now fall back to
    the safe general media route.
- `frontend/src/modules/opportunity/SourceHealthPageScope.test.tsx`
  - Covers media-scoped status/history endpoints and media-only component rendering.
- `backend/openapi.json`, `frontend/src/generated/api-schema.ts`, and `frontend/src/core/types.ts`
  - Canonical runtime and generated contracts include Task 2–4 media APIs and Today fields.
  - Handwritten media/Today kind-action field masks were removed in favor of generated types.
- `backend/scripts/export_openapi.py`, `frontend/scripts/check-api.mjs`, `frontend/package.json`,
  and `.github/workflows/ci.yml`
  - `npm run api:check` can no longer pass merely because a stale OpenAPI/TypeScript pair is
    internally consistent; CI installs the backend runtime needed for that check.

### Scope and concerns

- No migration was added.
- No Task 5 visual rewrite was started; this change only makes the current MediaPage a real
  receiver for existing Task 4 links.
- The generated-contract diff is intentionally large because it captures the previously
  deferred Task 2/3 media API surface as required by the review.

---

## Task 4 — Full verification and runtime check (2026-08-25)

### Verification commands and results

1. Command: `cd frontend && npm test`

   Result: PASS — `27 passed | 1 skipped` test files; `64 passed | 9 skipped` tests. The
   pre-existing Task 5 media contract remains skipped.

2. Command: `cd frontend && node scripts/generate-api.mjs --check && npm run build`

   Result: PASS — API schema check exited 0; TypeScript, Vite production build, PWA
   generation, and bundle check all exited 0 (`1704 modules transformed`).

3. Command: `git diff --check && git status --short`

   Result: PASS — no whitespace errors. Status output contains only the pre-existing
   ` M .superpowers/sdd/task-3-report.md` change.

4. Runtime commands:

   ```bash
   docker compose restart web
   docker compose ps web
   curl -fsS http://127.0.0.1:5173/ | grep '<title>forkOS</title>'
   ```

   Results: restart exited 0 (`forkos-web-1` started); the immediate status was `Up 2
   seconds (health: starting)`; curl exited 0 and matched `    <title>forkOS</title>`. A
   fresh `docker compose ps web` after five seconds reported `Up 18 seconds (healthy)` on
   `127.0.0.1:5173->5173/tcp`.

### Commit and working-tree interpretation

No verification adjustment was required, so no commit was created (`commit: none`). HEAD
remains `c73dbf6 feat: collapse settings source health logs`; the only working-tree change
is the pre-existing `.superpowers/sdd/task-3-report.md`, which was preserved and not
modified by this task.

### Concerns

None. The web container briefly reported `health: starting` immediately after restart, then
became `healthy`; the live curl check succeeded during that startup window.
