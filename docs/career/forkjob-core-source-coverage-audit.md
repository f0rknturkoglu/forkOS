# forkOS — Forkjob Core Native Source Coverage & Telemetry Audit

This document retains the historical 37-source and Batch 1 audits below. Current Batch 2 state on 2026-10-01: 62 Layer B entries, 49 enabled. Eight new sources are enabled; Workcamino and Relocantly are disabled by explicit site terms, and LinkedIn remains disabled by robots policy. The current audit in section 6 supersedes historical activation claims.
Every scraper conforms to the canonical `ScrapeTelemetry` contract defined in `backend/app/sources/base.py`.

---

## 1. Architectural Taxonomy

Native `forkjob_core` sources fall into four operational execution models:

1. **Paged API / Paged Search (12 sources):**
   - Query pagination parameters (`page`, `offset`, `pageIndex`, etc.).
   - Terminated when page limit reached (`max_pages`), API total count reached (`totalCount`, `totalPages`, `numberRecords`), or empty/no-more items returned.
2. **Sitemap / Offer-Capped (6 sources):**
   - Reads an XML sitemap or directory listing, sorts or caps URLs to `max_offers`, and scrapes individual detail pages.
   - Terminated when `max_offers` is reached or sitemap/listing is exhausted.
3. **Single Feed / Shallow Batch (18 sources):**
   - Fetches a single public JSON feed, RSS/Atom feed, or single SSR page.
   - Bounded by design (`pages_fetched=1`, `cap_hit=False`).
4. **Multi-Profile Dynamic Batch (1 source: LinkedIn):**
   - Executes multi-search matrix via isolated JobSpy guest runner.
   - Bounded by `results_wanted` per profile, tracked with granular profile telemetry metadata.

---

## 2. Canonical Telemetry Contract

Every source run produces or inherits structured `ScrapeTelemetry`:

```python
class ScrapeTelemetry:
    items_seen: int | None          # Total listings/cards seen across all pages
    items_returned: int | None      # Valid deduplicated Job items produced
    pages_fetched: int | None       # Number of HTTP pages/queries executed
    page_limit: int | None          # Configured page budget limit (if applicable)
    result_limit: int | None        # Configured item/offer budget limit (if applicable)
    cap_hit: bool | None            # True if crawl stopped because of a cap/budget
    stop_reason: str | None         # Reason why crawler stopped
    partial_reason: str | None      # Human-readable explanation if cap_hit is True
    metadata: dict[str, Any]        # Structured auxiliary metrics (e.g. profile counts)
```

---

## 3. Original 37-source baseline matrix

| # | Source Key | Label | Execution Type | Stopping Semantics | Cap Detection | Telemetry Fields Populated |
|---|------------|-------|----------------|--------------------|---------------|----------------------------|
| 1 | `arbeitnow` | Arbeitnow | Paged JSON API | `page == max_pages` or `has_more == False` | `page == max_pages and has_more` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 2 | `fourdayweek` | 4dayweek.io | Paged JSON API | `page == max_pages` or `has_more == False` | `page == max_pages and has_more` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 3 | `kariyernet` | Kariyer.net | Paged HTML Search | `page == max_pages` or no fresh jobs | `page == max_pages` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 4 | `eures` | EURES | Paged POST API | `page * rpp >= numberRecords` or `page == max_pages` | `page == max_pages and page * rpp < total` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 5 | `nofluffjobs` | No Fluff Jobs | Paged POST API | `page >= totalPages` or `page == max_pages` | `page == max_pages and page < totalPages` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 6 | `solidjobs` | SOLID.Jobs | Paged GET API | `page * size >= totalCount` or `page == max_pages` | `page == max_pages and page * size < total` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 7 | `bulldogjob` | BulldogJob | Paged GraphQL API | `page * size >= totalCount` or `page == max_pages` | `page == max_pages and page * size < total` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 8 | `web3career` | Web3.career | Paged HTML Table | `page == max_pages` or no fresh rows | `page == max_pages and fresh` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 9 | `jobtech` | JobTech (Platsbanken) | Paged GET API | `(page+1)*size >= total` or `page == max_pages` | `page == max_pages - 1 and (page+1)*size < total` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 10 | `hackernews` | HN Who is Hiring | Algolia Search API | `page + 1 >= nbPages` or `page == max_pages` | `page + 1 == max_pages and page + 1 < nbPages` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 11 | `relocateme` | Relocate.me | Paged HTML Listing | `page == max_pages` or no fresh cards | `page == max_pages and fresh` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 12 | `dailyremote` | DailyRemote | Paged HTML Listing | `page == max_pages` or no URLs | `page == max_pages` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 13 | `jobgether` | Jobgether | Paged GET API | `pagination.hasMore == False` or `page == max_pages` | `page == max_pages and pagination.hasMore` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 14 | `freelancermap` | Freelancermap | Paged HTML Listing | `page == max_pages` or no fresh objects | `page == max_pages and fresh` | `seen, returned, pages, page_limit, cap_hit, stop_reason` |
| 15 | `manfred` | Manfred | Sitemap Capped | `entries[:max_offers]` or sitemap exhaust | `len(sitemap_entries) > max_offers` | `seen, returned, pages, result_limit, cap_hit, stop_reason` |
| 16 | `tecnoempleo` | Tecnoempleo | Sitemap Capped | `entries[:max_offers]` or sitemap exhaust | `len(sitemap_entries) > max_offers` | `seen, returned, pages, result_limit, cap_hit, stop_reason` |
| 17 | `jobfluent` | JobFluent | Sitemap Capped | `len(jobs) >= max_offers` or sitemap exhaust | `len(jobs) >= max_offers` | `seen, returned, pages, result_limit, cap_hit, stop_reason` |
| 18 | `ticjob` | Ticjob | Sitemap Capped | `len(jobs) >= max_offers` or sitemap exhaust | `len(jobs) >= max_offers` | `seen, returned, pages, result_limit, cap_hit, stop_reason` |
| 19 | `dynamitejobs` | Dynamite Jobs | Sitemap Capped | `urls[:max_offers]` or sitemap exhaust | `len(sitemap_urls) > max_offers` | `seen, returned, pages, result_limit, cap_hit, stop_reason` |
| 20 | `bebee` | beBee | HTML Capped | `len(jobs) >= max_offers` or listing exhaust | `len(jobs) >= max_offers` | `seen, returned, pages, result_limit, cap_hit, stop_reason` |
| 21 | `gulftalent` | GulfTalent | Search Capped | `len(jobs) >= max_offers` or search exhaust | `len(jobs) >= max_offers` | `seen, returned, pages, result_limit, cap_hit, stop_reason` |
| 22 | `remoteok` | RemoteOK | Single Feed API | Single response payload (capped by server to 100) | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 23 | `remotive` | Remotive | Single Feed API | Single `/api/remote-jobs` response | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 24 | `himalayas` | Himalayas | Single Feed API | Single `/jobs/api` response | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 25 | `workingnomads` | Working Nomads | Single Feed API | Single `/jobs/api` response | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 26 | `jobicy` | Jobicy | Single Feed API | Single `/api/v2/remote-jobs` response | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 27 | `jobspresso` | Jobspresso | Single RSS Feed | Single `/feed` XML payload | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 28 | `realworkfromanywhere` | Real Work From Anywhere | Single RSS Feed | Single RSS XML payload | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 29 | `weworkremotely` | We Work Remotely | Category RSS Feeds | Category RSS XML payloads | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 30 | `consider-sequoia` | Sequoia Portfolio | Single Board API | Single `/api-boards/search-jobs` response | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 31 | `wellfound` | Wellfound | Single Listing | Single listing fetch | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 32 | `eurotechjobs` | EuroTechJobs | Single RSS Feed | Single RSS XML payload | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 33 | `wearedevelopers` | WeAreDevelopers | Single RSS Feed | Single RSS XML payload | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 34 | `arcdev` | Arc.dev | Single SSR Page | Single `__NEXT_DATA__` listing extract | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 35 | `javascriptjobs` | JavaScript Jobs | Single SSR Page | Single listing HTML extract | `False` | `seen, returned, pages=1, cap_hit=False, stop_reason` |
| 36 | `customfeeds` | Custom User Feeds | Multi-feed Batch | Fetches configured RSS/Atom feed list | `False` | `seen, returned, pages, cap_hit=False, stop_reason` |
| 37 | `linkedin` | LinkedIn (Opt-in) | Multi-Profile Dynamic | `results_wanted` per search profile | Any profile returns `>= results_wanted` | `seen, returned, pages=None, result_limit, cap_hit, stop_reason, metadata` |

---

## 4. Invariants Upheld

1. **No Silent Cuts:** When a cap is hit, `cap_hit = True` is recorded in telemetry and forwarded to the source run status (`partial = True`). This prevents missed-sync sweeps from closing active jobs that fell outside the crawl window.
2. **Truthful Pagination Reporting:** Single-page feeds never invent page counts (`pages_fetched=1`). Scrapers with opaque internal pagination (like JobSpy) report `pages_fetched=None`.
3. **Structured Metadata:** Dynamic multi-search sources (LinkedIn) attach explicit execution metrics (`profiles_attempted`, `profiles_succeeded`, `profiles_failed`) in `metadata`.
4. **End-to-End Persistence:** Scrape telemetry is persisted in PostgreSQL column `source_run.telemetry` (JSONB) and surfaced in `SourceRunOut` and `/api/sources/runs` and `/api/sources/health`.

## 5. Native Source Expansion — Batch 1 (2026-10-01)

### Acquisition and scheduling

All six keys are discovered through the existing Layer B class index and registered in `portals.yaml`; five are enabled, while `devitjobs` is truthfully disabled after local HTTP 403. Enabled sources use the normal general-refresh class, 720-minute interval, existing 180-second source budget, honest forkjob UA, robots respect, two-second host spacing and an **8 MiB decoded response bound** through the shared HTTP client. No browser, credentials, external candidate-data transmission, new dependency, database column or CI change.

| Source ID suffix | Current transport and discovery | Default bounds | Richness actually acquired | Date provenance |
|---|---|---|---|---|
| `germantechjobs` | GET `/api/jobsLight`; GET `/rss` joins full prose by canonical URL; GET `/api/jobWithUrl/<slug>` only for RSS misses | 1,000 offers; 20 missing-detail requests | Source `_id`, title/company, actual city, DE, workplace, explicit visa Yes/No/unknown, dedicated language, salary, technologies, experience, employment, remote scope, requirements/responsibilities, application URL | `activeFrom` is activation/republication, conservatively **updated**, not original employer publication; `updatedAt` fallback; missing → discovered |
| `swissdevjobs` | Same verified public JSON + RSS contract | Same | Same fields with CH and source CHF salary | Same |
| `devitjobs` | Current Netherlands board; shared contract parser. Local `/robots.txt`, `/`, `/en`, `/rss`, `/sitemap.xml`, `/api/jobsLight` all returned 403 | Same parser/config, disabled | **No successful local live acquisition.** Synthetic Netherlands contract fixture only; not represented as a frozen live response | Unknown live; same parser rules when transport recovers |
| `remotecom` | GET `/jobs/all?page=N`, inert SSR Next Flight `jobsData`, `currentPage`, `totalPages`; bounded SSR details, including UTF-8 byte-sized text references | 5 listing pages; 100 offers; 20 details | Stable slug suffix ID, company/title, actual global/country/continent/timezone hiring restriction, workplace, salary minor units (UI verified), publication, employment, travel, seniority, explicit visa bool/null, application URL; full description only for detail-enriched jobs | `publishedAt` → employer; `updatedAt` → updated; neither → discovered |
| `berlinstartupjobs` | 12 public categories (engineering, marketing, design/UX, operations, sales, product, HR, finance, internships, contracting, cofounders, other), `/page/N/`; JSON-LD details | 2 pages per category (24 listing requests); 500 offers; 20 details | Listing company/title, preview and actual skill/topic tags/category; detail stable numeric ID, date, actual location/country, remote label, employment, full description and any explicit salary | Detail `datePosted` → employer; listing has no full absolute date → discovered |
| `eustartups` | Real `/startup-jobs/` WPJobBoard, `/startup-jobs/page/N/`; `/job/<slug>/` JSON-LD | 3 listing pages; 150 offers; 20 details | Listing company/title/location/employment/remote wording; details numeric ID, actual country, absolute date, full description and explicitly labelled pay; domain does not determine EU region | Detail `datePosted` → employer; listing's month/day lacks a year and remains discovered |

### Live reconnaissance evidence

- GermanTechJobs and SwissDevJobs robots allow these JSON/RSS/detail surfaces for the honest UA. The old `/api/jobs` still returns `ENDPOINT Deprecated`; public frontend JavaScript identifies **different current routes**. RSS provides full text cheaply (460/475 DE and 197/198 CH URL matches in the first reconnaissance snapshot). The DE/CH root is a JS shell for this UA; Swiss details sometimes embed `window.__detailedJob`, but the current JSON contract is cheaper and consistent. The published sitemap is much larger and includes facets, so it is not the acquisition index. No 429 was observed.
- DevITJobs is **not dead**: its current public site/search view shows listings and dedicated language/visa/experience fields. The local runtime and host HTTP paths above consistently return 403, including the current JSON route. No login/CAPTCHA/UA impersonation/proxy bypass was attempted. This is the one unmet live target; the registry keeps it disabled with the current reason.
- Remote.com robots allow the jobs surface. The homepage holds selected groups; `/jobs/all` is the real paginated universe. Reconnaissance reported 6,244 entries / 313 pages, later 6,255; totals change during live collection. Global/location/timezone fields retain explicit restrictions. UI salary `11k–16k USD/year` matches structured 1,100,000–1,600,000 minor units. Ordinary HTTP supplies both listings and detail descriptions; no private GraphQL call is used.
- Berlin's homepage is a featured category directory, and `/page/2/` repeats that directory. The real category listings have 25 cards and their own pagination. RSS has only 12 recent items and is insufficient for board coverage. Public detail JobPosting has stable numeric identifier/date/location/employment; skill tags are read only inside the job's own tag block, never the global sidebar. Robots allow category/detail/feed surfaces.
- EU-Startups robots allow the actual jobs board and details. Editorial main-site RSS is not a jobs feed. Listing pages have WPJobBoard rows; details provide JobPosting. Worldwide/UK, USA and Ukraine locations were observed. Two “AI Tools … Comparison Guide” advertisements were incorrectly marked JobPosting: the narrow non-job guard rejects those promotional guide titles; no seniority, geography, language, stack or candidate-relevance filter is added. Source salary absence remains unknown.

### Telemetry and canonical evidence

- Every successful fetch returns `ScrapeBatch` with canonical telemetry. `pages_fetched` counts successful response retrievals (listing/feed/details), excluding robots and transport failures; separate metadata reports listing/detail counts. `items_seen` counts source entries/cards including malformed/duplicate entries; `items_returned` counts valid deduplicated jobs.
- Offer/page/detail bounds are explicit. `max_pages_reached`, `max_offers_reached` and `detail_budget_reached` set `cap_hit=True` and produce **partial** source runs; no missed-sync closure can follow an incomplete run. Natural exhaustion has no cap. A later-page/detail/feed failure retains acquired listings, includes errors and is partial. Total failure is error, never healthy empty. Unexpected JSON/Flight/HTML/RSS schema is rejected; recognized genuinely empty schemas are supported.
- Facts are deterministic `Source facts (<source>):` blocks inside descriptions. Missing visa is omitted; only explicit Yes/No is emitted. Dedicated language is preserved without guessing from posting/page language. Structured scope distinguishes Anywhere, Europe only, Germany only, multi-country and timezone windows. Unknown `remoteType` remains unknown. No currency conversion or annual-equivalent fabrication.
- Existing ingestion remains the owner of entities, canonical state, scoring and source observations. Full prose is retained over previews; source blocks from both observations are unioned and same-source fields refreshed deterministically. Both normalized and forkjob description paths preserve richness.
- Source-supported application URLs are carried through RawItem. Direct board→ATS URL matching requires a recognized **specific** ATS posting route plus identical company/title. Generic career/application roots and conflicting roles do not earn a cross-link merge. No title-only or coarse-cluster weakening.
- Existing scoring weights are unchanged. Explicit fact label recognition was added for visa refusal, English, Anywhere and geographic restrictions; original date provenance survives canonical fast scoring. A frozen fixture travels through native Job→RawItem→Opportunity→score→candidate matching and a distinct ATS observation on the isolated test DB.

### Fixture provenance

`backend/tests/sources/fixtures/native_batch1/README.md` records the capture rules. DE/CH fixtures are reduced real public JSON/RSS; Remote fixtures retain inert real Flight payloads; startup fixtures retain real cards/JobPosting. The Netherlands file is explicitly **synthetic**, because ordinary local HTTP could not capture it. Normal tests are offline; live tests require `live_network` and `FORKOS_RUN_LIVE_CAREER_TESTS=1`, with the documented DevITJobs 403 reported as xfail rather than green transport.

### Final bounded dogfood and canonical ingestion

Captured ordinary public responses on 2026-10-01 (local date); these verified receipts then passed through normal `poll_source` on an isolated test DB and the authorized additive personal sync. No reset or delete. Runtime below is network acquisition, not receipt replay.

| Source | Seen / returned | Runtime | Successful pages (listing/feed/detail) | Cap / status | Pre-ingestion strong overlap with career-ops / existing forkjob | New canonical personal rows |
|---|---:|---:|---:|---|---:|---:|
| GermanTechJobs | 477 / 477 | 40.94 s | 20 (1/1/18) | No; exhausted, success | 0 / 0 | 477 |
| SwissDevJobs | 198 / 198 | 6.35 s | 3 (1/1/1) | No; exhausted, success | 0 / 0 | 198 |
| DevITJobs NL | unavailable | 2.87 s | 0 | HTTP 403; disabled | unavailable | 0 |
| Remote.com | 100 / 100 | 50.86 s | 25 (5/0/20) | Yes; max offers, partial | 27 / 0 | 73 |
| Berlin Startup Jobs | 177 / 146 | 74.53 s | 36 (16/0/20) | Yes; detail budget, partial | 0 / 0 | 141 |
| EU-Startups | 51 / 49 | 46.39 s | 22 (2/0/20) | Yes; detail budget, partial | 0 / 0 | 49 |

Native unique against strong observed preexisting identities: DE 477, CH 198, Remote 73, Berlin 146, EU 49. This is an observed URL/application identity check, not proof of absence of differently linked equivalents. Berlin's 146 distinct source listings resolve to 141 canonical observations through existing company/title/location identity; all are scored. Total **938 new canonical rows**, **965 scored source observations**, from 970 acquired listings. Remote's 27 matches enrich existing career-ops rows rather than duplicate them. Source health confirms two success runs and three truthful partial runs, all with zero consecutive failures.

Richness counts: DE salary/language/country/visa/experience/employment 477 each, technology 475, explicit remote scope 17, application URL 432; 459 RSS descriptions plus 18 missing details. CH corresponding fields 198 each, remote scope 8, application URL 119; 197 RSS descriptions plus one detail. Remote salary 57, country 38, explicit visa 32, experience 94, scope 95, employment/travel 100, application URL 81; only 20 full descriptions and no dedicated language/technology field. Remote listing total was 6,263 during final collection; the configured 100 is a bounded sample. Berlin preserves 75 skill/topic lists, 20 detail country/employment records and 20 full descriptions; remaining records retain listing previews. EU preserves salary 2, country 47, scope 23, employment 49 and 20 full descriptions; two promotional guides were excluded. Missing fields stay unknown.

Examples: GermanTechJobs PAGNOS Cloud AI Engineer; SwissDevJobs Intelliact SRE; Remote.com Tru7 Plant Hire Controller (explicit restricted geography); Berlin Solarize Senior NodeJS and withyou Product Engineer; EU-Startups Ethos Software Engineer with explicit $150/hour. Senior/nontechnical/non-EU examples remain ingested because acquisition is coverage-first.

Validation: final relevant offline suite **196 passed, 8 skipped, 1 deselected**; gated live **5 passed, 1 xfailed** (documented DevITJobs 403). Broader backend validation before the final small parser/scoring refinements: **2,557 passed, 22 skipped, 1 deselected**. The deselected preexisting LinkedIn opt-in test contradicts the user's already-enabled local LinkedIn configuration; Batch 1 does not change it. Isolated receipt replay verifies acquisition→canonical score persistence and idempotent replay. Ruff on changed Python files and `git diff --check` pass. No CI workflow changed.


## 6. Acquisition Expansion — Batch 2 (2026-10-01)

### Verified access and limits

Recon used the honest `forkjob/0.1` user agent and public pages, robots, terms and documented public APIs. No login, challenge solving, identity spoofing, private API, credential, FreeHire CLI, account cookie or personal data was used. All new transports use fixed public host scope, redirect checks, an 8 MiB decoded response bound, normal shared retry/Retry-After handling, and at least two seconds between requests to a host. Read-only acquisition uses the existing SourceAdapter → worker → canonical ingestion → observations → scoring → source_run pipeline. No Job/schema/migration, scoring-weight or CI changes.

| Source | Access / identity and dates | Rich evidence / practical limit |
|---|---|---|
| Arbeidsplassen | Official public SSR Flight; UUID; employer publish/expiry dates. [NAV API terms](https://arbeidsplassen.nav.no/vilkar-api), [official feed contract](https://github.com/navikt/pam-public-feed/blob/master/README.md) | Public SSR fallback because official feed requires JWT. Full employer description, languages, workload, contract, remote options, expiry and apply URL on detail. 3×25 listings, 10 details. Never infer visa/English from Norway. |
| Workindenmark | Official Jobnet BFF public search; jobAdId UUID; ISO employer publication. [Official portal guide](https://www.workindenmark.dk/getting-started/finding-vacancies-in-denmark/use-our-job-portal) | Current public JS uses static `x-csrf: 1`; works without cookie/account/token. Full descriptions in 3×50 search batches, country/deadline/work hours; external employer apply URL or verified internal Jobnet route. Board orientation is not an English/visa requirement. |
| DEVjobs.at | SSR search cards + JSON-LD JobPosting; 32-hex detail ID and employer dates. [Terms](https://devjobs.at/page/agb) | Technologies, salary, contract, experience level, work model, full JD. Robots disallows query pagination and API: first 15 cards only, 10 details; always partial public window. |
| developerjobs.ch | Public paged SSR /en/ + JSON-LD, UUID, employer dates; RSS also verified | Separate from SwissDevJobs. Technologies, CHF annual salary, workload, employment, city/canton, apply link and full JD. TELECOMMUTE means remote possible, not worldwide eligibility. 3×50 cards + 10 details. |
| englishjobs.de | Public 16-state SSR listings; stable 16-hex card ID independent of signed clickout URL. [Public llms contract](https://englishjobs.de/llms.txt), [Terms](https://englishjobs.de/terms) | Company, location, preview, original board, preserved clickout URL. Date lacks year → discovered provenance. 2 pages per state (≤32), ≤640 jobs; disallowed clickout/detail routes never fetched. No invented full JD or sponsorship. |
| WorkationBase | Public SSR card state + JSON-LD; source slug, employer detail publish dates. [Private use notice](https://workationbase.com/impressum) | Explicit scope, timezone, salary, async flag, board visa bool and language tag; full detail/JD and apply link. 3×24 cards + 10 details. Board false flag is not employer visa refusal; posting language is not working-language requirement. |
| jumpinto.eu | Public root SSR `initialJobs` (128 full records); UUID; createdAt is board update, not employer publication | Full JD, technologies, experience tag, salary currency (period unknown), apply URL. Generic board visa/English benefits are attributed claims, excluded from employer-promise scoring. One root, ≤500, no prohibited API/filter queries. |
| FreeHire | Documented anonymous REST agent batch; public_slug/upstream ID with URL fallback; upstream posted_at vs created/updated provenance. [OpenAPI](https://freehire.me/openapi.yaml), [API docs](https://freehire.me/docs/api), [Terms](https://freehire.me/terms) | Full JD, technologies, seniority, remote geography, employment, explicit tri-state sponsorship, language, salary and original publisher/URL. Lower-authority meta evidence. Recent 7-day EU/UK/TR/NO/CH slice + global remote slice, 3×50 each, ≤300; depth offset+limit≤10000. No N+1 detail. |
| Workcamino | Public SSR shape was observed, but [terms](https://workcamino.com/en/legal/terms) explicitly prohibit scraping/bulk export | Disabled and runtime refusal before network. 50 recon records were discarded, not ingested. Original publisher/URL, copied JD and inferred labels were observable but are not active acquisition. |
| Relocantly | Public HTML/JSON-LD shape was observed, but [terms](https://relocantly.com/terms) explicitly prohibit automated scraping | Disabled and runtime refusal before network. 60 recon records were discarded, not ingested. Original LinkedIn apply URL observed without fetching it; inferred English/visa labels remain board evidence. |

Missing fields stay unknown. Source fact blocks preserve provenance without a new storage schema. Canonical native fields/descriptions are protected from conflicting lower-authority meta fields; a later native record upgrades meta-first canonical evidence. Contradictory aggregator visa labels cannot override native visa evidence. Different locations/application identities are not merged solely by similar title/company.

### Actual bounded default dogfood and canonical contribution

This table records the latest default run, not the 5-record smoke. Fetch receipts were passed once through the normal worker; no second network scrape was needed for ingestion. Request counts include detail requests but exclude robots and transient retries; runtime is measured wall time including pacing.

| Source | Enabled | Acquired | New canonical | Existing/in-run overlap | Pages/requests | Seconds | Outcome |
|---|---|---:|---:|---:|---:|---:|---|
| arbeidsplassen | yes | 75 | 75 | 0 | 13 | 30.52 | result_limit_reached; detail_budget_reached |
| workindenmark | yes | 150 | 150 | 0 | 3 | 6.75 | result_limit_reached |
| devjobsat | yes | 15 | 15 | 0 | 11 | 23.54 | robots_limited_listing_window; detail_budget_reached |
| developerjobsch | yes | 150 | 148 | 2 | 13 | 26.39 | result_limit_reached; detail_budget_reached |
| englishjobsde | yes | 619 | 619 | 0 | 31 | 62.64 | page_limit_reached |
| workationbase | yes | 70 | 70 | 0 | 13 | 49.23 | page_limit_reached; detail_budget_reached |
| jumpintoeu | yes | 128 | 85 | 43 | 1 | 4.67 | complete / exhausted |
| freehire | yes | 284 | 282 | 2 | 6 | 12.68 | page_limit_reached |
| workcamino | no (terms) | 0 (recon discarded) | 0 | 0 | 1 | 2.78 | robots_limited_listing_window; recon only |
| relocantly | no (terms) | 0 (recon discarded) | 0 | 0 | 13 | 26.43 | page_limit_reached; detail_budget_reached; recon only |

Active-source totals: **1,491 acquired, 1,444 new canonical, 47 existing/in-run merges**. JumpIntoEU resolves 43 strong pre-existing canonicals with careerops and/or forkjob_core observations; FreeHire resolves one pre-existing forkjob canonical and two total merges after the earlier Batch 2 sources were ingested. Developerjobs.ch has two in-run canonical collapses. No existing LinkedIn overlap was confirmed in the active receipts; this is not a claim of no overlap across the complete databases. Strong URL/application and compatible identity matching was checked; title/company similarity alone is not proof. Source observation records preserve each contributor and all final jobs use existing fast/candidate scoring. Seven partial runs persist truthful limits and cannot close unseen jobs; JumpIntoEU alone exhausted its complete public root. `/api/sources/health` confirms 7 partial + 1 ok.

### FreeHire accounting

Six agent-search requests, 300 rows seen, 284 unique transport identities, 282 new canonical and 2 payloads that did not create a new canonical. Persisted source_run metadata records `freehire_seen`, `freehire_unique`, `freehire_new_canonical`, `freehire_overlap`, `freehire_existing_strengthened` in historical telemetry. That old field did not measure material strengthening; historical persisted runs are left unchanged. Current runs instead emit `freehire_not_new_canonical`. Both `freehire_overlap` and `freehire_not_new_canonical` mean transport payloads that did not create a new canonical Opportunity, including an existing match or within-run collapse. `freehire_new_canonical + freehire_not_new_canonical` equals deduplicated payloads passed to ingestion (not rows seen). Empty ingestion emits zero counters. Last public rate headers were limit 300, remaining 299, reset 1; exact values retained without guessing reset timestamp semantics. Low remaining quota stops rather than bypasses. Recent total counts were 49,679 EU/UK/country slice and 21,595 remote slice, so cap is partial. Optional API key was unnecessary and never read or transmitted; no CLI dependency.

### LinkedIn Guest V2: blocked, not delivered as an active engine

[Current LinkedIn robots](https://www.linkedin.com/robots.txt) disallows all generic crawler access; specialized crawler rules also disallow `/jobs-guest/`. Actual robots body is frozen in the offline fixtures. No guest search, geo typeahead, detail or pagination endpoint was probed after this denial. No native V2 parser/fixtures were fabricated. **Native V2 is not implemented or live verified** under this batch's mandatory verified-public-transport rule. Registry disabled; current public policy denial also prevents launching retained JobSpy fallback. Existing profile schema and killable JobSpy subprocess/cancellation tests remain compatible.

Native usage 0, fallback network usage 0, geo resolution/pagination/detail enrichment not attempted, soft blocks/429s not observed (0 endpoint requests), one policy blocker. Direct/proxy environment flags cannot bypass robots. Robots retrieval failure fails closed for LinkedIn. Existing activation sections in the v2/v2.1 documents are historical and superseded. Future public permission/transport change would require separate recon before native V2 work.

### Tests, privacy and closure

Frozen fixtures contain reduced actual public listing/detail/state/API shapes, optional/malformed records, exact robots, provenance and limits. Offline tests cover all ten source parsers, both terms blockers, registry discovery, salary/visa/language truth, detail budgets, later-page/detail failure preservation, API bounds/rate headers/no credentials, native-vs-meta conflict protection, strong canonical overlap and distinct identity separation. Redirect tests reject foreign/private hosts, userinfo and non-public ports before follow; gzip decoded-body bounds are tested. Broader backend suite: **2,612 passed, 33 skipped** against isolated PostgreSQL, with live tests gated. Final focused source/LinkedIn/canonical/security tests: **66 passed**. Explicit gated live suite: **8 passed, 3 xfailed** (LinkedIn robots, Workcamino terms, Relocantly terms). Replaying all eight actual public receipts twice against the isolated test DB passed: second ingestion added zero canonical rows. The final pagination repeat guard is covered by the focused suite. No personal DB was reset or used for fixtures/tests. Public live acquisitions were additive normal ingestion only. No new package, model/migration, frontend, API contract, hosted service, telemetry or CI change. Existing unrelated UI/doctor changes remain outside the Batch 2 commit.


## 7. Batch 1 + Batch 2 Closure Hygiene

Baseline: `74f07bc87a14ab56ff36c83aa71712aeae11eb16`. Acquisition and historical dogfood counts above are unchanged.

- **Catalog vs runnable:** PortalSource exposes registry `enabled` as `runnable`, plus existing registry status as `unavailable_reason`; other adapters default to runnable. LinkedIn remains catalogued/configurable, class `slow_optin`, opt-in true, runnable false under the current verified robots policy. Catalog API exposes both fields; the UI retains its catalog row.
- **Implicit refresh:** critical/general/full, system refresh and periodic general polling select runnable sources. Full Scan includes every runnable source, including runnable slow/opt-in EURES; it does not blindly queue every catalog row. Existing critical → normal → slow_optin ordering remains.
- **Explicit refresh:** a known unavailable source (single endpoint or explicit source_ids list) returns HTTP 409 with a concise registry-derived reason before stale-run reconciliation or queue/run mutation. A mixed list is rejected as a whole; unavailable explicit requests are never silently dropped. Unknown IDs still return 404.
- **Official classification:** government portal metadata declares critical for NAV Arbeidsplassen and Workindenmark. Existing explicit slow-optin overrides take priority, so EURES and LinkedIn remain slow_optin. Ordinary boards and FreeHire remain normal. Timeout constants and polling intervals are unchanged. Portal execution deadlines retain their pre-hygiene ID-based values (180 seconds for NAV/Workindenmark, 900 seconds for EURES/LinkedIn), independently of the corrected scheduling class.
- **FreeHire new runs:** `freehire_seen`, `freehire_unique`, `freehire_new_canonical`, `freehire_overlap`, `freehire_not_new_canonical`. No new `freehire_existing_strengthened` field is emitted; no historical migration or material field-diff claim. The worker computes counters even for empty payloads. Acquisition filters, pagination, quota handling, credentials, authority and identity/scoring behavior are unchanged.

Focused verification: **120 passed** across closure, scheduler, refresh, sync, source contract, Batch 2 acquisition and pipeline tests. Relevant forkjob/opportunity/career suites: **585 passed, 26 skipped**, offline only against isolated PostgreSQL. Tests cover generic disabled critical/normal/opt-in selection, actual catalog classes, LinkedIn 409 without a batch/run, EURES full-only selection and FreeHire mixed/all-new/all-overlap/empty exact payload accounting. No new sources, migration, UI redesign or CI changes.

Final additional closure suite: **14 passed**, including real three-payload ingestion (two new, one existing) and unknown-source 404 without queue mutation. Source workspace/scope frontend tests: **11 passed**. TypeScript, API runtime snapshot/generated-schema checks, targeted Ruff/Prettier and `git diff --check` passed; endpoint coverage remains 2 unreferenced routes below the existing threshold 3. Read-only live catalog verification confirms LinkedIn non-runnable, EURES runnable slow_optin, and both official government portals critical. No live acquisition was run.

Final scheduler/refresh/catalog/source-contract gate after verifying unchanged portal execution deadlines: **64 passed, 0 skipped**.
