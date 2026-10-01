# LinkedIn Acquisition V1 + V2 Report

## Current state — 2026-10-01

**IMPLEMENTED / RUNTIME POLICY BLOCKED.** One source, `forkjob_core:linkedin`, owns acquisition and canonical observations. Its `portals.yaml` entry remains `enabled: false`: catalogued does not imply runnable. No scoring weights, canonical identity rules, migrations, other sources or CI were changed.

The live policy check at 13:26:34 UTC fetched only [robots.txt](https://www.linkedin.com/robots.txt). It denied `/jobs`, `/jobs/view/1`, `/jobs-guest/`, `/jobs-guest/jobs/api/seeMoreJobPostings/search`, `/jobs-guest/jobs/api/jobPosting/1` and `/jobs-guest/api/typeaheadHits`. Guest acquisition requests: **0**; JobSpy network calls: **0**. Code readiness is not live transport verification.

## Architecture and routing

`LinkedInScraper → LinkedInPolicyGate → Native V2 / JobSpy V1 → ordinary Job ingestion`.

`FORKJOB_LINKEDIN_TRANSPORT` is the single local selector:

- `auto` (default): native first; eligible failed profiles may use V1 recovery.
- `native`: V2 only.
- `jobspy`: V1 only.
- Unknown values fail closed.

Policy is dynamically parsed, cached in memory for 300 seconds, and checked before both transports and subsequent native requests. Unavailable, malformed, ambiguous or denied robots fails closed. Wildcard/end-anchor rules unsupported by the standard parser are conservatively treated as ambiguous. Diagnostics reads do not trigger network requests. Future permission still requires permitted live validation and explicit source activation.

Native useful partial results survive profile failures and fallback. Transport/schema failures and a guest shell can be eligible for recovery; login, challenge, 403, persistent 429, policy denial and exhausted run budget forbid fallback. Recovery retains native errors and soft-block counters: successful fallback cannot relabel the run healthy/exhausted.

## V1: isolated JobSpy

Installed `python-jobspy`: **1.1.82**, exposed at runtime; no package upgrade. Existing term, location, results_wanted, hours_old, is_remote and fetch_description profiles remain supported. The runner uses a child process, bounded wall time (at most 180 seconds and remaining run budget), process-group termination on timeout/cancellation, discarded stderr and structured warning counts. Required dataframe columns, title/company and LinkedIn identity are validated. Unverified empty output is degraded. Richer descriptions and explicit facts survive deduplication.

Proxy passwords are redacted. `FORKJOB_LINKEDIN_PROXIES_FILE` remains transport routing configuration; only the first configured proxy is used. It cannot bypass policy, authentication, challenge or enforcement. There is no rotating-IP recovery, impersonated crawler, account cookie or browser fallback. V1 internal HTTP request counts cannot be measured by this wrapper; diagnostics do not invent them.

## V2: native public guest transport

Card DTO parsing precedes Job conversion. Numeric LinkedIn IDs are primary identity; a canonical LinkedIn job URL is the fallback. Tracking parameters are removed. Repeated observations across profiles and transports merge into one source identity.

The deterministic search builder supports keywords, location/geoId, remote and hours filters. Bounded per-run geo caching performs one lookup per distinct location, exact name matching, and location-text fallback on ordinary lookup failure. Auth/enforcement responses stop acquisition.

Pagination advances by actual returned card count, counts unique profile identities, and stops at a verified empty structure, repeated page, result/page/request/wall budget or failure. Login, challenge, unknown schema, suspicious shell, content type, 403 and 429 are distinguished. A missing search structure is not healthy zero results.

Defaults: 180 seconds, 40 native acquisition requests, 10 pages/profile, profile result limit (50 when absent), 10 detail attempts. Native reads are bounded to 4 MiB, scoped hosts, timeout and cancellation. Detail enrichment respects fetch_description and selects missing-description cards in profile order; it does not import Opportunity scoring. JSON-LD takes priority for full descriptions and explicit dates/salary; exposed criteria and application/company links become source facts. Reposted recency is not an invented original publication date.

One controller spaces requests by a conservative provisional 4 seconds plus up to 0.2 seconds jitter. Retry count defaults to 2; exponential delays are bounded, server Retry-After is honored without truncation, and clean responses recover pacing. These defaults have **not** been tuned by permitted live guest smoke.

## Diagnostics and evidence

The existing source catalog carries preferred transport, cached policy state, native implementation availability, installed JobSpy version, fallback availability and last used transports. Source-run telemetry records policy, profile outcomes, native requests/pages/items, geo/detail outcomes, JobSpy contributions, fallback, soft blocks, schema failures and deduped items. Secrets, cookies and complete challenge pages are not logged.

`backend/tests/sources/fixtures/linkedin-v2/README.md` labels all new guest HTML/typeahead contracts **SYNTHETIC**, not live captures. Search endpoint and standard filter construction were corroborated against installed JobSpy source. DOM, geo payload, valid-empty and detail contracts remain provisional until legitimate live verification is possible.

Canonical tests cover V2 → RawItem → Opportunity → score/candidate matching, same-ID V1 ingestion preserving richer evidence, and LinkedIn/FreeHire/employer ATS strong application-URL overlap producing one Opportunity with multiple observations.

Validation: broader backend suite **2675 passed, 34 skipped**; final focused LinkedIn/Batch 2/canonical suite **107 passed**; source/scheduler/ingestion/scoring regression suite **252 passed, 18 skipped**. Gated live smoke (`FORKOS_RUN_LIVE_CAREER_TESTS=1`) **xfail** on current policy denial before either acquisition transport. OpenAPI snapshot check, TypeScript check, changed-file lint and whitespace checks passed before commit.
