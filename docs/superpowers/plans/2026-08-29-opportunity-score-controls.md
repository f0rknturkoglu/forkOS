# Opportunity Score Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add job-only score range filtering and explicit ascending/descending score sorting to the opportunity workspace.

**Architecture:** Extend the existing paginated browse contract; keep score extraction in the backend query layer and filter against `opportunity.raw.forkjob.score` without schema changes. Carry optional bounds in frontend browse state and render a focused score-control section using existing design-system primitives.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, PostgreSQL JSONB, React 18, TypeScript, TanStack Query, Vitest, pytest.

## Global Constraints

- Score controls apply only to `section=jobs`; announcements and trash do not send score bounds.
- Score bounds are inclusive and limited to `-1..100`.
- An active score range excludes rows whose score is null or non-numeric.
- `score` remains the backward-compatible descending sort; `score_asc` is ascending. Null scores remain last in both directions.
- Use `NumberInput`, `Select`, `FilterChip`, and design tokens; do not introduce raw form elements or fixed color/size values.
- Keep stable pagination tie-breakers after every score sort.

---

### Task 1: Backend score browse contract

**Files:**
- Modify: `backend/tests/test_opportunity_browse.py`
- Modify: `backend/app/modules/opportunity/browse.py`
- Modify: `backend/app/modules/opportunity/router.py`

**Interfaces:**
- Consumes: `BrowseFilters`, `_conditions()`, `_order()` and `GET /api/opportunities/browse`.
- Produces: `BrowseFilters.min_score: float | None`, `BrowseFilters.max_score: float | None`, and accepted sort value `score_asc`.

- [ ] **Step 1: Write failing backend integration tests**

Add a helper that creates entity-backed jobs with `raw={"forkjob": {"score": score}}`, then assert:

```python
response = await client.get(
    "/api/opportunities/browse",
    params={"section": "jobs", "search": marker, "min_score": 40, "max_score": 80},
)
assert [item["score"] for item in response.json()["items"]] == [80, 40]

ascending = await client.get(
    "/api/opportunities/browse",
    params={"section": "jobs", "search": marker, "sort": "score_asc"},
)
assert [item["score"] for item in ascending.json()["items"]] == [20, 40, 80, None]

invalid = await client.get(
    "/api/opportunities/browse",
    params={"section": "jobs", "min_score": 80, "max_score": 40},
)
assert invalid.status_code == 422
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `cd backend && pytest -q tests/test_opportunity_browse.py`

Expected: FAIL because `min_score`, `max_score`, and `score_asc` are not implemented.

- [ ] **Step 3: Implement the minimal backend behavior**

Define one reusable score expression and apply inclusive bounds:

```python
def _score_expression():
    return cast(Opportunity.raw["forkjob"]["score"].astext, Float)

if filters.min_score is not None:
    conditions.append(_score_expression() >= filters.min_score)
if filters.max_score is not None:
    conditions.append(_score_expression() <= filters.max_score)
```

Extend `_order()` so `score_asc` uses `asc().nulls_last()`. Add FastAPI query validation for `-1..100`; reject `min_score > max_score` with `HTTPException(422, "Minimum skor maksimum skordan büyük olamaz")`.

- [ ] **Step 4: Run the focused backend tests and verify GREEN**

Run: `cd backend && pytest -q tests/test_opportunity_browse.py`

Expected: PASS.

- [ ] **Step 5: Commit backend behavior**

```bash
git add backend/tests/test_opportunity_browse.py backend/app/modules/opportunity/browse.py backend/app/modules/opportunity/router.py
git commit -m "feat(opportunity): filter and sort jobs by score"
```

### Task 2: Frontend browse state and query contract

**Files:**
- Modify: `frontend/src/modules/opportunity/OpportunityFilters.test.tsx`
- Modify: `frontend/src/modules/opportunity/opportunityBrowse.ts`

**Interfaces:**
- Consumes: backend query parameters `min_score`, `max_score`, and sort `score_asc`.
- Produces: optional numeric fields on `OpportunityBrowseFilters` and job-only query serialization.

- [ ] **Step 1: Write failing frontend contract tests**

Extend the jobs fixture with `min_score: 40` and `max_score: 80`, then assert:

```typescript
expect(browseQuery(filters)).toContain("min_score=40");
expect(browseQuery(filters)).toContain("max_score=80");
const announcements = switchOpportunitySection(filters, "announcements");
expect(browseQuery(announcements)).not.toContain("min_score=");
expect(announcements.min_score).toBeUndefined();
expect(announcements.max_score).toBeUndefined();
```

- [ ] **Step 2: Run the frontend test and verify RED**

Run: `cd frontend && npm test -- src/modules/opportunity/OpportunityFilters.test.tsx`

Expected: FAIL because score bounds are absent from the type/query.

- [ ] **Step 3: Implement the minimal state/query changes**

Add `score_asc` to `OpportunitySort`; add optional `min_score` and `max_score`; serialize them only when `section === "jobs"`; clear them in non-job section transitions.

- [ ] **Step 4: Run the focused frontend test and verify GREEN**

Run: `cd frontend && npm test -- src/modules/opportunity/OpportunityFilters.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit the frontend contract**

```bash
git add frontend/src/modules/opportunity/OpportunityFilters.test.tsx frontend/src/modules/opportunity/opportunityBrowse.ts
git commit -m "feat(opportunity): carry score range filters"
```

### Task 3: Score filter controls and explicit sorting UI

**Files:**
- Modify: `frontend/src/modules/opportunity/OpportunityFilters.test.tsx`
- Modify: `frontend/src/modules/opportunity/OpportunityFilters.tsx`
- Modify: `frontend/src/modules/opportunity/OpportunityPage.tsx`

**Interfaces:**
- Consumes: `OpportunityBrowseFilters.min_score`, `.max_score`, `.sort`.
- Produces: job-only `Uyum skoru` controls, score presets, exact bounds, and clear score-sort labels.

- [ ] **Step 1: Write failing rendering and interaction tests**

Assert that jobs render `Uyum skoru`, `Minimum skor`, `Maksimum skor`, `70–100`, and both score sort labels; announcements render none of the score controls. Add an interaction test that clicks `70–100` and observes `onChange` with `{min_score: 70, max_score: 100, offset: 0}`.

- [ ] **Step 2: Run the tests and verify RED**

Run: `cd frontend && npm test -- src/modules/opportunity/OpportunityFilters.test.tsx`

Expected: FAIL because the controls do not exist.

- [ ] **Step 3: Implement the score section**

Use `FilterChip` for the four presets and two `NumberInput` controls for exact bounds. Empty inputs map to `undefined`; clamp non-empty values to `-1..100`; if one bound crosses the other, move the opposite bound to preserve a valid range. Add a small score-only reset button when either bound is active.

Rename score sorting copy to `Skor: yüksekten düşüğe` and add `Skor: düşükten yükseğe`. Update the empty-state active-filter check in `OpportunityPage.tsx` so score-only filtering offers `Süzgeci temizle`.

- [ ] **Step 4: Run focused frontend tests and verify GREEN**

Run: `cd frontend && npm test -- src/modules/opportunity/OpportunityFilters.test.tsx src/modules/opportunity/OpportunityPage.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit the UI**

```bash
git add frontend/src/modules/opportunity/OpportunityFilters.test.tsx frontend/src/modules/opportunity/OpportunityFilters.tsx frontend/src/modules/opportunity/OpportunityPage.tsx
git commit -m "feat(opportunity): add score range controls"
```

### Task 4: Contract regeneration and full verification

**Files:**
- Modify: `frontend/src/generated/api-schema.ts`

**Interfaces:**
- Consumes: completed backend OpenAPI contract and frontend implementation.
- Produces: synchronized generated API types and verified release state.

- [ ] **Step 1: Regenerate the API schema**

Run: `cd frontend && npm run api:generate`

Expected: generated browse operation includes `min_score`, `max_score`, and `score_asc` acceptance through the string sort field.

- [ ] **Step 2: Run full backend verification**

Run: `cd backend && pytest -q && uv run ruff check app tests scripts`

Expected: all tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 3: Run full frontend verification**

Run: `cd frontend && npm test && npm run build && npm run api:check && npm run format:check && node scripts/check-endpoint-coverage.mjs`

Expected: all tests/build/checks pass; endpoint coverage remains within its threshold.

- [ ] **Step 4: Verify repository integrity and commit generated contract**

```bash
git diff --check
git add frontend/src/generated/api-schema.ts
git commit -m "chore: refresh opportunity score API contract"
```

- [ ] **Step 5: Push the verified main branch**

```bash
git fetch origin main
git rev-list --left-right --count origin/main...main
git push origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
```

Expected: no remote-only commits before push and local/remote hashes match afterward.

