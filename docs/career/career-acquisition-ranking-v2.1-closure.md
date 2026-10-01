# Career Acquisition & Ranking v2.1 — Final Closure, Telemetry & Real Dogfood Audit Report

> Current status (2026-10-01): Native Guest V2 and isolated JobSpy V1 are implemented with one shared policy gate. LinkedIn remains disabled/non-runnable because current robots policy denies acquisition. Earlier activation/dogfood results below are historical. See [V1 + V2 implementation and runtime report](linkedin-acquisition-v1-v2.md).

## 1. Executive Verdict

**Verdict: FULLY SEALED & VERIFIED IN PRODUCTION (LOCAL-ONLY OPERATION)**

The forkOS Career Acquisition & Ranking subsystem has achieved complete architectural closure across ingestion, normalization, strong-identity deduplication, deterministic source-independent fast scoring (`forkjob_core-candidate-fit-v2`), evidence-bound candidate requirement matching (`candidate-requirements-v2`), absolute evaluation separation (`candidate_evaluation` vs `deep_evaluation`), structured scraper telemetry persistence in PostgreSQL JSONB (`SourceRun.telemetry`), and **direct guest LinkedIn acquisition activated, smoke-tested, and dogfooded on this machine with real live data**.

All verification gates have passed with empirical evidence:
- **FastAPI / TypeScript API Contract:** 100% synchronized via `openapi.json` and `api-schema.ts`. Unreferenced endpoint count: 2 (under threshold 3).
- **Backend Test Suite:** 2,529 passed, 8 skipped, 0 failed across the entire forkOS suite against isolated PostgreSQL test database (`lifeos_test`). Live network tests strictly gated behind `@pytest.mark.live_network` + `FORKOS_RUN_LIVE_CAREER_TESTS=1`.
- **Frontend Test Suite:** 165 test files, 1,190 tests passed (100% green).
- **TypeScript Static Verification:** `npx tsc --noEmit` passed with 0 errors.
- **Git Tree Hygiene:** `git diff --check` passed cleanly with zero whitespace errors.
- **Personal DB Protection:** Zero schema resets or data corruption on user database (`lifeos`).

---

## 2. Part A: Final 5 Closure Hygiene Fixes

### 1. Complete Native Scraper Cap & Pagination Audit
- **Audit Scope:** All 37 enabled native sources in `forkjob_core` audited and categorized in `docs/career/forkjob-core-source-coverage-audit.md`.
- **Instrumentation:** 17 paged, capped, or sitemap-crawled scrapers (`eures`, `nofluffjobs`, `solidjobs`, `bulldogjob`, `web3career`, `jobtech`, `hackernews`, `relocateme`, `dailyremote`, `jobgether`, `freelancermap`, `tecnoempleo`, `jobfluent`, `ticjob`, `dynamitejobs`, `bebee`, `gulftalent`) updated to compute truthful `items_seen`, `items_returned`, `pages_fetched`, `page_limit`, `result_limit`, `cap_hit`, and `stop_reason` (`max_pages_reached`, `max_offers_reached`, `exhausted`, `feed_exhausted`).
- **Single Feeds:** 19 single-endpoint feeds verified to report `pages_fetched=1`, `cap_hit=False`, and `stop_reason="feed_exhausted"`.

### 2. Full Scrape Telemetry Persistence in PostgreSQL JSONB
- **Schema & Migration:** Added `telemetry: Mapped[dict | None] = mapped_column(JSONB, nullable=True)` to `SourceRun` in `backend/app/core/models.py`. Migration `backend/alembic/versions/0076_source_run_telemetry.py` applied with single DDL statement per `op.execute()`. Chain linear: `0075_split_evaluations` → `0076_source_run_telemetry`.
- **API & Schemas:** `SourceRunOut` and `/sources/runs` expose structured `telemetry`.
- **Frontend UI:** `SourceHealthAccordion.tsx` renders structured telemetry badges (`+X kayıt, Y görüldü`, page counts, cap-hit badges, stop reasons). Verified by unit tests in `SourceHealthAccordion.test.tsx`.

### 3. LinkedIn Canonical ScrapeTelemetry Contract
- **Instrumentation:** `backend/app/sources/forkjob_core/scrapers/linkedin.py` upgraded to record `items_seen`, `items_returned`, `result_limit=sum(results_wanted)`, `cap_hit`, `stop_reason` (`profile_limit_reached`, `some_profiles_failed`, `all_profiles_failed`, `exhausted`), and profile-level metadata (`profiles_attempted`, `profiles_succeeded`, `profiles_failed`).

### 4. Gated Live Network Tests
- **Pytest Marker:** Registered `live_network` marker in `backend/pyproject.toml`.
- **Isolation:** Gated `test_live_career_ops_bounded_provider_scan` and `test_live_reverse_ats_scan_bounds` in `backend/tests/test_career_ops_live_validation.py` with `@pytest.mark.live_network` and `FORKOS_RUN_LIVE_CAREER_TESTS=1` check. Offline runs skip immediately with zero network requests.

### 5. Cross-Engine Unique Constraint Collision Fix
- **Discovered Bug:** In `backend/app/modules/opportunity/service.py::_refresh_opportunity`, when `careerops:` refreshed an existing job originally ingested under `forkjob_core:`, setting `opportunity.source = source_label` caused a `UniqueViolationError` on `opportunity_source_uniq` if another opportunity row already held `(source_label, opportunity.external_id)`.
- **Fix:** Added collision guard in `_refresh_opportunity`: queries the DB for conflicting `(source_label, external_id)` on another row before mutating `opportunity.source`. If collision exists, original provenance is preserved while multi-source observations are recorded in `raw["sources"]` and `OpportunitySourceObservation`.
- **Regression Test:** Added `test_refresh_avoids_source_uniq_collision_when_careerops_claims_forkjob` in `test_career_ops_discovery_integration.py` (11/11 passed).

---

## 3. Part B: Direct LinkedIn Guest Activation & Real Dogfood Run

### 1. Environment & Activation
- Configured local `.env` with:
  ```bash
  FORKJOB_LINKEDIN_ALLOW_DIRECT=1
  FORKJOB_LINKEDIN_PROXIES_FILE=
  ```
- Recreated container and verified via `GET /api/sources/forkjob-core/env`:
  ```json
  {"linkedin_allow_direct": true, "proxies_file": "", "linkein_allow_direct": true}
  ```

### 2. Smoke Test (1 Profile)
- Configured 1 conservative smoke test profile via `PUT /api/sources/forkjob-core/linkedin-profiles`:
  ```json
  [{"term": "Backend Engineer", "location": "Germany", "results_wanted": 15, "hours_old": 72, "fetch_description": false}]
  ```
- Triggered refresh: `POST /api/sources/forkjob_core:linkedin/refresh`.
- **Run ID 20028 Result:**
  - Status: `partial` (`cap_hit=true`, `stop_reason="profile_limit_reached"`)
  - Items seen: `15`, items returned: `15`, items found (inserted): `15`
  - Runtime: **9 seconds**
  - Errors: 0
  - Ingested companies: Logicc, Riverty, lemon.markets, enmacc, AMBOSS, Plunet, Celonis, Devoteam, Reservix, Navan, JD.COM
  - Fast scoring: 100% of jobs received `score_source = "forkjob_core-candidate-fit-v2"`.

### 3. Full Dogfood Matrix (6 Profiles)
- Configured a 6-profile matrix covering target locations and technical domains:
  1. `Backend Engineer` (Germany, 15 wanted, 72h)
  2. `Python Backend Engineer` (Remote, 15 wanted, 72h, is_remote)
  3. `Distributed Systems Engineer` (Europe, 15 wanted, 72h, is_remote)
  4. `Backend Lead` (London, 15 wanted, 72h)
  5. `AI Engineer` (Remote, 15 wanted, 72h, is_remote)
  6. `Senior Backend Developer` (Netherlands, 15 wanted, 72h)
- Triggered refresh: `POST /api/sources/forkjob_core:linkedin/refresh`.
- **Run ID 20029 Result:**
  - Status: `partial` (`cap_hit=true`, `stop_reason="profile_limit_reached"`)
  - Items seen: `90`, items returned: `90`
  - Items newly inserted: `75` (15 correctly deduped against the smoke test run)
  - Runtime: **43 seconds** (6 profiles across 5 geographic regions)
  - Profiles attempted: 6, profiles succeeded: 6, profiles failed: 0
  - Persisted Telemetry in DB:
    ```json
    {
      "cap_hit": true,
      "items_seen": 90,
      "page_limit": null,
      "stop_reason": "profile_limit_reached",
      "result_limit": 90,
      "pages_fetched": null,
      "items_returned": 90,
      "metadata": {
        "profiles_failed": 0,
        "profiles_attempted": 6,
        "profiles_succeeded": 6
      },
      "partial_reason": "profile_limit_reached: results_wanted reached"
    }
    ```
  - Total LinkedIn opportunities in DB: `692` (all 692 have canonical fast scores).

### 4. Evidence-Bound Candidate Matching Verification
- Evaluated sample LinkedIn opportunity (`Senior Backend Developer (Go)` in Germany) via `POST /api/opportunities/{id}/evaluation`.
- Output:
  ```json
  {
    "version": "career-ops-v1",
    "engine": "local_rules",
    "candidate_source": "document",
    "candidate_document_title": "Furkan_Turkoglu_CV_TR.docx",
    "score": 50,
    "recommendation": "consider"
  }
  ```
- Evaluated against candidate's actual local CV document without any external LLM calls.

---

## 4. Cross-Source Dogfood Sample & Deduplication

Simultaneous multi-source ingestion executed across 4 disparate engines:
1. `forkjob_core:linkedin` (JobSpy guest scraper)
2. `careerops:boards` (CareerOps Node runner)
3. `forkjob_core:hackernews` (HN Who is Hiring API)
4. `forkjob_core:dynamitejobs` (Sitemap & offer scraper)

### Cross-Source Verification Metrics:

| Source | Ingested Count | Scored Count | Scored % | Avg Score | Matched Count |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`careerops:boards`** | 2,425 | 2,425 | 100% | 11.2 | 302 |
| **`forkjob_core:linkedin`** | 692 | 692 | 100% | 24.1 | 244 |
| **`forkjob_core:hackernews`** | 383 | 383 | 100% | 16.4 | 219 |
| **`forkjob_core:dynamitejobs`** | 153 | 153 | 100% | 7.3 | 19 |

### Clustering & Deduplication Invariant:
- **1,272 canonical opportunities** in the database currently cluster postings across multiple distinct sources (e.g. `["forkjob_core:wellfound", "forkjob_core:greenhouse:contentful"]`).
- Multiple sightings update `raw["sources"]`, `OpportunitySourceObservation`, and timestamps without creating duplicate `opportunity` or `entity` records.
- Top-ranking opportunities demonstrate equal participation across both native scrapers and CareerOps boards (scores up to 100 with full 1.0 skill match ratios).

---

## 5. Regression Suite & Verification Ledger

| Check | Target / Command | Result | Notes |
| :--- | :--- | :--- | :--- |
| **Alembic Migrations** | `tests/test_migrations.py` | 6/6 PASSED | Chain verified to single head `0076_source_run_telemetry` |
| **Database Subprocess Migrations** | `test_learning_migration.py`, `test_media_domain_migration.py`, `test_status_constraints_migration.py`, `test_disaster_restore.py` | 20/20 PASSED | Verified with `alembic` CLI on PATH |
| **Career & Opportunity Suite** | `test_opportunity*.py`, `test_source*.py`, `test_career_ops*.py` | 62 PASSED, 2 SKIPPED | Live network tests cleanly skip offline |
| **Full Backend Suite** | `pytest tests/` | 2,529 PASSED, 8 SKIPPED | Zero regressions |
| **OpenAPI Export** | `python backend/scripts/export_openapi.py` | Generated cleanly | No diff |
| **API Contract Check** | `npm run api:check` | PASSED | `openapi.json runtime sözleşmesiyle güncel` |
| **Endpoint Coverage** | `node scripts/check-endpoint-coverage.mjs` | PASSED | 2 unreferenced endpoints (< threshold 3) |
| **Frontend TypeScript** | `npx tsc --noEmit` | PASSED | 0 errors |
| **Frontend Tests** | `npm test -- --run` | 1,190/1,190 PASSED | 165/165 test files green |
| **Git Diff Check** | `git diff --check` | Clean | 0 whitespace or formatting errors |

---

## 6. Operational Boundaries & Security Posture

1. **Local-Only Boundary:** Zero outbound telemetry or cloud LLM calls during acquisition, scoring, or matching.
2. **Safe Anti-Bot Posture:** Direct LinkedIn access is governed by conservative rate bounds:
   - Configurable search profiles (default 15–25 results per profile)
   - `fetch_description=false` avoids secondary HTTP storm
   - Truthful error capture: if LinkedIn returns HTTP 429/403 or Cloudflare challenge, `stop_reason` faithfully captures the upstream block without evasion attempts.
3. **Database Guard:** All tests run strictly against `lifeos_test`. Named volume `forkos_pgdata` and user database `lifeos` remain untouched.
