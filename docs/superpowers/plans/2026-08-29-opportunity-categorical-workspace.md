# Fırsatlar Kategorik Çalışma Alanı Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** İş ilanlarını iş ailesine göre kategorize eden; YLSY/ÖSYM duyurularını gerçek yayın tarihleriyle ayıran; responsive liste/grid sunan; sayfalanmış ve kaynak hatalarına dayanıklı bir Fırsatlar çalışma alanı oluşturmak.

**Architecture:** `opportunity` tablosuna sorgulanabilir `category` ve `published_at` alanları eklenir. Yeni `browse.py` birimi SQL filtreleme, facet sayaçları ve sayfalama sorumluluğunu taşır; mevcut CRUD servisi entity/event kurallarını korur. Frontend iki bağlamsal çalışma alanına ayrılır ve server-side browse sözleşmesini kullanır. Kaynak ingest'i duplicate kümeleri deterministik birleştirir; sağlık özeti yetim RSS koşularını dışlar; canlı doğrulanan adapter sözleşmeleri güncellenir.

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL 16, Alembic, httpx, selectolax, React 18, TypeScript, TanStack Query, Tailwind CSS 3, Vitest, Testing Library, pytest.

## Global Constraints

- `opportunity.id` mevcut `entity.id` FK ilişkisini korur; yeni entity istisnası eklenmez.
- Entity yazmaları `app/core/entity.py` yardımcılarıyla yapılır.
- `event` append-only kalır; UPDATE/DELETE yapılmaz.
- Migration elle yazılır ve her SQL komutu ayrı `op.execute()` çağrısında olur.
- Türkçe arama `simple` + `immutable_unaccent()` düzenini korur.
- Mutation sonrası frontend yenilemesi yalnızca `invalidateAfter()` ile yapılır.
- Renk, boyut ve radius mevcut tasarım tokenları ve ortak UI bileşenlerinden gelir.
- Yeni frontend veya backend bağımlılığı eklenmez.
- Harici LLM veya kullanıcı verisini dışarı gönderen servis eklenmez.
- Bilinmeyen YLSY/ÖSYM son tarihi tahmin edilmez.
- Çalışmayan kaynaklar başarılı gibi raporlanmaz.

---

### Task 1: Kalıcı kategori ve yayın tarihi alanları

**Files:**
- Create: `backend/alembic/versions/0030_opportunity_category_dates.py`
- Create: `backend/app/modules/opportunity/taxonomy.py`
- Modify: `backend/app/modules/opportunity/models.py`
- Modify: `backend/app/modules/opportunity/schemas.py`
- Modify: `backend/app/modules/opportunity/service.py`
- Modify: `backend/app/modules/opportunity/worker.py`
- Create: `backend/tests/test_opportunity_taxonomy.py`
- Modify: `backend/tests/test_migrations.py`

**Interfaces:**
- Produces: `classify_job(title: str, department: str | None, description: str | None = None) -> str`.
- Produces: `parse_turkish_heading_date(title: str) -> datetime | None`.
- Extends `Opportunity`/`OpportunityOut` with `category: str | None` and `published_at: datetime | None`.

- [ ] **Step 1: Write failing taxonomy and Turkish date tests**

```python
@pytest.mark.parametrize(
    ("title", "department", "expected"),
    [
        ("Senior Backend Engineer", "Engineering", "software"),
        ("MLOps Engineer", "Data Scientist", "data-ai"),
        ("Product Designer", "Product", "product-design"),
        ("Cloud Security Specialist", "Security", "cloud-security"),
        ("Financial Operations Analyst", "Finance", "business-ops"),
        ("B2B Sales Manager", "Sales", "sales-marketing"),
        ("Veteriner Hekim", None, "other"),
    ],
)
def test_classify_job(title, department, expected):
    assert classify_job(title, department) == expected

def test_parse_turkish_heading_date():
    assert parse_turkish_heading_date(
        "26 Ağustos 2026 2026-MEB-AGS: Sınav Sonuçları Açıklandı"
    ).isoformat() == "2026-08-26T00:00:00+00:00"
```

- [ ] **Step 2: Run tests and verify red**

Run: `cd backend && pytest -q tests/test_opportunity_taxonomy.py`

Expected: import failure because `taxonomy.py` does not exist.

- [ ] **Step 3: Implement ordered, normalized taxonomy helpers**

```python
CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("data-ai", ("machine learning", "data scientist", "data engineer", "ai engineer", "mlops", "yapay zeka")),
    ("cloud-security", ("devops", "sre", "platform engineer", "cloud", "cyber", "security", "guvenlik")),
    ("product-design", ("product manager", "product designer", "ux", "ui designer", "product owner")),
    ("software", ("software", "developer", "engineer", "backend", "frontend", "full stack", "mobile", "qa", "tester", "yazilim", "bilisim")),
    ("sales-marketing", ("sales", "marketing", "account manager", "business development", "satis", "pazarlama")),
    ("business-ops", ("operations", "finance", "legal", "people", "human resources", "analyst", "customer support", "operasyon", "finans")),
)

def classify_job(title: str, department: str | None, description: str | None = None) -> str:
    haystack = normalize_text(" ".join(filter(None, (title, department, description))))
    return next((slug for slug, needles in CATEGORY_RULES if any(n in haystack for n in needles)), "other")
```

Use a 12-item Turkish month map and return UTC midnight only when the heading starts with `day month year`.

- [ ] **Step 4: Create a manual Alembic migration**

Upgrade uses separate calls:

```python
op.execute("ALTER TABLE opportunity ADD COLUMN category text")
op.execute("ALTER TABLE opportunity ADD COLUMN published_at timestamptz")
op.execute("CREATE INDEX opportunity_category_idx ON opportunity (category) WHERE category IS NOT NULL")
op.execute("CREATE INDEX opportunity_published_at_idx ON opportunity (published_at DESC) WHERE published_at IS NOT NULL")
```

Backfill valid JSON ISO publication dates, YLSY dates, OSYM Turkish heading dates, and job categories with separate `op.execute()` calls. The OSYM statement joins `entity`, maps all twelve Turkish month names in a `CASE`, and only runs for titles matching `^[0-9]{1,2} [[:alpha:]ÇĞİÖŞÜçğıöşü]+ [0-9]{4} `.

Downgrade drops both indexes and columns in four separate calls.

- [ ] **Step 5: Wire fields into model, schemas and ingestion**

`NativeJob` exposes `published_at`; `ingest_jobs()` assigns:

```python
published_at = getattr(job, "published_at", None)
department = (job.to_row().get("forkjob") or job.to_row()).get("department")
category = classify_job(job.title, department, job.description) if job.kind == "job" else None
```

Existing rows update missing `category`/`published_at` during successful source refresh. `_out()` returns the two fields.

- [ ] **Step 6: Verify migration and focused tests**

Run:

```bash
docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm backend-test sh -c 'alembic upgrade head && pytest -q tests/test_migrations.py tests/test_opportunity_taxonomy.py'
```

Expected: all pass; migration multi-statement guard remains green.

- [ ] **Step 7: Commit Task 1**

```bash
git add backend/alembic/versions backend/app/modules/opportunity backend/tests/test_opportunity_taxonomy.py backend/tests/test_migrations.py
git commit -m "feat(opportunities): add job taxonomy and publication dates"
```

### Task 2: Sayfalanmış ve facet'li browse endpoint'i

**Files:**
- Create: `backend/app/modules/opportunity/browse.py`
- Modify: `backend/app/modules/opportunity/schemas.py`
- Modify: `backend/app/modules/opportunity/router.py`
- Modify: `backend/app/modules/opportunity/service.py`
- Create: `backend/tests/test_opportunity_browse.py`
- Modify: `backend/tests/test_opportunity_lifecycle.py`

**Interfaces:**
- Produces: `browse_opportunities(session, filters: BrowseFilters) -> OpportunityBrowseOut`.
- Produces: `GET /api/opportunities/browse` before the dynamic `/{item_id}` route.
- Preserves: legacy `GET /api/opportunities` list shape while enforcing its query parameters.

- [ ] **Step 1: Write failing API tests**

Create jobs in at least three categories plus YLSY, ÖSYM, other announcement and trash fixtures. Assert:

```python
response = await client.get("/api/opportunities/browse?section=jobs&category=data-ai&limit=2")
payload = response.json()
assert [item["category"] for item in payload["items"]] == ["data-ai"]
assert payload["total"] == 3
assert payload["section_counts"] == {"jobs": 7, "announcements": 3, "trash": 1}
assert payload["facets"]["categories"]["data-ai"] == 3
```

Also test `announcement_source=ylsy|osym|other`, `period_days`, `year`, search, status, region, remote, `sort=score|newest|oldest|deadline`, offset, and `limit <= 120`.

- [ ] **Step 2: Run tests and verify red**

Run: `docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm backend-test pytest -q tests/test_opportunity_browse.py`

Expected: 404 for `/api/opportunities/browse`.

- [ ] **Step 3: Implement browse schemas**

```python
class OpportunityBrowseOut(BaseModel):
    items: list[OpportunityOut]
    total: int
    offset: int
    limit: int
    section_counts: dict[str, int]
    facets: dict[str, dict[str, int]]
```

`BrowseFilters` is an internal frozen dataclass with section, announcement source, category, search, status, source, region, remote, period days, year, sort, offset and limit.

- [ ] **Step 4: Implement SQL filtering and stable sorting**

Build one base `select(Opportunity, Entity.title).join(Entity)` query. Apply:

```python
if section == "jobs":
    conditions.append(Opportunity.kind == "job")
elif section == "announcements":
    conditions.append(Opportunity.kind != "job")
elif section == "trash":
    conditions.append(Opportunity.trashed_at.is_not(None))
```

Search uses `Entity.search_vec.op("@@")(func.plainto_tsquery("simple", func.immutable_unaccent(search)))`. Newest sort uses `coalesce(published_at, found_at).desc(), Entity.title.asc(), Opportunity.id.asc()`. Deadline sort keeps nulls last. Query only returns `limit` rows after `offset`; `count(*)` and facet groupings are separate aggregate queries.

- [ ] **Step 5: Fix the legacy list contract**

Apply status/kind predicates and `.limit(limit)` before execution. Remove the unreachable second return in `list_opportunities()`. Keep document reverse-link enrichment only for returned IDs.

- [ ] **Step 6: Verify focused backend behavior**

Run:

```bash
docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm backend-test pytest -q tests/test_opportunity_browse.py tests/test_opportunity_lifecycle.py tests/test_application_crm.py
```

Expected: all pass and a `limit=2` legacy request returns exactly two items.

- [ ] **Step 7: Commit Task 2**

```bash
git add backend/app/modules/opportunity backend/tests/test_opportunity_browse.py backend/tests/test_opportunity_lifecycle.py
git commit -m "feat(opportunities): add faceted browse API"
```

### Task 3: Duplicate cluster hatasını kökten düzeltme

**Files:**
- Modify: `backend/app/modules/opportunity/service.py`
- Modify: `backend/app/modules/opportunity/__init__.py`
- Create: `backend/scripts/dedupe_opportunities.py`
- Create: `backend/tests/test_opportunity_ingest.py`

**Interfaces:**
- Produces: `canonical_cluster(rows: Sequence[Opportunity]) -> Opportunity`.
- Produces: `merge_duplicate_clusters(session, *, dry_run: bool = True) -> DuplicateMergeSummary`.
- Preserves source run error reporting; no exception swallowing.

- [ ] **Step 1: Write a failing duplicate ingest regression test**

Insert two discovered opportunities with the same `raw.forkjob.cluster_key`, then ingest the same cluster from a third source. Assert no `Multiple rows` exception, no third row, and canonical `raw.sources` contains all source IDs.

- [ ] **Step 2: Verify red**

Run: `docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm backend-test pytest -q tests/test_opportunity_ingest.py`

Expected: `MultipleResultsFound` from `scalar_one_or_none()`.

- [ ] **Step 3: Select a canonical row without a single-row assumption**

Fetch cluster matches with `.scalars().all()`. Prefer, in order: non-discovered status, applied date, notes, linked row, earliest `found_at`, stable UUID. Merge source labels into canonical `raw.sources`. Same-source/different-external-ID matches are duplicates too.

- [ ] **Step 4: Implement guarded maintenance cleanup**

`merge_duplicate_clusters()` only deletes duplicate rows when all rows are `discovered`, have no notes/application/links, and are not trashed. It logs one `opportunity.duplicates_merged` event on the canonical entity with merged IDs before calling `delete_entity()` on duplicates. Unsafe groups are reported as skipped.

The script defaults to dry-run and requires `--apply` for writes:

```bash
PYTHONPATH=. .venv/bin/python scripts/dedupe_opportunities.py
PYTHONPATH=. .venv/bin/python scripts/dedupe_opportunities.py --apply
```

- [ ] **Step 5: Verify red-green and idempotency**

Test that a second cleanup run reports zero merged groups and event rows remain append-only.

- [ ] **Step 6: Commit Task 3**

```bash
git add backend/app/modules/opportunity backend/scripts/dedupe_opportunities.py backend/tests/test_opportunity_ingest.py
git commit -m "fix(opportunities): merge duplicate job clusters"
```

### Task 4: Aktif kaynak sağlığını tarihsel gürültüden ayırma

**Files:**
- Modify: `backend/app/core/runs.py`
- Modify: `backend/app/core/router.py`
- Create: `backend/tests/test_source_health.py`

**Interfaces:**
- Extends: `health(session, limit=50, *, active_only=True)`.
- Preserves all `source_run` rows; only health projection changes.

- [ ] **Step 1: Write a failing orphan RSS test**

Create one active feed entity with an error run, one deleted/nonexistent `rss:<uuid>` error run and one opportunity source error. Assert `/api/sources/health` includes active feed + opportunity source but excludes orphan RSS.

- [ ] **Step 2: Verify red**

Run: `docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm backend-test pytest -q tests/test_source_health.py`

Expected: orphan RSS appears in the response.

- [ ] **Step 3: Filter entity-backed source IDs in the health query**

For rows with `source LIKE 'rss:%'`, require an existing `Entity` whose type is `feed` and whose UUID text matches the suffix. Do this with an `exists()` expression and a UUID-format regex guard; do not import RSS module models into core. Non-RSS source IDs are unchanged.

- [ ] **Step 4: Verify health and banner-adjacent tests**

Run backend focused test plus frontend `SourceHealthAccordion`, `SettingsSourceHealth` and app banner tests.

- [ ] **Step 5: Commit Task 4**

```bash
git add backend/app/core/runs.py backend/app/core/router.py backend/tests/test_source_health.py
git commit -m "fix(sources): hide orphan runs from active health"
```

### Task 5: ÖSYM, YÖK, BulldogJob ve Consider adapterlerini onarma

**Files:**
- Modify: `backend/app/sources/announcements.py`
- Modify: `backend/app/sources/forkjob_core/scrapers/bulldogjob.py`
- Modify: `backend/app/sources/forkjob_core/scrapers/consider.py`
- Modify: `backend/app/sources/forkjob_core/data/portals.yaml`
- Modify: `backend/tests/sources/fixtures/announcement.html`
- Create: `backend/tests/sources/fixtures/yok_announcements.html`
- Modify: `backend/tests/sources/test_forkjob_parsers.py`
- Create: `backend/tests/sources/test_consider.py`

**Interfaces:**
- OSYM/YÖK `RawItem.published_at` contains the official publication date when present.
- Sequoia Consider performs a public page bootstrap before CSRF-protected POST.
- a16z Consider is disabled with a dated status reason.

- [ ] **Step 1: Add failing parser and request-contract tests**

Tests cover:

- OSYM anchor text beginning `26 Ağustos 2026` produces UTC `published_at`.
- YÖK `.blog-item` reads `.date-block .month/.day` and current page year.
- Bulldog GraphQL query does not request removed `salaryFrom`, `salaryTo`, `salaryCurrency` fields and parses the verified reduced payload.
- Consider calls `get_html(base_url + "/jobs")`, extracts `window.serverInitialData.csrfToken`, then posts with `x-csrf-token`, `origin`, `referer` using the same client session.

- [ ] **Step 2: Verify red**

Run: `cd backend && pytest -q tests/sources/test_forkjob_parsers.py tests/sources/test_consider.py`

- [ ] **Step 3: Update announcement adapters**

Set YÖK URL to the live official `https://www.yok.gov.tr/tr/announcements`. Implement a dedicated `YokAnnouncementSource` that iterates `.blog-item`, extracts the title link, date block and only configured graduate/burs keywords. Keep source ID `yok-msc` for continuity.

Generic `AnnouncementSource.parse_html()` uses `parse_turkish_heading_date(title)` for ÖSYM before creating `RawItem`.

- [ ] **Step 4: Update Bulldog GraphQL query**

Remove the three deleted salary fields. Keep salary rendering nullable; do not synthesize salary. If GraphQL returns an `errors` array, raise `ScraperPermanentError` containing the first GraphQL message rather than the misleading shape error.

- [ ] **Step 5: Bootstrap Sequoia CSRF and disable a16z**

Parse `window.serverInitialData` from the public `/jobs` HTML, read `csrfToken`, and POST with matching origin/referer headers. Keep pagination behavior. Set `consider-a16z.enabled: false` with status `Disabled 2026-08-29: legacy /api-boards/search-jobs is gone; current board no longer uses the public Consider contract.`

- [ ] **Step 6: Verify parsers and live smoke checks**

Run fixture tests first. Then run named source refreshes for `yok-msc`, `jobhunter:bulldogjob`, and `jobhunter:consider-sequoia`; poll `/api/sources/sync` until complete and verify their latest `source_run` is `ok` or honest `empty`, never the previous contract error.

- [ ] **Step 7: Commit Task 5**

```bash
git add backend/app/sources backend/tests/sources
git commit -m "fix(sources): refresh opportunity adapters"
```

### Task 6: Frontend domain model ve bağlamsal filtreler

**Files:**
- Modify: `frontend/src/core/types.ts`
- Create: `frontend/src/modules/opportunity/opportunityBrowse.ts`
- Create: `frontend/src/modules/opportunity/OpportunityFilters.tsx`
- Create: `frontend/src/modules/opportunity/OpportunityFilters.test.tsx`
- Modify: `frontend/src/modules/opportunity/labels.ts`

**Interfaces:**
- Produces: `OpportunitySection = "jobs" | "announcements" | "trash"`.
- Produces: `AnnouncementSource = "ylsy" | "osym" | "other"`.
- Produces: `OpportunityBrowseFilters`, `OpportunityBrowseResponse`, `browseQuery(filters)`.

- [ ] **Step 1: Write failing query and contextual-filter tests**

Assert jobs query includes category/region/remote and announcements query includes announcement source/period/year but excludes job-only filters. Assert switching section resets only incompatible fields and preserves search/layout.

- [ ] **Step 2: Verify red**

Run: `cd frontend && npm test -- --run src/modules/opportunity/OpportunityFilters.test.tsx`

- [ ] **Step 3: Implement typed browse query builder**

Use existing `qs()` and return `/opportunities/browse?...`. Keep URL parameter names identical to backend. Add category labels:

```ts
export const JOB_CATEGORY_LABELS = {
  software: "Yazılım & mühendislik",
  "data-ai": "Veri & yapay zekâ",
  "product-design": "Ürün & tasarım",
  "cloud-security": "Bulut, DevOps & güvenlik",
  "business-ops": "İş, finans & operasyon",
  "sales-marketing": "Satış & pazarlama",
  other: "Diğer",
} as const;
```

- [ ] **Step 4: Implement contextual filter groups**

Compose existing `Input`, `Select`, `Checkbox`, `FilterChip`, `Section` and token classes. Do not render hidden/inapplicable job filters in announcement mode. Every toggle has `aria-pressed`; mobile toolbar wraps without a minimum fixed width larger than the viewport.

- [ ] **Step 5: Verify and commit Task 6**

```bash
npm test -- --run src/modules/opportunity/OpportunityFilters.test.tsx
git add frontend/src/core/types.ts frontend/src/modules/opportunity
git commit -m "feat(opportunities): add contextual browse filters"
```

### Task 7: Responsive iş ve duyuru kartları

**Files:**
- Modify: `frontend/src/modules/opportunity/OpportunityList.tsx`
- Modify: `frontend/src/modules/opportunity/OpportunityList.test.tsx`
- Create: `frontend/src/modules/opportunity/OpportunityGrid.test.tsx`

**Interfaces:**
- Produces: `OpportunityCollection({ layout, children })`.
- Produces: separate `JobOpportunityCard` and `AnnouncementCard` presentations behind `OpportunityCard` dispatch.

- [ ] **Step 1: Write failing responsive structure tests**

Render `OpportunityCollection` and assert grid mode contains token classes equivalent to `grid-cols-1 md:grid-cols-2 xl:grid-cols-3`, while rows mode is one column. Render an announcement and assert it shows absolute publication date, institution and no score label. Render a job and assert category, score and publish/discovery copy.

- [ ] **Step 2: Verify red**

Run: `cd frontend && npm test -- --run src/modules/opportunity/OpportunityList.test.tsx src/modules/opportunity/OpportunityGrid.test.tsx`

- [ ] **Step 3: Implement responsive collection and card variants**

Grid container:

```tsx
<div className={cx(layout === "grid" ? "grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3" : "divide-y divide-subtle")}>
  {children}
</div>
```

Grid cards receive border/background/padding from semantic tokens; row cards retain divider presentation. Actions use `Button`, `Select`, `Chip`; no raw inputs or arbitrary values. Announcement cards use a compact calendar block and `deadline_at` only when real.

- [ ] **Step 4: Verify keyboard, overflow and component tests**

Run focused tests and `npm test -- --run src/core/designSystem.test.ts`.

- [ ] **Step 5: Commit Task 7**

```bash
git add frontend/src/modules/opportunity/OpportunityList.tsx frontend/src/modules/opportunity/OpportunityList.test.tsx frontend/src/modules/opportunity/OpportunityGrid.test.tsx
git commit -m "feat(opportunities): add responsive job and announcement cards"
```

### Task 8: Fırsatlar sayfasını browse akışına bağlama

**Files:**
- Modify: `frontend/src/modules/opportunity/OpportunityPage.tsx`
- Create: `frontend/src/modules/opportunity/OpportunityPage.test.tsx`
- Modify: `frontend/src/modules/documents/DocumentsPage.test.tsx` if the enforced legacy limit changes fixtures

**Interfaces:**
- Consumes: `/opportunities/browse`, `OpportunityFilters`, `OpportunityCollection`.
- Preserves: focus route, detail drawer, save-to-library, lifecycle mutations and CRM panel.

- [ ] **Step 1: Write failing page integration tests**

Mock browse responses and assert:

- primary `İş ilanları`, `Duyurular`, `Çöp` navigation;
- `YLSY`, `ÖSYM`, `Diğer` only under announcements;
- default jobs sort `score`, default announcements sort `newest`;
- “Daha fazla” increments offset/limit without downloading the full dataset;
- list/grid choice persists and grid collection receives the selected layout;
- loading skeleton, API error retry and contextual empty-state reset.

- [ ] **Step 2: Verify red**

Run: `cd frontend && npm test -- --run src/modules/opportunity/OpportunityPage.test.tsx`

- [ ] **Step 3: Replace all-active client filtering with browse query state**

Use one query key containing normalized filters. Accumulate pages only for “Daha fazla”; filter changes reset offset and selected page data. Mutation success keeps `invalidateAfter("opportunity.write")`. Keep trash confirmation behavior unchanged.

- [ ] **Step 4: Persist the view safely**

Read `forkos:opportunity-view`; accept only `rows`/`grid`, default to `rows`, and write on explicit toggle. Guard `window.localStorage` for SSR/tests.

- [ ] **Step 5: Add contextual skeleton/error/empty states**

Skeleton mirrors row/grid shape. Retry uses query `refetch`. Empty state resets all filters valid for the current section, including category/source/period/year.

- [ ] **Step 6: Run focused and adjacent frontend tests**

```bash
npm test -- --run src/modules/opportunity/OpportunityPage.test.tsx src/modules/opportunity/OpportunityList.test.tsx src/modules/opportunity/OpportunityGrid.test.tsx src/modules/opportunity/OpportunityFilters.test.tsx src/modules/documents/DocumentsPage.test.tsx
npm run build
```

- [ ] **Step 7: Commit Task 8**

```bash
git add frontend/src/modules/opportunity frontend/src/modules/documents/DocumentsPage.test.tsx
git commit -m "feat(opportunities): integrate categorical browse workspace"
```

### Task 9: Contract, veri bakımı, görsel doğrulama ve teslim

**Files:**
- Modify: `backend/openapi.json`
- Modify: `frontend/src/generated/api-schema.ts`
- Verify: all changed files

**Interfaces:**
- Produces synchronized generated contracts, cleaned local duplicate rows and a verified `origin/main` push.

- [ ] **Step 1: Regenerate API contracts**

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/export_openapi.py
cd ../frontend
npm run api:generate
```

- [ ] **Step 2: Run the duplicate cleanup dry-run and apply**

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/dedupe_opportunities.py
PYTHONPATH=. .venv/bin/python scripts/dedupe_opportunities.py --apply
PYTHONPATH=. .venv/bin/python scripts/dedupe_opportunities.py
```

Expected: first run reports only safe discovered/unlinked groups; apply reports merged groups; final dry-run reports zero safe duplicate groups.

- [ ] **Step 3: Run full backend verification**

```bash
docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm backend-test sh -c 'alembic upgrade head && pytest -q'
docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm --no-deps backend-test ruff check app tests scripts
```

- [ ] **Step 4: Run full frontend verification**

```bash
cd frontend
npm test
npm run build
npm run api:check
node scripts/check-endpoint-coverage.mjs
npm run format:check
```

- [ ] **Step 5: Measure the browse payload**

Request default jobs browse with limit 60. Assert response has at most 60 items and is materially below the previous 6,3 MB full-list payload. Record bytes and response time in the final handoff.

- [ ] **Step 6: Visually verify real data at three widths**

Check approximately 390px, 900px and 1440px widths. Verify no horizontal overflow, grid columns 1/2/3, list single-column behavior, contextual filters, category labels, YLSY/ÖSYM date order, detail opening and action accessibility.

- [ ] **Step 7: Commit generated artifacts**

```bash
git add backend/openapi.json frontend/src/generated/api-schema.ts
git commit -m "chore: refresh opportunity API contracts"
```

Skip this commit if generated files are unchanged.

- [ ] **Step 8: Verify and push main**

```bash
git diff --check
git status --short
git fetch origin main
git rev-list --left-right --count origin/main...main
git push origin main
test "$(git rev-parse HEAD)" = "$(git ls-remote origin refs/heads/main | awk '{print $1}')"
```

Only fast-forward when the remote side has not advanced unexpectedly.
