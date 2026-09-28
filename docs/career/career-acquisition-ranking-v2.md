# Career Acquisition & Ranking v2 — implementation record

## Verdict

The canonical acquisition, deduplication, fast-score and evaluation-storage paths are implemented. This record must not be read as proof that every optional external source is operational: LinkedIn currently has no configured proxy or explicit direct-access permission in the local runtime. No live LinkedIn or Jooble requests were made during this change. Personal data was not used as test data; all migration tests ran on an isolated `forkos_test` database.

## Root causes and architecture

Previously `jobhunter:*` and CareerOps had separate source inventories and refresh policies. Reverse ATS discovery reused candidate-targeting filters, so legitimate jobs could be discarded before ranking. Coarse company/title/location clusters could merge different simultaneous postings. Fast scores and displayed skill percentages depended on forkjob-specific raw data, leaving CareerOps-only jobs unscored and treating configured keywords as CV evidence. Candidate and C4 deep evaluations wrote incompatible JSON into the same `opportunity.evaluation` column.

The new pipeline is acquisition → normalization → strong identity check → canonical fast score → evidence-bound candidate match → optional deep evaluation. A single catalog in `backend/app/sources/catalog.py` feeds queueing, periodic refresh, manual refresh and lease estimation. General refresh includes `careerops:boards`; reverse ATS, company scans and LinkedIn remain explicit/full opt-ins. Candidate relevance never blocks ingestion. The source-independent scorer writes `Opportunity.score` and its algorithm/config revision; a bounded cursor backfill refreshes old rows without fetching external data. `Opportunity.skill_match_ratio` now derives from verified candidate context against canonical requirements, not `raw.forkjob.reasons`. Unknown requirements do not count as proven gaps; insufficient evidence remains `NULL`. The detailed match, evidence coverage, candidate revision and listing fingerprint live under `raw.candidate_match`.

Identity resolution requires a stable source ID, canonical URL, provider requisition ID or sufficiently specific corroborating evidence. A coarse cluster is only a lookup bucket. Source observations remain the provenance record, and a partial/failed run still cannot close missing jobs. Existing user-owned statuses, applications, notes, CV links and events are not rewritten by the v2 code path.

## Evaluation and migration safety

`0074_forkjob_identity` migrates persisted `jobhunter:*` identities to `forkjob_core:*` across opportunity, observation, source-run, batch and stored setting references. Collision history is retained in observation enrichment rather than dropped. `0075_split_evaluations` classifies known legacy JSON shapes into `candidate_evaluation` or `deep_evaluation`, retaining the original payload in the mapped legacy column. Unknown JSON remains intact. Downgrade refuses to discard a newer split evaluation. Candidate and deep evaluation writers/readers, browse filters, analytics, application-package checks and interview intelligence now use their distinct fields. Their staleness checks are independent.

These migrations were first tested against isolated data. Before applying them to the personal runtime, a verified custom-format database backup was saved at `backend/backups/pre-career-v2-20260928.dump` (97 MB; archive list and source/destination SHA-256 checked). The live database advanced from `0073` to `0075`, then the rebuilt API and web containers passed health checks. A local-only, 500-row-batch backfill refreshed 29,908 existing listings; all 30,521 current job rows now carry the canonical fast-score version and candidate-match metadata. The temporary in-container backup copy was removed after verifying the retained host backup.

## Recall and source coverage

Reverse ATS targets use unrestricted title/location acquisition filters; candidate scoring happens after persistence. The default reverse scan window is 30 days and the tenant bound is 500, with Workday's more cautious limit retained. The pinned CareerOps checkout exposes 89 provider files and 4 optional plugins; those numbers are installed capabilities, **not** 89 active acquisition feeds. Public-board and verified-company targets are projected from forkOS configuration, and the UI reports configured targets and unique versus overlapping CareerOps contributions separately.

Before v2, installed CareerOps provider capability was not represented by a single scheduled source catalog: `careerops:boards` could be omitted from general refresh despite the pinned package's 89 providers. After v2, the live UI reports 27 configured public-board targets in the general `careerops:boards` source and 39 tracked-company targets in explicit/full scans; the 4 optional plugins remain unconfigured. This is a configured-target count, not a promise of 66 successful live feeds or 89 active sources.

The provider bridge now respects bounded target `max_pages` up to 12, retains a 40-request per-target guard and a 5,000-offer global bound, and marks an exact or exceeded result limit as partial. Target receipts include `cap_hit`, requested page cap, request count and result limit; a partial run's detail names capped targets. Those are request and result metrics, not a claim that upstream providers expose a reliable pages-fetched count. The portal registry's existing page/offer limits remain in place where the source's robots rules, rate sensitivity or detail-page cost require them. Broadly removing these bounds would not be a truthful recall improvement.

Disabled portal audit:

| Portal | Classification | Decision |
| --- | --- | --- |
| LinkedIn | Explicit opt-in, currently unconfigured | Keep `slow_optin`; require search profiles and proxy or explicit direct access. |
| Remote Rocketship, CryptoJobsList, Ruby on Remote | Honest access challenged/403 | Keep disabled; no bot-evasion path. |
| JustJoin.it, Nodesk | Current forkjob scraper route blocked or unverified; separate CareerOps public-board targets exist | Keep old adapters disabled; use the configured CareerOps targets, monitor their run receipts. |
| Landing.jobs | Current forkjob API route disallowed by robots | Keep adapter disabled; CareerOps target coverage must be judged by its own receipts. |
| DevITjobs, Honeypot | Deprecated endpoint or unreachable host | Keep disabled. |
| OfferZen | Login/reverse marketplace; no public posting feed | Keep disabled. |
| Consider a16z | Old Consider board contract removed | Keep disabled; the distinct a16z-speedrun CareerOps provider is not a drop-in replacement. |

## LinkedIn diagnosis

Read-only inspection of existing source-run history showed repeated proxy-configuration errors followed by circuit-open errors. A configuration probe confirmed `FORKJOB_LINKEDIN_ALLOW_DIRECT=false` and no proxy-file environment variable in the running local API. This is the reproducible operational cause; parsing changes or automatic proxy bypass would not fix it. The scraper now checks for configured profiles before a proxy/JobSpy import error, keeps successful profile results when another fails, normalizes direct employer URLs/tracking parameters and handles nullish JobSpy values. Production JobSpy runs in a killable process per profile; source cancellation or timeout terminates its process group instead of leaving a network thread behind. Mocked tests cover success, partial and total failure, deduplication, URL preference, absent profiles, explicit access policy and child cancellation. JobSpy network scraping itself remains opt-in; it was not claimed to be live-verified.

## JD enrichment and UI semantics

Initial sparse listings receive a cheap score. The existing bounded, identity-checked JD extractor can later promote a substantive employer description. Promotion now refreshes fast score and candidate match; stored candidate and deep evaluation fingerprints then become stale independently. The UI calls the main score “hızlı uygunluk”, separate from listing health/quality and CV/profile match. An unknown match is shown as insufficient evidence, never as `0%`. The source screen distinguishes active, opt-in, partial/error and circuit-open states, last success, CareerOps target counts and unique overlap; LinkedIn's required opt-in configuration is explained inline.

## Changed areas

- Backend: source catalog and refresh callers; CareerOps bridge/targeting/adapter; forkjob_core LinkedIn parser and source adapter; opportunity identity, canonical scorer, candidate matching, browse, JD enrichment and evaluation services.
- Data: hand-written Alembic revisions `0074` and `0075`, with migration regression tests.
- Frontend: Forkjob Core naming/settings, opportunity score and match copy, shared source-health surface; generated API artifacts were regenerated for the renamed route.
- Tests: source scheduling, identity, acquisition, scoring, candidate evidence, LinkedIn isolation, browse, migration and evaluation separation.

## Validation and limitations

Local validation: isolated PostgreSQL `make test CO='docker compose'` passed with **2,504 passed, 13 skipped**. Frontend Vitest passed **1,189 tests in 165 files**. `npm run api:check`, Prettier, endpoint-coverage (2 unreferenced, threshold 3), dead-export (10, threshold 10), TypeScript and production Vite build passed. The targeted changed-path Ruff check passed; repository-wide Ruff remains red with 56 existing errors in older CareerOps code/tests (mostly import ordering), so it is not reported as passing. `git diff --check` passed. GitHub Actions were not run because the owner's quota is exhausted.

The live API, source catalog, source coverage, five-item opportunity browse and web root returned HTTP 200 after migration/backfill; API, database and web containers were healthy. The rebuilt Sources and Opportunities pages rendered in the browser at the normal width, and the opportunities layout at a 390px viewport had no document-level horizontal overflow. External limitations remain: LinkedIn needs an explicit local access/profile choice; individual provider pagination may cap upstream before forkOS sees an array, so a returned count below our limit is not proof of exhaustive provider coverage; blocked portals are not silently represented as live sources. Existing forkjob portal scraper page caps are configured per source, but do not yet all emit reliable pages-fetched/cap-hit metadata; their item totals alone should not be read as exhaustive coverage. No Jooble key was written to the repository or used for live requests.

Follow-up ideas outside this phase: source-specific pages-fetched telemetry where each adapter can expose it honestly; optional live smoke checks under a manually enabled flag; a user-approved LinkedIn access configuration and direct provider credential onboarding.
