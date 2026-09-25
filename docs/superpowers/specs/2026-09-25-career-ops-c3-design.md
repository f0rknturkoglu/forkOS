# forkOS × career-ops — C3 Architectural Specification: JD Extraction, Liveness & Listing Intelligence

**Date:** 2026-09-25  
**Status:** Approved for Implementation  
**Upstream Target:** `career-ops-hq/career-ops` @ `1.34.0` (`6326eb5d3804e8cb20d28acd5701a4e603a301f9`)  
**Baseline Remote Commit:** `e64be93` (Phase 0: C2.1 Final Seal)  

---

## 1. Executive Summary & Core Invariants

C3 integrates the **content extraction, zero-token link liveness verification, and listing intelligence** capabilities of the pinned `career-ops` engine into forkOS.

### The Non-Negotiable Invariants
1. **Zero LLM Calls:** All extraction, liveness checks, and listing quality assessments are 100% deterministic (using DOM selectors, regex, heuristics, and upstream JSON APIs). No LLM tokens (OpenAI, Anthropic, Gemini, Ollama, Hermes) are used in C3.
2. **Single Source of Truth:** forkOS PostgreSQL is the sole persistent store of opportunities and posting histories. Upstream files (`scan-history.tsv`, `portals.yml`) are ephemeral projections into runtime scratch spaces and are immediately deleted after execution.
3. **Listing Health ≠ Candidate Fit:** `Opportunity.score` strictly represents candidate-to-job match (derived from user profile, skills, and hard requirements). It MUST NOT be modified or diluted by listing quality signals. Listing health is presented as a separate diagnostic attribute (`listing_health`).
4. **Liveness Conservatism (`uncertain != expired`):** A transient failure (timeout, network error, WAF challenge, Cloudflare block) yields `uncertain` and NEVER hard-closes an opportunity. Closure requires confirmed `expired` status across all attached sources, confirmed over two successive evaluations separated by at least 12 hours.
5. **No Regex Scraping of CLI Output:** upstream CLI scripts that emit human prose or emojis (`check-liveness.mjs`) MUST NOT be regex-parsed. A repo-owned static Node bridge (`bridges/liveness.mjs`) imports upstream ES modules and outputs strict, typed JSON.
6. **No Browser Storms:** Chromium execution is bounded, sequential, on-demand, and cached with a 24-hour TTL. ATS APIs (Greenhouse, Lever, Ashby, Workday) resolve first with zero browser overhead.

---

## 2. Architecture & Anti-Corruption Layer

```text
                  ┌───────────────────────────────────────────────┐
                  │                 forkOS Web UI                 │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
                  ┌───────────────────────────────────────────────┐
                  │            FastAPI Opportunity API            │
                  └───────────────┬───────────────┬───────────────┘
                                  │               │
                                  ▼               ▼
          ┌───────────────────────────────┐  ┌─────────────────────────────┐
          │   OpportunityListingService   │  │   OpportunityIntelligence   │
          └───────────────┬───────────────┘  └──────────────┬──────────────┘
                          │                                 │
                          ▼                                 ▼
          ┌───────────────────────────────┐  ┌─────────────────────────────┐
          │       CareerOpsAdapter        │  │     Ephemeral Projection    │
          │  (SubprocessCareerOpsRunner)  │  │   (scan-history.tsv bridge) │
          └───────────────┬───────────────┘  └──────────────┬──────────────┘
                          │                                 │
           ┌──────────────┴───────────────┐                 │
           ▼                              ▼                 ▼
┌──────────────────────┐      ┌──────────────────────┐ ┌───────────────────┐
│ browser-extract.mjs  │      │ bridges/liveness.mjs │ │ detect-reposts.mjs│
│   (upstream CLI)     │      │  (repo-owned bridge) │ │  (upstream CLI)   │
└──────────────────────┘      └──────────────────────┘ └───────────────────┘
```

### 2.1 Static JSON Bridge: `bridges/liveness.mjs`
Upstream's `check-liveness.mjs` prints styled CLI text (`✅ active`, `❌ expired`). To ensure reliable, unbreakable integration, forkOS introduces a dedicated bridge inside `backend/app/integrations/career_ops/bridges/liveness.mjs`.

* **Imports:**
  - `checkLivenessViaApi` from `../.vendor/career-ops/liveness-api.mjs`
  - `checkUrlLivenessWithFallback`, `newLivenessPage` from `../.vendor/career-ops/liveness-browser.mjs`
  - `rejectPrivateOrInvalid` from `../.vendor/career-ops/liveness-browser.mjs`
* **Invocation:**
  `node bridges/liveness.mjs <url> [--timeout <ms>] [--no-fallback]`
* **Contract Output (stdout, exit 0):**
  ```json
  {
    "url": "https://boards.greenhouse.io/example/jobs/12345",
    "status": "active",
    "code": "greenhouse_api_ok",
    "reason": "ATS API returns the posting (live)",
    "method": "api",
    "checked_at": "2026-09-25T20:25:00Z"
  }
  ```
* **Error Handling:**
  Any unhandled crash or invalid input outputs structured error to stdout/stderr:
  `{"status": "uncertain", "code": "bridge_error", "reason": "...", "method": "bridge"}` with exit code 1.

### 2.2 Ephemeral Projection for Repost Detection
To evaluate repost frequency across the ecosystem:
1. `OpportunityListingService` queries PostgreSQL for all `Opportunity` and `OpportunitySourceObservation` records from the past 90 days.
2. In a temporary scratch directory inside `CareerOpsAdapter.runtime_dir`, it formats these records as `data/scan-history.tsv` (`url\tfirst_seen\tportal\ttitle\tcompany\tstatus\tlocation\t...\tnormCompany`).
3. Executes `node detect-reposts.mjs --window 90` via `SubprocessCareerOpsRunner`.
4. In a `finally:` block, `data/scan-history.tsv` is unconditionally unlinked.

---

## 3. Subsystem Specifications

### 3.1 Job Description (JD) Extraction
* **Upstream Script:** `browser-extract.mjs <url> --mode jd --max-chars 12000`
* **SSRF Guard:** upstream enforces `rejectPrivateOrInvalid` on the initial URL and on all page redirects/subresources. forkOS wraps this with preliminary domain validation.
* **ATS API Short-Circuit:** `browser-extract.mjs` natively checks Greenhouse, Lever, Ashby, and Workday CXS endpoints before launching Playwright, guaranteeing instant retrieval for >80% of job boards.
* **Canonical Description Promotion Policy:**
  - If canonical `Opportunity` has no description or has a stub (< 200 chars), and extraction produces substantive content (`len(text) >= 200`), promote the extracted text to `Opportunity.raw["description"]`.
  - Update `Entity.search_text` via `touch_entity` to ensure the new JD content is instantly searchable via PostgreSQL `immutable_unaccent()` and full-text search.
  - Store extraction metadata in `OpportunitySourceObservation.enrichment`:
    ```json
    {
      "jd_extracted_at": "2026-09-25T20:25:00Z",
      "jd_text_length": 4820,
      "jd_hash": "a1b2c3d4...",
      "jd_title": "Senior Backend Engineer"
    }
    ```

### 3.2 Liveness Verification Engine
* **Execution Flow:**
  1. Check cached liveness in `OpportunitySourceObservation.enrichment["liveness"]`. If `checked_at` is within 24 hours (TTL), return cached verdict.
  2. If stale or forced refresh: invoke `bridges/liveness.mjs`.
  3. Update `OpportunitySourceObservation.enrichment["liveness"]`.
* **Multi-Source Aggregation Policy:**
  - An Opportunity may have observations from `careerops:greenhouse`, `forkjob:rss`, and `manual`.
  - **Overall Status:**
    - If ANY attached observation is `active` -> `Opportunity.source_status = "active"`.
    - If observations are a mix of `expired` and `uncertain` -> `Opportunity.source_status = "active"`.
    - If ALL attached observations are `expired` -> Candidate for closure.
* **Safe 2-Step Closure Confirmation:**
  - On first observation of all-expired: mark `OpportunitySourceObservation.source_status = "likely_closed"`.
  - On second observation of all-expired, separated by at least 12 hours: set `OpportunitySourceObservation.source_status = "closed"`, `source_removed_at = now()`, and set canonical `Opportunity.source_status = "closed"`, `Opportunity.closed_at = now()`.
  - User shortlisted/applied listings (`status in ("shortlisted", "applied")`) retain their workflow status even when source closes; they are never deleted or trashed.

### 3.3 Listing Quality & Intelligence Signals
Listing quality evaluates whether an employer provides a transparent, legitimate, and complete vacancy posting.

* **Signals Computed:**
  - `jd_completeness`: `complete` (>1000 chars), `concise` (300-1000 chars), or `stub` (<300 chars).
  - `salary_transparency`: `transparent` (explicit numeric range), `unclear` (single bound or wide spread >50%), or `missing`.
  - `liveness_health`: `live` (active check within 48h), `unchecked` (never verified), or `at_risk` (likely closed).
  - `repost_frequency`: `none` (first sighting), `moderate` (reposted 2 times in 90 days), or `frequent` (reposted 3+ times).
* **Listing Health Score (0-100):**
  - Base: 100
  - Stub JD (<300 chars): -30
  - Missing salary: -15
  - Reposted >= 3 times: -20
  - Source closed/expired: -30
* **Isolation Rule:** `Opportunity.score` (candidate match) is NEVER touched. `OpportunityIntelligenceOut` is extended with `listing_health: ListingHealthOut`.

---

## 4. Database Schema & Migration

### 4.1 Schema Modification
Table: `opportunity_source_observation` (support table; exception to entity.id PK rule).
Add column:
- `enrichment`: `JSONB`, nullable=False, default=`{}`.

### 4.2 Alembic Migration Plan
- Migration name: `add_enrichment_to_source_observation`
- Rule enforcement (`postgres-alembic-guardian`):
  - Every DDL statement in a dedicated `op.execute()` call.
  - Safe default `{}`.
  - Reversible downgrade.

```python
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

---

## 5. Playwright Browser Provisioning & Doctor Readiness

* **Makefile Target:**
  ```makefile
  career-ops-browser-setup:
  	cd .vendor/career-ops && npx playwright install chromium
  ```
* **Doctor Health (`backend/app/integrations/career_ops/doctor.py`):**
  - Adds browser probe: checks if Playwright package is importable and Chromium binary is present.
  - Reports `browser_ready: bool`.
* **Capability Registry (`capabilities.py`):**
  - When `browser_ready` is True:
    - `discovery.liveness` -> `SUPPORTED`
    - `job.extract` -> `SUPPORTED`
    - `job.repost_analysis` -> `SUPPORTED`
  - When `browser_ready` is False:
    - Reports `UNAVAILABLE` with guidance: "Run 'make career-ops-browser-setup'".

---

## 6. Verification & Test Plan

1. **Unit Tests:**
   - Bridge output typing and error isolation (`test_career_ops_liveness_bridge.py`).
   - JD extraction normalization, length bounds, and promotion (`test_career_ops_extraction.py`).
   - Repost TSV projection formatting and cleanup (`test_career_ops_repost_projection.py`).
   - Listing health score computation and separation from candidate score (`test_opportunity_listing_health.py`).
2. **Database & Migration Tests:**
   - Migration upgrade/downgrade round-trip (`test_migrations.py`).
   - Multi-source observation liveness state transitions (`test_opportunity_liveness_service.py`).
3. **Bounded Live Smoke Tests:**
   - Greenhouse / Lever API-first liveness verification (<1 second, zero browser).
   - Headless Playwright extraction on mock/bounded public job board.

---

## 7. Approval Sign-off
This document serves as the canonical specification for C3. Once approved, the writing-plans skill will generate the fine-grained implementation tasks.
