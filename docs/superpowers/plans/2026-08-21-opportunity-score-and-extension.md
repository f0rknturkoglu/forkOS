# Opportunity Score and Capture Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show only numeric opportunity scores, make extension capture loss-safe, and install the unpacked extension in Brave Nightly.

**Architecture:** The opportunity API keeps extracting the numeric score while the frontend removes all reason rendering. The extension serializes storage mutations, runs one flush at a time, preserves captures added during network activity, and stores permanent backend rejections separately from the retry queue.

**Tech Stack:** FastAPI/Pydantic, React/TypeScript/Vite, Chrome Manifest V3, JavaScript ES modules, Node.js built-in test runner, Docker Compose/OrbStack.

## Global Constraints

- Preserve unrelated opportunity, source-picker, and notification changes already in the dirty working tree.
- Render numeric score and score band only; never render `score_reasons`.
- Every capture is written to `chrome.storage.local` before network delivery.
- Only HTTP(S) URLs are accepted.
- Do not report a backend rejection as a successful save.
- Use Brave Nightly for the local unpacked installation.

---

### Task 1: Simplify opportunity score presentation

**Files:**
- Modify: `frontend/src/modules/opportunity/OpportunityDetail.tsx`
- Modify: `frontend/src/modules/opportunity/labels.ts`
- Verify: `backend/app/modules/opportunity/service.py`

**Interfaces:**
- Consumes: `Opportunity.score: number | null` from `/api/opportunities` and `/api/opportunities/{id}`.
- Produces: `scoreBand(score: number | null): ScoreBand | null` for card/detail badges.

- [ ] **Step 1: Run the current build and preserve the failing output**

Run: `docker compose exec -T web npm run build`

Expected: FAIL with TypeScript `TS1117` for the duplicate `earning` key in `labels.ts`.

- [ ] **Step 2: Remove score-reason rendering and helpers**

Remove `scoreParts` from the `OpportunityDetail.tsx` import and delete the `parts` calculation and breakdown `<dl>`. Keep the score number, `/ 100`, score band, and progress bar.

Delete `REASON_LABELS`, `ScorePart`, `DELTA_KEYS`, `DETAIL_SKIP`, `DETAIL_WORDS`, `detailWord`, and `scoreParts` from `labels.ts`. Keep only score-band constants and helpers.

- [ ] **Step 3: Verify the detail API and frontend build**

Run:

```bash
curl --fail --silent http://127.0.0.1:8787/api/opportunities/$(docker compose exec -T db psql -U lifeos -d lifeos -Atc "select id from opportunity limit 1")
docker compose exec -T web npm run build
```

Expected: API JSON contains numeric `score`; build exits 0.

---

### Task 2: Add failing extension reliability tests

**Files:**
- Create: `extension/package.json`
- Create: `extension/tests/outbox.test.mjs`
- Test: `extension/tests/outbox.test.mjs`

**Interfaces:**
- Consumes: `enqueue(item)` and `flush()` from `extension/outbox.js`.
- Produces: regression coverage for concurrent enqueue, invalid URLs, and backend `4xx` rejection.

- [ ] **Step 1: Add the Node test entry point**

```json
{
  "private": true,
  "type": "module",
  "scripts": { "test": "node --test tests/*.test.mjs" }
}
```

- [ ] **Step 2: Write three behavior tests**

Use an in-memory `chrome.storage.local` implementation and real imports of `outbox.js`:

```js
test("preserves an item enqueued while a flush is awaiting the backend", async () => {
  // Pause the first fetch, enqueue a second URL, finish the older flush,
  // then assert the second client_uuid remains in storage.
});

test("rejects non-http URLs without enqueueing or fetching", async () => {
  const result = await enqueue({ url: "chrome://extensions" });
  assert.equal(result.rejected.length, 1);
  assert.equal(fetchCalls, 0);
});

test("moves backend 4xx responses to failed captures", async () => {
  // Return 422 and assert outbox is empty, failedCaptures has the item,
  // sent is zero, and rejected contains the status.
});
```

- [ ] **Step 3: Run tests to verify RED**

Run: `cd extension && npm test`

Expected: all three tests fail against the current queue implementation for the described behavior.

---

### Task 3: Make the extension queue loss-safe

**Files:**
- Modify: `extension/outbox.js`
- Modify: `extension/popup/popup.js`
- Modify: `extension/background.js`
- Modify: `extension/manifest.json`
- Test: `extension/tests/outbox.test.mjs`

**Interfaces:**
- Produces: `enqueue(item): Promise<FlushResult>` and `flush(): Promise<FlushResult>` where `FlushResult` contains `sent`, `pending`, `duplicates`, and `rejected`.
- Storage keys: `outbox`, `failedCaptures`, and `lastResult`.

- [ ] **Step 1: Serialize queue mutations**

Add an in-memory promise chain:

```js
let storageOperation = Promise.resolve();

function withStorageLock(operation) {
  const run = storageOperation.then(operation, operation);
  storageOperation = run.catch(() => {});
  return run;
}
```

Use it for enqueue writes, flush snapshots, and final filtering of the current queue by finalized `client_uuid` values.

- [ ] **Step 2: Make flush single-flight and preserve rejected records**

Use one `activeFlush` promise. Successful IDs are removed from the current queue. `4xx` items are appended to `failedCaptures` with status/time and removed from retryable outbox; network/`5xx` items remain pending.

- [ ] **Step 3: Validate URL schemes and surface rejection**

Before enqueueing, parse `item.url` and accept only `http:` and `https:`. Return a `rejected` entry for invalid schemes without calling `fetch`.

In the popup, display `Kaydedilemedi: yalnızca http(s) sayfaları destekleniyor` or the backend rejection and re-enable the save button. In keyboard/context-menu flows, show a red `!` badge.

- [ ] **Step 4: Remove unused permission**

Delete `scripting` from `manifest.json`; retain `storage`, `alarms`, `contextMenus`, `activeTab`, and the localhost host permission.

- [ ] **Step 5: Run tests to verify GREEN**

Run:

```bash
cd extension && npm test
node --check outbox.js
node --check background.js
node --check popup/popup.js
```

Expected: all extension tests pass and every syntax check exits 0.

---

### Task 4: Regression verification

**Files:**
- Verify: `backend/tests/test_api.py`
- Verify: `frontend/src/modules/opportunity/*`
- Verify: `extension/*`

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
docker compose exec -T api pytest -q \
  tests/test_api.py::test_capture_is_idempotent \
  tests/test_api.py::test_move_between_collections_logs_event \
  tests/test_api.py::test_tags_and_search
```

Expected: `3 passed`.

- [ ] **Step 2: Run frontend build and extension tests**

Run:

```bash
docker compose exec -T web npm run build
cd extension && npm test
```

Expected: Vite build exits 0 and extension tests pass.

---

### Task 5: Install and acceptance-test in Brave Nightly

**Files:**
- Modify local-only: `.env`
- Load unpacked: `extension/`

- [ ] **Step 1: Load the extension**

Open `brave://extensions`, enable Developer mode, choose **Load unpacked**, and select `/Users/furkanturkoglu/Downloads/forkOS/extension`.

- [ ] **Step 2: Configure the extension origin**

Copy the displayed extension ID into `.env` as `EXTENSION_ID=<id>`, then run:

```bash
docker compose up -d --force-recreate api
```

Expected: API returns healthy after recreation.

- [ ] **Step 3: Perform a disposable end-to-end capture**

Open an HTTP(S) page, save it through the popup, verify it appears in `/api/bookmarks`, then delete only that disposable bookmark through its API ID.

- [ ] **Step 4: Confirm final state**

Run `docker compose ps`, `curl --fail http://127.0.0.1:8787/health`, frontend build, and extension tests once more.

