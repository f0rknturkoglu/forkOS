# Implementation Plan: forkOS × career-ops — C2.1 Correctness & Canonical Merge Closure

## 1. Goal
Execute all 12 correctness and hardening fixes for C2 without introducing new features, without LLM dependencies, and without modifying canonical PostgreSQL ownership.

## 2. Tasks Breakdown

- [ ] **Task 1: Fix Upstream `location_filter` schema in `CareerOpsDiscoveryConfigBuilder`**
  - Update `CareerOpsDiscoveryConfigBuilder` in `backend/app/integrations/career_ops/targeting.py` to produce `{always_allow, allow, block, block_hard, strict}`.
  - Project Turkish cities, remote, European countries to `allow`/`always_allow`.
  - Project block words like US citizenship to `block_hard`.
  - Set `strict: False`.
  - Add compatibility unit tests & contract tests invoking pinned upstream `buildLocationFilter()` via node or direct assertions.

- [ ] **Task 2: Pinned Identity Verification & Runtime Readiness Gate**
  - Implement `CareerOpsRuntimeGuard` in `backend/app/integrations/career_ops/guard.py` (or shared verifier).
  - Verify package.json version matches lock, git commit matches lock, Node >= 18, required script exists.
  - Call `await guard.ensure_ready()` in `CareerOpsAdapter.reverse_scan()`.
  - Add fail-closed unit tests asserting runner is never invoked on version/commit mismatch.

- [ ] **Task 3: URL Boundary Validation & Strict Single-Document JSON Contract**
  - Validate offer URLs in `CareerOpsAdapter.reverse_scan()`: accept only `http://` and `https://` with netloc; quarantine/skip invalid URLs.
  - Enforce single JSON document: `json.loads(stdout.strip())`; fail with `CareerOpsInvalidOutputError` if stdout contains text before or after.
  - Add unit tests for JSON pollution and URL validation.

- [ ] **Task 4: Subprocess Cancellation & Child Reaping**
  - In `SubprocessCareerOpsRunner.run_script()`, catch `asyncio.CancelledError`, terminate and wait for child process.
  - Add unit test proving cancelled task terminates and reaps child process.

- [ ] **Task 5: Scan Completeness & Degradation Truthfulness**
  - In `CareerOpsAdapter.reverse_scan()`, if `cap_hit` is True or `capped_boards > 0` or `stopped_by_outage` or `dataset_degraded`: set `is_partial = True` with clear `partial_detail`.
  - Add unit tests for partial coverage signals.

- [ ] **Task 6: Deterministic Cluster Mapping & Cross-URL Ingestion Dedup**
  - In `backend/app/sources/career_ops_sources.py`, generate `cluster_key` using `forkjob_core.models.cluster_key(company, title, location)`.
  - Populate `extra["cluster_key"]` and `extra["forkjob"] = {"cluster_key": ckey}`.
  - In `backend/app/modules/opportunity/service.py`, ensure `ingest_jobs()` correctly looks up existing opportunities by cluster key across different URLs.
  - Add integration tests for cross-URL deduplication (Case 1: same role different URLs merge into 1 Opportunity; Case 2: different roles remain separate).

- [ ] **Task 7: Non-Destructive Ingest Refresh Semantics in `Opportunity` Service**
  - In `backend/app/modules/opportunity/service.py: _refresh_opportunity()`:
    - `description`: preserve existing if incoming is empty/None.
    - `remote`: preserve existing if incoming is unknown.
    - `published_at`, `deadline_at`: preserve existing if incoming is None.
    - `compensation`: preserve existing if incoming is empty/None.
    - `country`, `region`: preserve existing if incoming is empty/None.
    - `score`, `score_source`, `score_computed_at`: preserve existing unless incoming has a valid score.
    - `skill_match_ratio`: do not wipe out if incoming description is empty.
    - `raw`: merge non-destructively: preserve existing `raw["forkjob"]`, append/update `raw["career_ops"]` and `raw["sources"]`.
  - Add integration tests for rich->sparse and sparse->rich refresh.

- [ ] **Task 8: Worker Lease Catalog & Discovery Feature Flag Truthfulness**
  - In `backend/app/worker/jobs.py`: include career-ops sources in `_source_catalog()` when career-ops discovery is enabled.
  - In `backend/app/integrations/career_ops/capabilities.py`: mark `discovery.reverse_ats` as `DISABLED` when `CAREER_OPS_DISCOVERY_ENABLED=false`.
  - In `CareerOpsAdapter.reverse_scan()`: reject execution when `discovery_enabled` is False with `CareerOpsConfigurationError`.
  - Add unit tests.

- [ ] **Task 9: Doctor Capability Count Truthfulness & Stronger Zero-Mutation Proof**
  - In `backend/app/integrations/career_ops/doctor.py`: compute `capabilities_available` dynamically.
  - In `backend/tests/test_career_ops_safety.py`: add test reaching the READY/probe path and proving zero PostgreSQL mutations.

- [ ] **Task 10: Documentation & Roadmap Alignment**
  - Update `docs/integrations/career-ops.md` to reflect actual `upstream.lock.json` schema and agreed roadmap (C1 -> C1.1 -> C2 -> C2.1 -> C3 -> C4 -> C5).

- [ ] **Task 11: Bounded Live Smoke & Verification**
  - Run full test suite with test database.
  - Run bounded live smoke test with pinned checkout.
  - Verify git diff and push to origin/main.
