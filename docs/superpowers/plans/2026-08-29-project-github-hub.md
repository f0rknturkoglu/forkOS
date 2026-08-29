# Project GitHub Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the empty-first project GitHub tabs with a balanced, chronological activity hub that reports real fetch freshness and keeps issue-to-todo state visible.

**Architecture:** Extend the existing cached REST overview with `fetched_at`, then enrich open issues with persisted todo matches in the project service/router without adding schema. In React, normalize issues, pull requests, and commits into one presentation model, filter that model client-side, and keep manual refresh separate from the three-hour worker event sync.

**Tech Stack:** FastAPI, SQLAlchemy async, httpx, PostgreSQL 16, React 18, TypeScript, TanStack Query, Tailwind CSS 3, Vitest, Testing Library, pytest.

## Global Constraints

- Preserve the existing `entity`, `event`, and `link` schemas; no migration is allowed.
- Every issue-to-todo write continues through the existing entity helpers and `invalidateAfter("project.write")` flow.
- `event` remains append-only.
- Use existing semantic design tokens and shared UI components; no raw hex colors, arbitrary pixel text sizes, or raw form controls.
- Do not expose the GitHub token in responses, logs, tests, or frontend state beyond the existing password input.
- Manual refresh updates the live panel only; it must not claim to run the three-hour worker event sync.
- Do not add a new frontend dependency or design system.

---

### Task 1: Make repository fetch freshness explicit

**Files:**
- Modify: `backend/app/modules/project/github_repo.py`
- Create: `backend/tests/test_project_github_repo.py`

**Interfaces:**
- Consumes: `github_repo.overview(repo: str, token: str | None, *, refresh: bool = False) -> dict`.
- Produces: the same dictionary with `fetched_at: str`, an ISO-8601 UTC timestamp that stays unchanged for cache hits and changes after a forced refresh.

- [ ] **Step 1: Write failing cache freshness tests**

Create a deterministic fake `httpx.AsyncClient` that returns repository metadata, no issues, no pull requests, and one commit. Patch `github_repo.httpx.AsyncClient` and `github_repo.datetime`/clock as needed, clear `github_repo._cache`, then assert:

```python
first = await github_repo.overview("owner/repo", "secret")
cached = await github_repo.overview("owner/repo", "secret")
refreshed = await github_repo.overview("owner/repo", "secret", refresh=True)

assert first["fetched_at"] == cached["fetched_at"]
assert refreshed["fetched_at"] != first["fetched_at"]
assert "secret" not in repr(first)
```

Also assert that the fake client receives `Authorization: Bearer secret` while the returned dictionary does not contain an access-token field.

- [ ] **Step 2: Run the tests and verify red**

Run:

```bash
cd backend
pytest -q tests/test_project_github_repo.py
```

Expected: failure because `fetched_at` is absent.

- [ ] **Step 3: Add `fetched_at` to the cached payload**

Import `UTC` and `datetime`. Build `fetched_at` only after successful GitHub responses and before storing `_Entry`:

```python
data = {
    # existing public fields
    "fetched_at": datetime.now(UTC).isoformat(),
    "authenticated": bool(token),
}
_cache[key] = _Entry(at=now, data=data)
```

Keep cache hits returning the existing payload. Remove the duplicated `authenticated` key if present.

- [ ] **Step 4: Run focused backend tests**

Run:

```bash
cd backend
pytest -q tests/test_project_github_repo.py
ruff check app/modules/project/github_repo.py tests/test_project_github_repo.py
```

Expected: all tests and lint pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add backend/app/modules/project/github_repo.py backend/tests/test_project_github_repo.py
git commit -m "feat(github): expose repository fetch freshness"
```

### Task 2: Persistently mark GitHub issues already converted to todos

**Files:**
- Modify: `backend/app/modules/project/service.py`
- Modify: `backend/app/modules/project/router.py`
- Create: `backend/tests/test_project_github.py`

**Interfaces:**
- Produces: `github_issue_todo_ids(session, project, issue_numbers) -> dict[int, uuid.UUID]`.
- Extends each item in `GET /api/projects/{project_id}/github` `issues` with `todo_id: UUID | null`.
- Preserves: `POST /api/projects/{project_id}/github/issues` idempotency.

- [ ] **Step 1: Write failing issue mapping tests**

Use the Postgres-backed ASGI client. Create a project with `github_repo="owner/repo"`, create one todo with the existing marker title `owner/repo#17 Fix sync`, and link it to the project. Patch `router.github_repo.overview` to return issues `#17` and `#18`. Assert:

```python
response = await client.get(f"/api/projects/{project_id}/github")
issues = {item["number"]: item for item in response.json()["issues"]}
assert issues[17]["todo_id"] == todo_id
assert issues[18]["todo_id"] is None
```

Keep a regression assertion that posting issue `#17` returns `duplicate: true` and does not create another todo.

- [ ] **Step 2: Run the test and verify red**

Run:

```bash
docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm backend-test sh -c 'alembic upgrade head && pytest -q tests/test_project_github.py'
```

Expected: failure because `todo_id` is absent.

- [ ] **Step 3: Implement one-query issue matching**

Add a service helper that returns early for no repo/no numbers, fetches todo entities whose titles begin with `f"{project.github_repo}#"` in one query, and matches only exact `owner/repo#number ` prefixes:

```python
async def github_issue_todo_ids(
    session: AsyncSession,
    project: Project,
    issue_numbers: Collection[int],
) -> dict[int, uuid.UUID]:
    numbers = set(issue_numbers)
    if not project.github_repo or not numbers:
        return {}
    rows = await session.execute(
        select(Entity.id, Entity.title).where(
            Entity.type == Todo.ENTITY_TYPE,
            Entity.title.startswith(f"{project.github_repo}#"),
        )
    )
    return {
        number: entity_id
        for entity_id, title in rows
        for number in numbers
        if title.startswith(f"{project.github_repo}#{number} ")
    }
```

Enrich the overview in the router after the GitHub request succeeds. Do not mutate the globally cached dictionary in place; return copied issue dictionaries:

```python
todo_ids = await service.github_issue_todo_ids(
    session, project, [item["number"] for item in panel["issues"]]
)
return {
    **panel,
    "issues": [
        {**item, "todo_id": todo_ids.get(item["number"])}
        for item in panel["issues"]
    ],
}
```

- [ ] **Step 4: Run focused backend tests**

Run the Task 2 test plus existing project journal/API tests. Expected: all pass and duplicate conversion remains idempotent.

- [ ] **Step 5: Commit Task 2**

```bash
git add backend/app/modules/project/service.py backend/app/modules/project/router.py backend/tests/test_project_github.py
git commit -m "feat(github): expose converted issue state"
```

### Task 3: Build the balanced chronological GitHub activity hub

**Files:**
- Modify: `frontend/src/core/types.ts`
- Modify: `frontend/src/modules/projects/GithubPanel.tsx`
- Create: `frontend/src/modules/projects/GithubPanel.test.tsx`

**Interfaces:**
- Extends `GithubIssue` with `todo_id: string | null`.
- Extends `GithubRepoPanel` with `fetched_at: string`.
- Produces a pure `githubActivities(data: GithubRepoPanel): GithubActivity[]` helper and `GithubActivityFilter = "all" | "issue" | "pull" | "commit"`.

- [ ] **Step 1: Write failing activity and interaction tests**

Mock `api.get`, `api.post`, `useOnline`, TanStack Query, and `invalidateAfter`. Use a fixture containing an older issue, a newer PR, and the newest commit. Assert:

```tsx
expect(screen.getByText("Newest commit")).toBeTruthy();
expect(screen.getByText("Open pull request")).toBeTruthy();
expect(screen.getByText("Older issue")).toBeTruthy();
expect(screen.getAllByTestId("github-activity-row").map((row) => row.textContent)).toEqual([
  expect.stringContaining("Newest commit"),
  expect.stringContaining("Open pull request"),
  expect.stringContaining("Older issue"),
]);
```

Add tests that:

- `Tümü` is initially pressed;
- selecting `Commit` hides issues and PRs;
- issue-free data still renders commits initially;
- a converted issue renders `Görevlerde`;
- clicking an unconverted issue calls the existing POST endpoint;
- the create action remains visible without hover-specific assertions.

- [ ] **Step 2: Run the frontend test and verify red**

Run:

```bash
cd frontend
npm test -- --run src/modules/projects/GithubPanel.test.tsx
```

Expected: failure because the unified activity model and new labels do not exist.

- [ ] **Step 3: Implement types and pure activity normalization**

Create a discriminated presentation type in `GithubPanel.tsx` with a stable key, kind, title, URL, timestamp, metadata, and source payload. Normalize all three arrays and sort invalid/missing dates last. Keep GitHub domain data in `core/types.ts`; do not add a global route/type constant.

- [ ] **Step 4: Replace the tabs with the approved layout**

Use existing `Section`, `Button`, `Chip`, `MetricStrip`, `Metric`, `RowList`, `Empty`, and token classes:

- responsive repo identity header with private/public and branch chips;
- explicit `GitHub'da aç` link;
- four-cell metric strip for issue count, PR count, last push, and language;
- filter toolbar with counts and `aria-pressed`;
- one chronological row list;
- always-visible issue action;
- row-local pending state via `toTodo.variables === issue.number`;
- `Görevlerde` state when `todo_id` exists.

Do not render stars/forks/watchers in the primary summary.

- [ ] **Step 5: Run and format the focused frontend test**

```bash
cd frontend
npx prettier --write src/core/types.ts src/modules/projects/GithubPanel.tsx src/modules/projects/GithubPanel.test.tsx
npm test -- --run src/modules/projects/GithubPanel.test.tsx
```

Expected: all new component tests pass.

- [ ] **Step 6: Commit Task 3**

```bash
git add frontend/src/core/types.ts frontend/src/modules/projects/GithubPanel.tsx frontend/src/modules/projects/GithubPanel.test.tsx
git commit -m "feat(github): add unified project activity hub"
```

### Task 4: Add truthful refresh and actionable panel states

**Files:**
- Modify: `frontend/src/modules/projects/GithubPanel.tsx`
- Modify: `frontend/src/modules/projects/GithubPanel.test.tsx`

**Interfaces:**
- Manual refresh calls `/projects/{id}/github?refresh=true`.
- Produces a pure `githubPanelError(error: unknown) -> { title: string; detail: string; settings: boolean }` helper.

- [ ] **Step 1: Add failing refresh, error, offline, and loading tests**

Assert that manual refresh calls the forced URL, presents `GitHub'dan … alındı` from `fetched_at`, and disables refresh while offline. Parameterize error fixtures containing `GitHub 401`, `GitHub 403: API rate limit exceeded`, `GitHub 403: Resource not accessible`, `GitHub 404`, and network timeout text. Assert user-facing Turkish copy and absence of raw JSON/error strings.

Add loading assertions for structure-shaped placeholders and verify stale data remains visible when a refresh mutation fails.

- [ ] **Step 2: Run focused tests and verify red**

Run the GitHub panel test. Expected: refresh URL and classified-state assertions fail.

- [ ] **Step 3: Implement real refresh and state presentation**

Use a dedicated TanStack mutation for `?refresh=true`. Render `refresh.data ?? query.data` so successful forced data appears immediately; call the normal query refetch after success so the canonical cache key catches up without another external GitHub request. Show refresh errors as a non-blocking inline banner while retaining previous data.

Classify lower-cased `ApiError.message` content into token, rate-limit, permission, not-found, and network cases. Token/permission cases include an `#/settings` link. Never print the raw response body.

Use short token-based skeleton blocks for initial loading. Offline mode retains cached content and disables write/refresh controls with explanatory text.

- [ ] **Step 4: Run focused and adjacent frontend tests**

```bash
cd frontend
npm test -- --run src/modules/projects/GithubPanel.test.tsx src/modules/projects/ProjectTodos.test.tsx src/modules/projects/ProjectJournal.test.tsx
npm run build
```

Expected: tests and build pass.

- [ ] **Step 5: Commit Task 4**

```bash
git add frontend/src/modules/projects/GithubPanel.tsx frontend/src/modules/projects/GithubPanel.test.tsx
git commit -m "fix(github): make refresh and errors actionable"
```

### Task 5: Regenerate contracts and verify the whole repository

**Files:**
- Modify: `backend/openapi.json` if export changes it
- Modify: `frontend/src/generated/api-schema.ts` if generation changes it
- Verify: all changed files

**Interfaces:**
- Produces a clean repository with synchronized API contracts and all checks passing.

- [ ] **Step 1: Export and regenerate API contracts**

Run the repository's documented OpenAPI export and frontend generation commands. If the dynamic endpoint has no response model and produces no schema diff, leave generated files untouched.

- [ ] **Step 2: Run full backend verification**

```bash
docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm backend-test sh -c 'alembic upgrade head && pytest -q'
docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm --no-deps backend-test ruff check app tests scripts
```

Expected: all backend tests and lint pass.

- [ ] **Step 3: Run full frontend verification**

```bash
cd frontend
npm test
npm run build
npm run api:check
node scripts/check-endpoint-coverage.mjs
npm run format:check
```

Expected: all tests pass, production build succeeds, API contract is current, endpoint coverage remains under the allowed threshold, and formatting is clean.

- [ ] **Step 4: Run repository hygiene checks**

```bash
git diff --check
git status --short
```

Expected: no whitespace errors and only intended generated/source/test files are modified.

- [ ] **Step 5: Commit generated or final verification changes**

```bash
git add backend/openapi.json frontend/src/generated/api-schema.ts
git commit -m "chore: refresh GitHub hub API contracts"
```

Skip this commit when neither generated file changed.
