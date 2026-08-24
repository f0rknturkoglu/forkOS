# Cinematic Media Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a large-poster media library with one global library/provider search, canonical source chips, type-aware external links, append-only progress actions, and compact sync health.

**Architecture:** Preserve the existing single-kind provider endpoint and add a typed fault-tolerant global endpoint. Split the monolithic media frontend into shared pure helpers, search, poster-grid, detail/progress, menu, and sync-summary units, then let `MediaPage` compose them. All progress writes use consumption commands with a fresh `client_uuid`; library metadata edits remain PATCH operations.

**Tech Stack:** FastAPI, Pydantic, asyncio, React 18, TypeScript, TanStack React Query, native HTML disclosure/menu semantics, Vitest, Testing Library, Tailwind CSS.

## Global Constraints

- Keep forkOS local-only; add no auth, tenant, telemetry, or remote analytics.
- Preserve offline read-only behavior: reads remain available and every write control is disabled offline.
- Keep the existing `GET /media/search?kind=...` contract working.
- Global provider search starts only for a trimmed query of at least two characters.
- A single provider failure must not hide successful global-search results.
- Every catalog result carries `kind`, `provider`, `provider_id`, and `provider_ids`.
- Provider-created media sends `source: "provider"` plus canonical identity fields at the top level.
- Every progress write uses `POST /media/{id}/consumptions` with a fresh `client_uuid`; never PATCH `progress` or PATCH `status: "completed"`.
- Use local cached artwork before remote artwork, then fall back to a neutral 2:3 initial placeholder.
- Color is not the only source/status signal; chips always contain text.
- Use existing Newsreader, IBM Plex Sans, design tokens, Lucide dependency, and UI primitives; add no frontend package.
- No gradients, heavy shadows, large pill containers, or persistent visible external-link rows.
- Preserve the two pre-existing `.superpowers/sdd/task-3-report.md` and `task-4-report.md` working-tree edits; never stage or revert them.
- Write and observe each failing test before production code.

---

## File Map

- Modify `backend/app/modules/media/schemas.py`: typed global search result/warning response.
- Modify `backend/app/modules/media/service.py`: shared result conversion and fault-tolerant parallel search.
- Modify `backend/app/modules/media/router.py`: `GET /media/search/global`.
- Create `backend/tests/test_media_global_search.py`: backend contract and compatibility tests.
- Regenerate `backend/openapi.json` and `frontend/src/generated/api-schema.ts`.
- Modify `frontend/src/core/types.ts`: aliases for generated global search/provider types.
- Modify `frontend/src/modules/media/shared.tsx`: cover resolution, source identity/color, external-link mapping.
- Create `frontend/src/modules/media/MediaActionsMenu.tsx`: accessible ellipsis menu.
- Create `frontend/src/modules/media/MediaSearchComposer.tsx`: merged library/catalog search and provider create flow.
- Create `frontend/src/modules/media/MediaPosterGrid.tsx`: responsive 2:3 cards and compact library controls.
- Create `frontend/src/modules/media/MediaProgressActions.tsx`: quick/set/finish commands.
- Create `frontend/src/modules/media/MediaDetailPage.tsx`: focused detail experience.
- Create `frontend/src/modules/media/MediaSyncSummary.tsx`: compact sync/provider disclosure.
- Rewrite `frontend/src/modules/media/MediaPage.tsx`: composition only.
- Modify `frontend/src/modules/media/index.ts`: add `/media/:id` route before `/media` fallback registration.
- Add focused tests next to every created frontend unit.
- Create `frontend/src/modules/media/MediaCinematicPage.test.tsx`: end-to-end page contract.

### Task 1: Fault-Tolerant Global Provider Search

**Files:**
- Modify: `backend/app/modules/media/schemas.py`
- Modify: `backend/app/modules/media/service.py`
- Modify: `backend/app/modules/media/router.py`
- Create: `backend/tests/test_media_global_search.py`
- Modify generated: `backend/openapi.json`
- Modify generated: `frontend/src/generated/api-schema.ts`
- Modify: `frontend/src/core/types.ts`

**Interfaces:**
- Produces `MetadataResult.kind: str`.
- Produces `MetadataSearchWarning { provider: str; kind: str; message: str }`.
- Produces `GlobalMetadataSearchOut { results: list[MetadataResult]; warnings: list[MetadataSearchWarning] }`.
- Produces `service.search_all_metadata(session, q) -> GlobalMetadataSearchOut`.
- Produces `GET /media/search/global?q=<term>`.

- [ ] **Step 1: Write failing backend tests**

Create fake providers and a fake registry in `backend/tests/test_media_global_search.py`:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.media import service
from app.modules.media.providers.base import ProviderResult


class FakeRegistry:
    kinds = ("movie", "book", "game")

    def __init__(self):
        self.movie = SimpleNamespace(
            id="tmdb", ready=True, missing_settings=(),
            search=AsyncMock(return_value=[ProviderResult(
                provider="tmdb", provider_id="movie:1", title="Dune"
            )]),
        )
        self.book = SimpleNamespace(
            id="openlibrary", ready=True, missing_settings=(),
            search=AsyncMock(side_effect=RuntimeError("upstream unavailable")),
        )
        self.game = SimpleNamespace(
            id="igdb", ready=False,
            missing_settings=("media.igdb_client_id",),
            search=AsyncMock(),
        )

    def for_kind(self, kind):
        return getattr(self, kind)


@pytest.mark.no_database
async def test_global_search_keeps_successes_and_reports_partial_failures(monkeypatch):
    registry = FakeRegistry()
    monkeypatch.setattr(service, "provider_registry", AsyncMock(return_value=registry))
    result = await service.search_all_metadata(SimpleNamespace(), "dune")
    assert [(row.kind, row.provider, row.provider_id) for row in result.results] == [
        ("movie", "tmdb", "movie:1")
    ]
    assert {(row.kind, row.provider) for row in result.warnings} == {
        ("book", "openlibrary"), ("game", "igdb")
    }
    registry.game.search.assert_not_awaited()


@pytest.mark.no_database
async def test_single_kind_search_still_returns_kind(monkeypatch):
    registry = FakeRegistry()
    monkeypatch.setattr(service, "provider_registry", AsyncMock(return_value=registry))
    rows = await service.search_metadata(SimpleNamespace(), "dune", "movie")
    assert rows[0].kind == "movie"
```

Add a duplicate fixture where the same `(kind, provider, provider_id)` appears twice and assert only one result remains.

- [ ] **Step 2: Verify RED**

Run: `cd backend && .venv/bin/pytest -q tests/test_media_global_search.py`

Expected: collection or execution fails because `search_all_metadata`, `MetadataResult.kind`, and the new response types do not exist.

- [ ] **Step 3: Implement schemas and service**

In `schemas.py` add:

```python
class MetadataResult(BaseModel):
    kind: str
    # keep every existing field unchanged below


class MetadataSearchWarning(BaseModel):
    provider: str
    kind: str
    message: str


class GlobalMetadataSearchOut(BaseModel):
    results: list[MetadataResult]
    warnings: list[MetadataSearchWarning]
```

In `service.py`, extract the existing conversion into:

```python
def _metadata_result(row: ProviderResult, kind: str) -> MetadataResult:
    return MetadataResult(
        kind=kind,
        provider=row.provider,
        provider_id=row.provider_id,
        title=row.title,
        subtitle=row.subtitle,
        year=row.year,
        summary=row.summary,
        total=row.total,
        progress_measure=row.progress_measure,
        cover=row.cover_url,
        backdrop=row.backdrop_url,
        cover_url=row.cover_url,
        backdrop_url=row.backdrop_url,
        provider_ids=row.provider_ids,
        meta=row.meta,
        metadata={
            **row.meta,
            "provider": row.provider,
            "provider_id": row.provider_id,
            "provider_ids": row.provider_ids,
        },
    )
```

Keep `search_metadata()` behavior, but map with `_metadata_result(row, kind)`. Add an `asyncio.gather` global search that skips calls to unready providers, converts exceptions into warnings, and deduplicates by `(kind, provider, provider_id)` while preserving registry-kind order.

- [ ] **Step 4: Add the route and regenerate contracts**

Register this route before the existing `/media/search` declaration:

```python
@router.get("/media/search/global", response_model=GlobalMetadataSearchOut)
async def search_all_metadata(
    q: str = Query(min_length=2),
    session: AsyncSession = Depends(get_session),
):
    return await service.search_all_metadata(session, q)
```

Import `GlobalMetadataSearchOut`. Run:

```bash
cd frontend
npm run api:generate
```

Then add generated aliases in `frontend/src/core/types.ts`:

```ts
export type GlobalMetadataSearch = ApiSchemas["GlobalMetadataSearchOut"];
export type MediaProviderStatus = ApiSchemas["MediaProviderStatusOut"];
```

- [ ] **Step 5: Verify GREEN and compatibility**

Run:

```bash
cd backend
.venv/bin/pytest -q tests/test_media_global_search.py tests/test_media_providers.py
cd ../frontend
npm run api:check
npm run build
```

Expected: focused backend tests pass, generated contracts are current, and frontend build exits 0.

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/media/schemas.py backend/app/modules/media/service.py backend/app/modules/media/router.py backend/tests/test_media_global_search.py backend/openapi.json frontend/src/generated/api-schema.ts frontend/src/core/types.ts
git commit -m "feat(media): add global provider search"
```

### Task 2: Shared Media Identity, Artwork, and External Menu

**Files:**
- Modify: `frontend/src/modules/media/shared.tsx`
- Modify: `frontend/src/modules/media/MediaPage.test.tsx`
- Modify: `frontend/src/index.css`
- Create: `frontend/src/modules/media/MediaActionsMenu.tsx`
- Create: `frontend/src/modules/media/MediaActionsMenu.test.tsx`

**Interfaces:**
- Produces `mediaCoverUrl(item): string | null`.
- Produces `mediaProvider(item): string | null`.
- Produces `providerChip(provider): string`.
- Preserves `externalLinks(kind, title, meta, provider?, providerId?, providerIds?)`.
- Produces `<MediaActionsMenu item={item} onTrash={fn} disabled={boolean} />`.

- [ ] **Step 1: Write failing pure-helper tests**

Extend `MediaPage.test.tsx` with assertions:

```tsx
expect(mediaCoverUrl({ cover_path: "abc.webp", cover_url: "https://remote" })).toBe(
  "/api/media/assets/abc.webp",
);
expect(mediaProvider({ provider: "musicbrainz", meta: { source: "itunes" } })).toBe(
  "musicbrainz",
);
expect(providerChip("musicbrainz")).toContain("--src-musicbrainz");
expect(externalLinks("music", "Closer", {}, "musicbrainz", "release-1", {}))
  .toEqual(expect.arrayContaining([
    ["MusicBrainz", "https://musicbrainz.org/release-group/release-1"],
    ["Apple Music", "https://music.apple.com/us/search?term=Closer"],
    ["RateYourMusic", "https://rateyourmusic.com/search?searchterm=Closer"],
  ]));
```

Add table-driven assertions for movie/show, anime/manga, book, audiobook, podcast, and game, ensuring unrelated services never appear.

- [ ] **Step 2: Write failing menu interaction tests**

In `MediaActionsMenu.test.tsx`, render a movie, click `Dune işlemleri`, assert the menu contains TMDB/IMDb/Rotten Tomatoes/Letterboxd, press Escape, assert it closes and focus returns to the trigger. Reopen and fire a pointer event on `document.body`; assert it closes. Assert `Çöpe taşı` is disabled when `disabled` is true.

- [ ] **Step 3: Verify RED**

Run:

```bash
cd frontend
npm test -- --run src/modules/media/MediaPage.test.tsx src/modules/media/MediaActionsMenu.test.tsx
```

Expected: imports/functions/menu fail because the new contracts do not exist.

- [ ] **Step 4: Implement helpers and color tokens**

Implement local-artwork normalization without accepting traversal:

```ts
export function mediaCoverUrl(item: Pick<MediaItem, "cover_path" | "cover_url" | "meta">): string | null {
  const name = item.cover_path?.split("/").pop();
  if (name && /^[a-f0-9]{64}\.(?:jpg|jpeg|png|webp)$/i.test(name)) {
    return `/api/media/assets/${encodeURIComponent(name)}`;
  }
  return item.cover_url ?? (String(item.meta?.cover_url ?? "") || null);
}

export function mediaProvider(item: Pick<MediaItem, "provider" | "meta">): string | null {
  return item.provider ?? (typeof item.meta?.source === "string" ? item.meta.source : null);
}
```

Extend source tokens/maps for `google_books`, `musicbrainz`, and `igdb`; retain every existing token. Extend `externalLinks` with canonical IDs when available and search URLs otherwise. Use `RateYourMusic` as the visible name; keep `srcColor` aliases backward compatible with `RyM`.

- [ ] **Step 5: Implement accessible menu**

`MediaActionsMenu` owns one boolean and trigger ref. It uses a button with `aria-haspopup="menu"`, `aria-expanded`, and `aria-label={`${item.title} işlemleri`}`. Attach document `keydown` and `pointerdown` listeners only while open, restore focus on Escape, and render links plus a separated trash button. Do not render external links outside the open menu.

- [ ] **Step 6: Verify GREEN and commit**

Run:

```bash
cd frontend
npm test -- --run src/modules/media/MediaPage.test.tsx src/modules/media/MediaActionsMenu.test.tsx
npm run build
```

Expected: helper/menu tests and build pass.

```bash
git add frontend/src/modules/media/shared.tsx frontend/src/modules/media/MediaPage.test.tsx frontend/src/modules/media/MediaActionsMenu.tsx frontend/src/modules/media/MediaActionsMenu.test.tsx frontend/src/index.css
git commit -m "feat(media): add source-aware media actions"
```

### Task 3: Unified Search Composer

**Files:**
- Create: `frontend/src/modules/media/MediaSearchComposer.tsx`
- Create: `frontend/src/modules/media/MediaSearchComposer.test.tsx`

**Interfaces:**
- Consumes `GlobalMetadataSearch`, `MediaPage`, `MetadataResult`, `mediaCoverUrl`, `providerChip`.
- Produces `providerCreateBody(hit: MetadataResult): Record<string, unknown>`.
- Produces `<MediaSearchComposer online={boolean} onAdded={() => void} />`.

- [ ] **Step 1: Write failing tests**

Use a `QueryClientProvider`, stub `fetch`, and fake timers. Assert:

```tsx
await user.type(screen.getByRole("searchbox", { name: "Tüm medyada ara" }), "dune");
await vi.advanceTimersByTimeAsync(250);
await screen.findByRole("heading", { name: "Kütüphanende" });
await screen.findByRole("heading", { name: "Katalog sonuçları" });
const headings = screen.getAllByRole("heading", { level: 3 });
expect(headings.map((node) => node.textContent)).toEqual(["Dune: Prophecy", "Dune"]);
```

Assert no `/media/search/global` call for one character. Assert a catalog result renders its kind and provider text. Click `Dune kütüphaneye ekle` and inspect the POST body:

```ts
expect(body).toMatchObject({
  source: "provider",
  title: "Dune",
  kind: "movie",
  provider: "tmdb",
  provider_id: "movie:99",
  provider_ids: { tmdb: "99" },
  cover_url: "https://image/dune.jpg",
});
```

Return 409 on a second add and assert `Kütüphanede aç` links to `#/media/<existing-id>`.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && npm test -- --run src/modules/media/MediaSearchComposer.test.tsx`

Expected: module import fails.

- [ ] **Step 3: Implement body conversion and composer**

`providerCreateBody` returns every canonical top-level identity/artwork/progress field plus `meta: hit.meta`. `MediaSearchComposer` uses `useDebounced(search.trim(), 250)`, queries `/media?q=...&limit=8` and `/media/search/global?q=...` in parallel, and enables both only at length >= 2. Render one centered input; do not render a kind select. Keep library results first. Render warnings as one muted line and show a Settings media-links route when all providers are unavailable.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
cd frontend
npm test -- --run src/modules/media/MediaSearchComposer.test.tsx
npm run build
```

Expected: search tests and build pass.

```bash
git add frontend/src/modules/media/MediaSearchComposer.tsx frontend/src/modules/media/MediaSearchComposer.test.tsx
git commit -m "feat(media): add unified media search"
```

### Task 4: Large Poster Library and Compact Metrics

**Files:**
- Create: `frontend/src/modules/media/MediaPosterGrid.tsx`
- Create: `frontend/src/modules/media/MediaPosterGrid.test.tsx`
- Modify: `frontend/src/modules/media/shared.tsx`

**Interfaces:**
- Produces `<MediaMetrics stats={stats} />`.
- Produces `<MediaLibraryControls kind status onKindChange onStatusChange />`.
- Produces `<MediaPosterGrid items online onQuick onTrash />`.
- Poster cards use `/media/${item.id}` via hash navigation and `data-media-poster`.

- [ ] **Step 1: Write failing responsive/card tests**

Render two items and assert:

```tsx
expect(container.querySelector("[data-media-grid]")?.className).toContain("auto-fill");
expect(container.querySelectorAll("[data-media-poster]")).toHaveLength(2);
expect(screen.getByRole("img", { name: "Dune kapağı" }).className).toContain("aspect-[2/3]");
expect(screen.getByText("TMDB")).toBeTruthy();
expect(screen.getByText("Film")).toBeTruthy();
expect(screen.getByRole("button", { name: "Dune ilerlemesini bir artır" })).toBeTruthy();
```

Assert a completed item has no `+1`; zero-cover item shows its initial. Assert metrics render in one compact grid and filter chips do not appear inside the global composer.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && npm test -- --run src/modules/media/MediaPosterGrid.test.tsx`

Expected: module import fails.

- [ ] **Step 3: Implement poster units**

Use a grid class equivalent to:

```tsx
<ul
  data-media-grid
  className="grid grid-cols-[repeat(auto-fill,minmax(156px,1fr))] gap-x-4 gap-y-6 sm:grid-cols-[repeat(auto-fill,minmax(176px,1fr))]"
>
```

The image/fallback occupies `aspect-[2/3] w-full`. Keep title and chips below the poster, render a 1px progress track, quick button only for progress-capable non-completed items, and the actions menu in the poster's top-right corner. Cards have a 1px subtle border at most and no heavy shadow.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
cd frontend
npm test -- --run src/modules/media/MediaPosterGrid.test.tsx src/modules/media/MediaPage.test.tsx
npm run build
```

Expected: poster/helper tests and build pass.

```bash
git add frontend/src/modules/media/MediaPosterGrid.tsx frontend/src/modules/media/MediaPosterGrid.test.tsx frontend/src/modules/media/shared.tsx
git commit -m "feat(media): render cinematic poster library"
```

### Task 5: Append-Only Progress and Media Detail

**Files:**
- Create: `frontend/src/modules/media/MediaProgressActions.tsx`
- Create: `frontend/src/modules/media/MediaProgressActions.test.tsx`
- Create: `frontend/src/modules/media/MediaDetailPage.tsx`
- Create: `frontend/src/modules/media/MediaDetailPage.test.tsx`
- Modify: `frontend/src/modules/media/index.ts`

**Interfaces:**
- Produces `consumptionBody(action, item, value?): MediaConsumptionIn` with a fresh UUID.
- Produces `<MediaProgressActions item online compact? onChanged />`.
- Produces `<MediaDetailPage />`, reading `route.params.get("id")`.
- Registers `/media/:id` before `/media`.

- [ ] **Step 1: Write failing command tests**

Stub `crypto.randomUUID` with unique values and assert quick/set/finish requests:

```ts
expect(posts.map((post) => post.body.action)).toEqual(["quick", "set", "finish"]);
expect(posts[0].body).toMatchObject({ amount: 1, measure: "episode" });
expect(posts[1].body).toMatchObject({ progress_after: 5, measure: "episode" });
expect(new Set(posts.map((post) => post.body.client_uuid)).size).toBe(3);
expect(patches.some((body) => "progress" in body || body.status === "completed")).toBe(false);
```

Assert all action buttons are disabled offline.

- [ ] **Step 2: Write failing detail tests**

Render `#/media/media-1`, return a `MediaDetailOut`, and assert the page shows large cover, heading, readable status/progress, exact progress form, finish action, score, notes, and source actions. Submit a score/note edit and assert PATCH contains only metadata fields, never progress/completed status.

- [ ] **Step 3: Verify RED**

Run:

```bash
cd frontend
npm test -- --run src/modules/media/MediaProgressActions.test.tsx src/modules/media/MediaDetailPage.test.tsx
```

Expected: modules/routes do not exist.

- [ ] **Step 4: Implement progress and detail**

Quick body uses `{ action: "quick", amount: 1, measure: item.progress_measure ?? "item" }`; set uses `{ action: "set", progress_after: value, measure }`; finish uses `{ action: "finish", measure }`. Every factory call invokes `crypto.randomUUID()`.

The detail page queries `/media/{id}`, renders a two-column poster/content layout on desktop and one column on mobile, keeps forms collapsed/compact until invoked, and invalidates `media`, `media-detail`, `media-stats`, `media-dashboard`, `today-agenda`, and `activity` after mutations.

Register:

```ts
const MediaDetailPage = lazy(() => import("./MediaDetailPage").then((module) => ({ default: module.MediaDetailPage })));

routes: [
  { path: "/media/:id", element: MediaDetailPage },
  { path: "/media", element: MediaPage },
]
```

- [ ] **Step 5: Verify GREEN and commit**

Run:

```bash
cd frontend
npm test -- --run src/modules/media/MediaProgressActions.test.tsx src/modules/media/MediaDetailPage.test.tsx src/core/mediaRouting.test.ts
npm run build
```

Expected: focused tests and build pass.

```bash
git add frontend/src/modules/media/MediaProgressActions.tsx frontend/src/modules/media/MediaProgressActions.test.tsx frontend/src/modules/media/MediaDetailPage.tsx frontend/src/modules/media/MediaDetailPage.test.tsx frontend/src/modules/media/index.ts
git commit -m "feat(media): add append-only progress detail"
```

### Task 6: Compact Media Sync Health

**Files:**
- Create: `frontend/src/modules/media/MediaSyncSummary.tsx`
- Create: `frontend/src/modules/media/MediaSyncSummary.test.tsx`

**Interfaces:**
- Consumes `MediaProviderStatus`, `/media/providers`, `/media/sync`, existing `SyncProgress scope="media"`.
- Produces `<MediaSyncSummary online={boolean} />` with `details[data-media-sync]`.

- [ ] **Step 1: Write failing tests**

Return six providers (five ready/healthy and one error), render the component, and assert closed summary text `6 kaynak`, `5 sağlıklı`, and relative last-run time. Open `Kaynak ayrıntıları` and assert provider rows show name, kinds, textual status, last error, and missing setting. Click `Şimdi tara`, assert `POST /media/sync`, and assert it is disabled offline.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && npm test -- --run src/modules/media/MediaSyncSummary.test.tsx`

Expected: module import fails.

- [ ] **Step 3: Implement minimal disclosure**

Use a controlled native `<details data-media-sync>`. Summary layout is one quiet bordered row; warnings use text plus tone, never color only. Healthy means `ready && last_status !== "error"`; surface `empty` separately as `boş`. Keep `SyncProgress scope="media" compact` inside the opened body. `Şimdi tara` queues all providers and invalidates `media-providers`, `source-sync`, and `media`.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
cd frontend
npm test -- --run src/modules/media/MediaSyncSummary.test.tsx
npm run build
```

Expected: sync tests and build pass.

```bash
git add frontend/src/modules/media/MediaSyncSummary.tsx frontend/src/modules/media/MediaSyncSummary.test.tsx
git commit -m "feat(media): add compact sync health"
```

### Task 7: Compose the Cinematic Media Page

**Files:**
- Rewrite: `frontend/src/modules/media/MediaPage.tsx`
- Create: `frontend/src/modules/media/MediaCinematicPage.test.tsx`
- Modify: `frontend/src/modules/media/MediaPageFocus.test.tsx`

**Interfaces:**
- Consumes Tasks 2–6 components.
- Preserves `receiveMediaFocus` export for current global-search/notification routing tests.
- Produces the final `/media` layout.

- [ ] **Step 1: Write the failing page contract**

Mock the live API surface and assert:

```tsx
expect(screen.getByRole("heading", { name: "Medya" })).toBeTruthy();
expect(screen.getByRole("searchbox", { name: "Tüm medyada ara" })).toBeTruthy();
expect(screen.queryByRole("combobox", { name: "Arama türü" })).toBeNull();
expect(container.querySelectorAll("[data-media-poster]")).toHaveLength(4);
expect(container.querySelector("details[data-media-sync]")?.hasAttribute("open")).toBe(false);
expect(screen.getByText("Toplam").closest("[data-media-metrics]")).toBeTruthy();
```

Type a query and assert library hits precede catalog hits. Open a card menu and assert type-specific links. Click quick progress and assert a consumption POST. Verify the old inline `MediaEditor`, visible link row, and small `RowList` are absent.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && npm test -- --run src/modules/media/MediaCinematicPage.test.tsx`

Expected: the existing page still renders category-selected search and small rows.

- [ ] **Step 3: Rewrite composition**

`MediaPage` keeps URL-independent library kind/status filters in local state, requests `/media` with those filters, and renders this sequence:

```tsx
<PageFrame className="space-y-6">
  <PageHeader eyebrow="Takip" title="Medya" />
  <MediaMetrics stats={stats} />
  <MediaSearchComposer online={online} onAdded={refresh} />
  <MediaLibraryControls ... />
  <MediaPosterGrid items={items} online={online} onQuick={...} onTrash={...} />
  <MediaSyncSummary online={online} />
</PageFrame>
```

Remove duplicate `Cover`, constants, external-link mapping, quick sites, `MediaEditor`, kind-selected provider search, and inline external links from `MediaPage.tsx`. Preserve `?focus=` compatibility by navigating it to `/media/:id` or retaining the tested `receiveMediaFocus` fallback without reintroducing inline editing.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
cd frontend
npm test -- --run src/modules/media/MediaCinematicPage.test.tsx src/modules/media/MediaPageFocus.test.tsx src/modules/media/MediaFrontend.test.tsx
npm run build
```

Expected: active cinematic/focus tests pass, pre-existing broader skipped Task 5 contract remains explicitly skipped, and build exits 0.

```bash
git add frontend/src/modules/media/MediaPage.tsx frontend/src/modules/media/MediaCinematicPage.test.tsx frontend/src/modules/media/MediaPageFocus.test.tsx
git commit -m "feat(media): compose cinematic library page"
```

### Task 8: Full Regression and Live Verification

**Files:**
- Modify only Task 1–7 files if verification exposes a regression.

**Interfaces:**
- Consumes all previous tasks.
- Produces a verified local forkOS runtime.

- [ ] **Step 1: Run full backend verification**

Run:

```bash
docker compose -p forkos-media-final -f compose.yaml -f compose.test.yaml \
  run --rm --build backend-test sh -c 'alembic upgrade head && pytest -q'
```

Expected: all backend tests pass; no migration is added.

- [ ] **Step 2: Run frontend contracts and build**

Run:

```bash
cd frontend
npm test
npm run api:check
npm run build
```

Expected: every active test passes, the deliberately out-of-scope legacy Task 5 block remains skipped, API snapshots are current, and bundle check passes.

- [ ] **Step 3: Check formatting and working tree**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only intended product files plus the preserved pre-existing `.superpowers/sdd/task-3-report.md` and `task-4-report.md` modifications appear.

- [ ] **Step 4: Restart and verify runtime**

Run:

```bash
docker compose up -d --build api worker web
docker compose ps
curl -fsS http://127.0.0.1:8787/api/media/search/global?q=dune >/tmp/forkos-media-search.json
curl -fsS http://127.0.0.1:5173/ | grep '<title>forkOS</title>'
```

Expected: db/api/worker/web are healthy; global search returns JSON even with provider warnings; web serves forkOS.

- [ ] **Step 5: Browser acceptance**

At `http://127.0.0.1:5173/#/media`, verify:

- four compact metrics and one centered global search;
- no search-kind dropdown;
- large 2:3 posters at desktop and narrow viewport;
- readable source/kind chips;
- external links only after opening the ellipsis menu;
- `+1` updates progress and detail remains consistent;
- sync summary starts closed and expands without page clutter;
- offline mode leaves reads visible and disables writes.

- [ ] **Step 6: Commit only verification fixes**

If verification required product changes, commit only those scoped files:

```bash
git add backend/app/modules/media frontend/src/modules/media frontend/src/core/types.ts frontend/src/generated/api-schema.ts backend/openapi.json
git commit -m "fix(media): finalize cinematic library"
```

If no fix was required, do not create an empty commit.
