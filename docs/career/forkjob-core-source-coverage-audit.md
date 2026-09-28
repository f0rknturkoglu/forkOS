# forkOS — Forkjob Core Native Source Coverage & Telemetry Audit

This document audits all 37 enabled native sources in `forkjob_core` (`portals.yaml` + opt-in `linkedin`).
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

## 3. Comprehensive Matrix of All 37 Native Sources

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
