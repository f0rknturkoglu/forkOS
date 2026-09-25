# forkOS × career-ops — C3 Implementation Plan: JD Extraction, Liveness & Listing Intelligence

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate career-ops headless JD extraction, zero-token link liveness verification, and listing intelligence into forkOS with strict local-only execution, zero LLM calls, and complete isolation between candidate match scores and listing quality.

**Architecture:** A static Node JSON bridge (`bridges/liveness.mjs`) connects upstream ES modules to the forkOS `SubprocessCareerOpsRunner` without parsing CLI prose. `OpportunityListingService` manages on-demand 24h-cached liveness, multi-source aggregation, safe 2-step confirmation closures, and canonical description promotion. PostgreSQL holds all persistent state (`OpportunitySourceObservation.enrichment` JSONB); repost detection runs via ephemeral scratch TSV projection.

**Architecture Diagram:**

```mermaid
graph TD
    subgraph "Frontend & API"
        UI[Opportunity Detail UI] --> API[FastAPI /api/opportunities]
    end

    subgraph "Domain & Intelligence"
        API --> LS[OpportunityListingService]
        API --> IS[Intelligence & Listing Health]
        LS --> DB[(PostgreSQL: Opportunity + SourceObservation)]
    end

    subgraph "CareerOps Adapter & Runner"
        LS --> ADP[CareerOpsAdapter]
        ADP --> RUN[SubprocessCareerOpsRunner]
        RUN --> BRG[bridges/liveness.mjs]
        RUN --> EXT[browser-extract.mjs]
        RUN --> REP[detect-reposts.mjs + Ephemeral TSV]
    end
```

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (asyncpg), Alembic, Pydantic v2, Node.js v20+, Playwright Chromium, React/TypeScript.

**Spec:** [docs/superpowers/specs/2026-09-25-career-ops-c3-design.md](file:///Users/furkanturkoglu/Desktop/Projeler/forkOS/docs/superpowers/specs/2026-09-25-career-ops-c3-design.md)

## Global Constraints
- Zero LLM calls (deterministic rules, regex, DOM selectors, JSON APIs only).
- `Opportunity.score` (candidate match) MUST NOT be modified or overwritten by listing quality signals.
- `uncertain != expired`: transient liveness failures NEVER hard-close opportunities.
- Hard closure requires 2 consecutive all-expired checks across all attached sources, separated by >= 12 hours.
- PostgreSQL is the sole source of truth; upstream TSV files are strictly ephemeral projections.
- Single SQL statement per `op.execute()` in Alembic migrations (asyncpg invariant).
- Every new or modified endpoint must have schema synced to `openapi.json` and `api-schema.ts`.

---

### Task 1: Playwright Browser Provisioning & Doctor Readiness

**Files:**
- Modify: `Makefile:120-135`
- Modify: `backend/app/integrations/career_ops/doctor.py:40-90`
- Modify: `backend/app/integrations/career_ops/capabilities.py:165-195`
- Test: `backend/tests/test_career_ops_doctor.py`
- Test: `backend/tests/test_career_ops_capabilities.py`

**Interfaces:**
- Consumes: `CareerOpsDoctorReport`, `CapabilityStatus`
- Produces: `make career-ops-browser-setup`, `doctor.probe_browser_readiness()` returning bool

- [ ] **Step 1: Write failing tests for doctor browser probe and capability activation**

```python
# In backend/tests/test_career_ops_doctor.py
@pytest.mark.no_database
@pytest.mark.asyncio
async def test_doctor_reports_browser_readiness(tmp_path: Path):
    from app.integrations.career_ops.doctor import probe_browser_readiness
    # Missing node_modules/playwright returns False
    assert probe_browser_readiness(tmp_path) is False
```

```python
# In backend/tests/test_career_ops_capabilities.py
def test_c3_capabilities_become_supported_when_browser_ready():
    from app.integrations.career_ops.capabilities import get_capability_status
    from app.integrations.career_ops.models import CapabilityStatus

    # Without browser_ready:
    assert get_capability_status("discovery.liveness", enabled=True, runtime_ready=True, browser_ready=False) == CapabilityStatus.UNAVAILABLE
    # With browser_ready:
    assert get_capability_status("discovery.liveness", enabled=True, runtime_ready=True, browser_ready=True) == CapabilityStatus.SUPPORTED
    assert get_capability_status("job.extract", enabled=True, runtime_ready=True, browser_ready=True) == CapabilityStatus.SUPPORTED
    assert get_capability_status("job.repost_analysis", enabled=True, runtime_ready=True, browser_ready=True) == CapabilityStatus.SUPPORTED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_career_ops_doctor.py backend/tests/test_career_ops_capabilities.py -k "browser"`
Expected: FAIL with `ImportError` or `unexpected keyword argument 'browser_ready'`.

- [ ] **Step 3: Implement browser probe in doctor.py, update capabilities.py and Makefile**

In `Makefile`:
```makefile
career-ops-browser-setup:
	cd .vendor/career-ops && npx playwright install chromium
```

In `backend/app/integrations/career_ops/doctor.py`:
Implement `probe_browser_readiness(checkout_dir: Path) -> bool` checking if Playwright Chromium can be resolved. Include `browser_ready: bool` in `CareerOpsDoctorReport`.

In `backend/app/integrations/career_ops/capabilities.py`:
Add `browser_ready: bool = False` to `get_capability_status` and `count_available_capabilities`. Map `discovery.liveness`, `job.extract`, `job.repost_analysis` to `SUPPORTED` when `browser_ready` is True.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/test_career_ops_doctor.py backend/tests/test_career_ops_capabilities.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Makefile backend/app/integrations/career_ops/doctor.py backend/app/integrations/career_ops/capabilities.py backend/tests/test_career_ops_doctor.py backend/tests/test_career_ops_capabilities.py
git commit -m "feat(career-ops): add browser provisioning target and doctor browser readiness probe"
```

---

### Task 2: Static JSON Bridge for Liveness (`bridges/liveness.mjs`) & Models

**Files:**
- Create: `backend/app/integrations/career_ops/bridges/liveness.mjs`
- Modify: `backend/app/integrations/career_ops/runner.py:18-35` (allowlist `bridges/liveness.mjs`)
- Modify: `backend/app/integrations/career_ops/models.py:70-120`
- Modify: `backend/app/integrations/career_ops/adapter.py:150-210`
- Test: `backend/tests/test_career_ops_liveness_bridge.py`

**Interfaces:**
- Consumes: `SubprocessCareerOpsRunner.run_script("bridges/liveness.mjs", [url])`
- Produces: `CareerOpsLivenessReceipt` model, `CareerOpsAdapter.check_liveness(url, timeout_ms=15000)`

- [ ] **Step 1: Write failing unit test for `bridges/liveness.mjs` and `adapter.check_liveness`**

```python
# backend/tests/test_career_ops_liveness_bridge.py
import pytest
from app.integrations.career_ops.models import CareerOpsLivenessReceipt
from app.integrations.career_ops.adapter import CareerOpsAdapter

@pytest.mark.no_database
@pytest.mark.asyncio
async def test_adapter_check_liveness_parses_json_receipt():
    payload = {
        "url": "https://boards.greenhouse.io/example/jobs/123",
        "status": "active",
        "code": "greenhouse_api_ok",
        "reason": "ATS API returns the posting (live)",
        "method": "api",
        "checked_at": "2026-09-25T20:20:00Z"
    }
    # Test that CareerOpsLivenessReceipt validates properly
    receipt = CareerOpsLivenessReceipt.model_validate(payload)
    assert receipt.status == "active"
    assert receipt.method == "api"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_career_ops_liveness_bridge.py -v`
Expected: FAIL with `ImportError: cannot import name 'CareerOpsLivenessReceipt'`.

- [ ] **Step 3: Implement `CareerOpsLivenessReceipt`, `bridges/liveness.mjs`, allowlist in runner, and `adapter.check_liveness`**

1. In `backend/app/integrations/career_ops/models.py`:
```python
class CareerOpsLivenessReceipt(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str
    status: Literal["active", "expired", "uncertain"]
    code: str
    reason: str
    method: Literal["api", "browser", "bridge"]
    checked_at: str
```

2. In `backend/app/integrations/career_ops/bridges/liveness.mjs`:
Implement Node script importing `checkLivenessViaApi` from `../liveness-api.mjs` and `checkUrlLivenessWithFallback` from `../liveness-browser.mjs`. Emit single JSON document to stdout.

3. In `backend/app/integrations/career_ops/runner.py`:
Add `"bridges/liveness.mjs"` to `ALLOWLISTED_SCRIPTS`.

4. In `backend/app/integrations/career_ops/adapter.py`:
Implement `async def check_liveness(self, url: str, timeout_ms: int = 15_000) -> CareerOpsLivenessReceipt`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_career_ops_liveness_bridge.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/career_ops/bridges/liveness.mjs backend/app/integrations/career_ops/models.py backend/app/integrations/career_ops/runner.py backend/app/integrations/career_ops/adapter.py backend/tests/test_career_ops_liveness_bridge.py
git commit -m "feat(career-ops): implement static JSON bridge for zero-token liveness verification"
```

---

### Task 3: JD Extraction Subsystem (`CareerOpsAdapter.extract_job`)

**Files:**
- Modify: `backend/app/integrations/career_ops/runner.py` (allowlist `browser-extract.mjs`)
- Modify: `backend/app/integrations/career_ops/models.py`
- Modify: `backend/app/integrations/career_ops/adapter.py`
- Test: `backend/tests/test_career_ops_extraction.py`

**Interfaces:**
- Consumes: `browser-extract.mjs <url> --mode jd --max-chars <N>`
- Produces: `CareerOpsJobExtractionResult` model, `CareerOpsAdapter.extract_job(url, max_chars=12000, timeout_ms=15000)`

- [ ] **Step 1: Write failing test for JD extraction**

```python
# backend/tests/test_career_ops_extraction.py
import pytest
from app.integrations.career_ops.models import CareerOpsJobExtractionResult

@pytest.mark.no_database
def test_career_ops_extraction_result_model():
    payload = {
        "url": "https://example.com/job/1",
        "title": "Backend Engineer",
        "text": "Job description text content...",
    }
    result = CareerOpsJobExtractionResult.model_validate(payload)
    assert result.title == "Backend Engineer"
    assert len(result.text) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_career_ops_extraction.py -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `CareerOpsJobExtractionResult` and `CareerOpsAdapter.extract_job`**

1. In `backend/app/integrations/career_ops/models.py`:
```python
class CareerOpsJobExtractionResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str
    title: str = ""
    text: str = ""
    error: str | None = None
    code: str | None = None
```

2. In `backend/app/integrations/career_ops/runner.py`:
Add `"browser-extract.mjs"` to `ALLOWLISTED_SCRIPTS`.

3. In `backend/app/integrations/career_ops/adapter.py`:
Implement `async def extract_job(self, url: str, max_chars: int = 12_000, timeout_ms: int = 15_000) -> CareerOpsJobExtractionResult`. Handle exit code 1 / error output safely without raising unhandled exceptions when page is dead.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_career_ops_extraction.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/career_ops/models.py backend/app/integrations/career_ops/runner.py backend/app/integrations/career_ops/adapter.py backend/tests/test_career_ops_extraction.py
git commit -m "feat(career-ops): implement deterministic JD extraction via browser-extract.mjs"
```

---

### Task 4: Ephemeral Repost Projection (`detect-reposts.mjs` Bridge)

**Files:**
- Modify: `backend/app/integrations/career_ops/runner.py` (allowlist `detect-reposts.mjs`)
- Modify: `backend/app/integrations/career_ops/models.py`
- Modify: `backend/app/integrations/career_ops/adapter.py`
- Test: `backend/tests/test_career_ops_repost_projection.py`

**Interfaces:**
- Consumes: Posting history rows `(url, first_seen, portal, title, company, status, location)`
- Produces: `CareerOpsRepostCluster` models, `CareerOpsAdapter.detect_reposts(rows, window_days=90)`

- [ ] **Step 1: Write failing test for ephemeral TSV projection and cluster parsing**

```python
# backend/tests/test_career_ops_repost_projection.py
import pytest
from app.integrations.career_ops.models import CareerOpsRepostCluster

@pytest.mark.no_database
def test_career_ops_repost_cluster_model():
    cluster = CareerOpsRepostCluster.model_validate({
        "company": "Acme Corp",
        "role": "Senior Engineer",
        "repostCount": 3,
        "firstSeen": "2026-08-01",
        "lastSeen": "2026-09-15",
        "daysSpan": 45,
        "appearances": [
            {"url": "https://example.com/1", "date": "2026-08-01", "title": "Senior Engineer"},
            {"url": "https://example.com/2", "date": "2026-09-15", "title": "Senior Engineer"},
        ]
    })
    assert cluster.repost_count == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_career_ops_repost_projection.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `CareerOpsRepostCluster`, allowlist, and `adapter.detect_reposts`**

1. Add `CareerOpsRepostAppearance` and `CareerOpsRepostCluster` models in `models.py` (with alias generator for camelCase).
2. Allowlist `"detect-reposts.mjs"` in `runner.py`.
3. In `adapter.py`:
Implement `async def detect_reposts(self, rows: list[dict[str, str]], window_days: int = 90) -> list[CareerOpsRepostCluster]`:
- Create `data/scan-history.tsv` inside temporary directory / runtime dir.
- Execute `detect-reposts.mjs --window <window_days>`.
- Parse output JSON `clusters`.
- In `finally:` block, unlink `data/scan-history.tsv`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_career_ops_repost_projection.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/career_ops/models.py backend/app/integrations/career_ops/runner.py backend/app/integrations/career_ops/adapter.py backend/tests/test_career_ops_repost_projection.py
git commit -m "feat(career-ops): implement ephemeral TSV projection and bridge for detect-reposts.mjs"
```

---

### Task 5: Database Migration: Add `enrichment` JSONB to `OpportunitySourceObservation`

**Files:**
- Create: `backend/alembic/versions/<revision>_add_enrichment_to_source_observation.py`
- Modify: `backend/app/modules/opportunity/models.py:98-131`
- Test: `backend/tests/test_migrations.py`

**Interfaces:**
- Consumes: SQLAlchemy metadata
- Produces: `OpportunitySourceObservation.enrichment` column (JSONB, default `{}`)

- [ ] **Step 1: Write migration test verifying `enrichment` column exists after upgrade**

Check `backend/tests/test_migrations.py` to ensure schema tests cover `OpportunitySourceObservation`.

- [ ] **Step 2: Create Alembic migration script adhering to `postgres-alembic-guardian`**

```python
"""add enrichment to source observation

Revision ID: b7d2e3f4a5c6
Revises: <previous_revision>
Create Date: 2026-09-25
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b7d2e3f4a5c6'
down_revision = '<previous_revision>'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute(
        "ALTER TABLE opportunity_source_observation "
        "ADD COLUMN IF NOT EXISTS enrichment JSONB NOT NULL DEFAULT '{}'::jsonb"
    )

def downgrade() -> None:
    op.execute(
        "ALTER TABLE opportunity_source_observation "
        "DROP COLUMN IF EXISTS enrichment"
    )
```

- [ ] **Step 3: Update `OpportunitySourceObservation` in `backend/app/modules/opportunity/models.py`**

```python
enrichment: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
```

- [ ] **Step 4: Run migration test and verify upgrade/downgrade**

Run: `pytest backend/tests/test_migrations.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/*_add_enrichment_to_source_observation.py backend/app/modules/opportunity/models.py
git commit -m "feat(opportunity): add enrichment JSONB column to opportunity_source_observation"
```

---

### Task 6: Opportunity Listing Service & Multi-Source Liveness Aggregation

**Files:**
- Create: `backend/app/modules/opportunity/listing_service.py`
- Modify: `backend/app/modules/opportunity/service.py`
- Test: `backend/tests/test_opportunity_liveness_service.py`

**Interfaces:**
- Consumes: `Opportunity`, `OpportunitySourceObservation`, `CareerOpsAdapter`
- Produces: `OpportunityListingService.verify_opportunity_liveness()`, `OpportunityListingService.enrich_job_description()`

- [ ] **Step 1: Write unit tests for multi-source liveness aggregation and 2-step confirmation**

```python
# backend/tests/test_opportunity_liveness_service.py
@pytest.mark.asyncio
async def test_one_active_source_keeps_canonical_opportunity_active():
    # If source A is expired but source B is active, opportunity source_status remains 'active'
    ...

@pytest.mark.asyncio
async def test_all_sources_expired_requires_two_step_confirmation():
    # 1st check sets source_status='likely_closed'
    # 2nd check (>= 12h later) sets source_status='closed'
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_opportunity_liveness_service.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `OpportunityListingService`**

Implement:
- `verify_opportunity_liveness(session, opportunity_id, force=False)`:
  - Checks 24h cache in observation enrichment.
  - Runs liveness check via adapter.
  - Updates observation `enrichment["liveness"]`.
  - Aggregates status: active wins; all expired -> safe 2-step closure.
- `enrich_job_description(session, opportunity_id)`:
  - If description is empty or <200 chars, call `adapter.extract_job(url)`.
  - If text is >= 200 chars, update `raw["description"]`, call `touch_entity(search_text=...)`.
  - Save extraction metadata in observation `enrichment`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_opportunity_liveness_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/opportunity/listing_service.py backend/tests/test_opportunity_liveness_service.py
git commit -m "feat(opportunity): implement OpportunityListingService with safe liveness aggregation and JD promotion"
```

---

### Task 7: Listing Health & Quality Signals

**Files:**
- Modify: `backend/app/modules/opportunity/schemas.py:20-50`
- Modify: `backend/app/modules/opportunity/intelligence.py:225-365`
- Test: `backend/tests/test_opportunity_listing_health.py`

**Interfaces:**
- Consumes: `Opportunity`, `OpportunitySourceObservation.enrichment`
- Produces: `ListingHealthOut` model, `quick_signals()` updated with `listing_health`

- [ ] **Step 1: Write tests proving `Opportunity.score` is unaffected by listing health**

```python
# backend/tests/test_opportunity_listing_health.py
def test_listing_health_never_modifies_candidate_score():
    # Opportunity.score remains strictly candidate fit
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_opportunity_listing_health.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `ListingHealthOut` and compute diagnostic listing health**

In `schemas.py`:
```python
class ListingHealthOut(BaseModel):
    health_score: int = Field(ge=0, le=100)
    jd_completeness: Literal["complete", "concise", "stub"]
    salary_transparency: Literal["transparent", "unclear", "missing"]
    liveness_status: Literal["live", "unchecked", "at_risk", "expired"]
    repost_frequency: Literal["none", "moderate", "frequent"]
```
Add `listing_health: ListingHealthOut` to `OpportunityIntelligenceOut`.
In `intelligence.py`: compute `listing_health` within `quick_signals()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_opportunity_listing_health.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/opportunity/schemas.py backend/app/modules/opportunity/intelligence.py backend/tests/test_opportunity_listing_health.py
git commit -m "feat(opportunity): compute diagnostic listing health isolated from candidate match score"
```

---

### Task 8: API Endpoints & Contract Sync (`api-contract-sync`)

**Files:**
- Modify: `backend/app/modules/opportunity/router.py`
- Modify: `backend/openapi.json`
- Modify: `frontend/src/generated/api-schema.ts`
- Test: `backend/tests/test_opportunity_listing_api.py`

**Interfaces:**
- Consumes: `POST /api/opportunities/{id}/liveness`, `POST /api/opportunities/{id}/extract-jd`
- Produces: Updated OpenAPI spec and TypeScript contracts

- [ ] **Step 1: Write integration tests for new endpoints**

```python
# backend/tests/test_opportunity_listing_api.py
@pytest.mark.asyncio
async def test_trigger_liveness_check_endpoint(client):
    response = await client.post(f"/api/opportunities/{opp_id}/liveness")
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_opportunity_listing_api.py -v`
Expected: FAIL (404 Not Found).

- [ ] **Step 3: Implement endpoints in router.py**

Wire `POST /api/opportunities/{id}/liveness` and `POST /api/opportunities/{id}/extract-jd` to `OpportunityListingService`.

- [ ] **Step 4: Run export-openapi and sync TypeScript contracts**

Run:
```bash
python backend/scripts/export_openapi.py
npm --prefix frontend run generate:api-schema
node frontend/scripts/check-endpoint-coverage.mjs
```

- [ ] **Step 5: Verify tests and commit**

Run: `pytest backend/tests/test_opportunity_listing_api.py -v`
Expected: PASS.

```bash
git add backend/app/modules/opportunity/router.py backend/openapi.json frontend/src/generated/api-schema.ts backend/tests/test_opportunity_listing_api.py
git commit -m "feat(opportunity): add on-demand liveness and JD extraction endpoints and sync API contracts"
```

---

### Task 9: Frontend Listing Health & Liveness Presentation

**Files:**
- Modify: `frontend/src/modules/opportunity/JobDetailPage.tsx` (or Opportunity detail component)
- Modify: `frontend/src/modules/opportunity/OpportunityIntelligenceCard.tsx`
- Test: `frontend/src/modules/opportunity/OpportunityIntelligenceCard.test.tsx`

**Interfaces:**
- Consumes: `opportunity.intelligence.listing_health`
- Produces: Diagnostic health badge, liveness indicator, and "Check Liveness" button using `@/core/ui` tokens

- [ ] **Step 1: Write frontend component test for listing health display**

Verify listing health badge and liveness status render without errors.

- [ ] **Step 2: Implement UI component using design tokens**

Show:
- Health badge (green/amber/red based on score).
- Liveness indicator (`Live`, `Likely Closed`, `Expired`).
- "Tazele" / "Yenile" button calling `POST /api/opportunities/{id}/liveness` and invoking `invalidateAfter(["opportunity"])`.

- [ ] **Step 3: Run frontend tests**

Run: `npm --prefix frontend test`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/modules/opportunity/
git commit -m "feat(ui): present listing health and liveness status in opportunity detail"
```

---

### Task 10: Full Verification & Final Documentation Sweep

**Files:**
- Modify: `docs/integrations/career-ops.md`
- Test: Full backend test suites, frontend tests, and bounded live smoke tests

- [ ] **Step 1: Run full test suite with temporary PostgreSQL test DB**

Run:
```bash
docker run -d --name forkos-test-db-tmp -e POSTGRES_USER=lifeos -e POSTGRES_PASSWORD=lifeos -e POSTGRES_DB=forkos_test -p 5433:5432 postgres:16-alpine
DATABASE_URL=postgresql+asyncpg://lifeos:lifeos@127.0.0.1:5433/forkos_test backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
DATABASE_URL=postgresql+asyncpg://lifeos:lifeos@127.0.0.1:5433/forkos_test backend/.venv/bin/pytest backend/tests/test_career_ops*.py backend/tests/test_opportunity*.py -v
docker rm -f forkos-test-db-tmp
```
Expected: 100% PASS, 0 failures.

- [ ] **Step 2: Update documentation in `docs/integrations/career-ops.md`**

Document C3 extraction, liveness bridge, listing health signals, and CLI/API usage.

- [ ] **Step 3: Commit and finalize**

```bash
git add docs/integrations/career-ops.md
git commit -m "docs(career-ops): document C3 JD extraction, liveness bridge, and listing intelligence"
```
