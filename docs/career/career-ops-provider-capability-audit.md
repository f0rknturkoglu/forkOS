# CareerOps Provider Capability Audit & Matrix

## 1. Executive Summary

This document provides the definitive, code-verified capability audit of all **89 provider modules** installed in the `.vendor/career-ops/providers/` directory as of baseline `f3c4726233f3f2fc2a208b135401f63f3026504e`.

A common misconception is that all 89 providers are standalone, globally enumerable job boards ready to be queried without configuration. In reality, the providers represent diverse integration types: multi-tenant ATS adapters, enterprise single-employer career portals, search APIs requiring query parameters, boards requiring external API keys, tool utilities, and boards blocked by Cloudflare anti-bot in headless HTTP.

### Capability Summary Table

| Category | Description | Count | % of Registry | Status in forkOS |
| :--- | :--- | :---: | :---: | :--- |
| **Category A** | **Publicly Enumerable Job Boards** | **22** | 24.7% | Active in `careerops:boards` (or mirrored in `forkjob_core`) |
| **Category B** | **Target-Based ATS & Employer Adapters** | **62** | 69.7% | Active in `careerops:companies` / Reverse ATS when targets configured in `portals.yml` |
| **Category C** | **Auth / Token / API-Key Required** | **1** | 1.1% | Requires explicit external API key (`wttj` requires Algolia key) |
| **Category D** | **Plugin / Tool / Ecosystem Bridges** | **2** | 2.2% | Ecosystem utilities (`local-parser`, `telegram-channel`) |
| **Category E** | **Blocked / Anti-Bot / Deprecated** | **2** | 2.2% | Blocked in headless HTTP by Cloudflare (`landingjobs`, `justjoin`) |
| **Total** | **All Installed Providers** | **89** | **100%** | **Audited and accounted for** |

---

## 2. Category A: Publicly Enumerable Job Boards (22 Providers)

These providers query a public global feed, public RSS/Atom endpoint, or unauthenticated public listing API without requiring a tenant subdomain, board token, or pre-configured employer target.

| Provider ID | Source File | Upstream Feed / API | Notes |
| :--- | :--- | :--- | :--- |
| `4dayweek` | `4dayweek.mjs` | `https://4dayweek.io/api/jobs` | Public JSON API, 4-day work week roles |
| `a16z-speedrun-talent` | `a16z-speedrun-talent.mjs` | `https://speedrun-talent-network.com/api/v1/jobs` | Public OpenAPI listing endpoint |
| `agentic-jobs` | `agentic-jobs.mjs` | `https://agenticjobs.com/api/jobs` | Public JSON API for AI/agentic engineering roles |
| `arbeitnow` | `arbeitnow.mjs` | `https://www.arbeitnow.com/api/job-board-api` | European tech/remote public API |
| `cryptocurrencyjobs` | `cryptocurrencyjobs.mjs` | `https://cryptocurrencyjobs.co/index.xml` | Public RSS 2.0 Web3 feed |
| `echojobs` | `echojobs.mjs` | `https://echojobs.io/api/jobs` | Software engineering public API |
| `generalist-world` | `generalist-world.mjs` | `https://generalist.world/jobs` | Generalist career board |
| `getonbrd` | `getonbrd.mjs` | `https://www.getonbrd.com/api/v0/categories/programming/jobs` | Latin America / Remote tech JSON:API |
| `hackernews` | `hackernews.mjs` | `https://hn.algolia.com/api/v1/search_by_date` | Algolia query for "Ask HN: Who is hiring?" |
| `himalayas` | `himalayas.mjs` | `https://himalayas.app/jobs/api` | Public remote jobs API |
| `jobicy` | `jobicy.mjs` | `https://jobicy.com/api/v2/remote-jobs` | Public remote jobs API |
| `jobspresso` | `jobspresso.mjs` | `https://jobspresso.co/?feed=job_feed` | Public WordPress job feed |
| `larajobs` | `larajobs.mjs` | `https://larajobs.com/feed` | Public Laravel / PHP RSS feed |
| `manfred` | `manfred.mjs` | `https://www.getmanfred.com/api/v2/public/offers` | Developer-focused Spanish platform |
| `nodesk` | `nodesk.mjs` | `https://nodesk.co/remote-jobs/index.xml` | Public remote jobs XML feed |
| `nofluffjobs` | `nofluffjobs.mjs` | `https://nofluffjobs.com/api/search/posting` | Polish / CEE tech board with salary bands |
| `pythonorg` | `pythonorg.mjs` | `https://www.python.org/jobs/feed/rss/` | Official Python Software Foundation RSS |
| `remoteok` | `remoteok.mjs` | `https://remoteok.com/api` | Public remote jobs JSON API |
| `remotive` | `remotive.mjs` | `https://remotive.com/api/remote-jobs` | Public remote tech API |
| `weworkremotely` | `weworkremotely.mjs` | `https://weworkremotely.com/remote-jobs.rss` | Canonical remote jobs RSS feed |
| `workingnomads` | `workingnomads.mjs` | `https://www.workingnomads.com/jobsapi/job/_search` | Remote job search API |
| `yourator` | `yourator.mjs` | `https://www.yourator.co/api/v2/jobs` | Taiwan / APAC startup job board |

---

## 3. Category B: Target-Based ATS Adapters & Single-Employer Portals (62 Providers)

These providers require explicit target configuration in `portals.yml` (e.g. `careers_url`, `boardToken`, `company`, or `subdomain`). They cannot execute in a vacuum without knowing which company's tenant to scan.

### B1. Multi-Tenant ATS Platforms (32 Providers)
These adapters power forkOS **Reverse ATS** scans and company career site monitoring:

1. `ashby` — Ashby (`https://jobs.ashbyhq.com/<org>`)
2. `avature` — Avature enterprise ATS (`<company>.avature.net`)
3. `bamboohr` — BambooHR (`<company>.bamboohr.com/jobs`)
4. `beesite` — Beesite / Mercedes-Benz / DAX portal adapter
5. `breezy` — Breezy HR (`<company>.breezy.hr`)
6. `collage` — Collage HR (`<company>.collage.co`)
7. `comeet` — Comeet / Spark Hire (`<company>.comeet.com`)
8. `consider` — Consider curated talent network board adapter
9. `csod` — Cornerstone OnDemand (`<company>.csod.com`)
10. `eightfold` — Eightfold AI enterprise talent intelligence
11. `gem` — Gem careers site (`gem.com/careers/<company>`)
12. `greenhouse` — Greenhouse (`boards-api.greenhouse.io/v1/boards/<token>/jobs`)
13. `icims` — iCIMS enterprise career portal
14. `jibeapply` — Jibe / iCIMS next-gen applicant experience
15. `jobvite` — Jobvite (`jobs.jobvite.com/<company>`)
16. `join` — JOIN.com employer career widget
17. `joinup` — Joinup career site adapter
18. `lever` — Lever (`api.lever.co/v0/postings/<company>`)
19. `mokahr` — MokaHR (`app.mokahr.com/apply/<company>`)
20. `oraclecloud` — Oracle Cloud Recruiting / Taleo CE (`requisitions` API)
21. `personio` — Personio (`<company>.jobs.personio.de/xml`)
22. `phenom` — Phenom People TXM platform
23. `pinpoint` — Pinpoint ATS (`<company>.pinpointhq.com/postings.json`)
24. `radancy` — Radancy / TMP Worldwide enterprise career site
25. `recruitee` — Recruitee (`<company>.recruitee.com/api/offers/`)
26. `rippling` — Rippling ATS (`rippling.com/api/v1/companies/<token>/jobs`)
27. `smartrecruiters` — SmartRecruiters (`api.smartrecruiters.com/v1/companies/<token>/postings`)
28. `softgarden` — Softgarden (`<company>.softgarden.io/jobdb/rest/v1/`)
29. `successfactors` — SAP SuccessFactors Recruiting Marketing (`career?company=<id>`)
30. `teamtailor` — Teamtailor (`<company>.teamtailor.com/jobs.rss`)
31. `workable` — Workable (`apply.workable.com/api/v1/widget/accounts/<token>`)
32. `workday` — Workday (`<tenant>.myworkdayjobs.com/wday/cxs/...`)

### B2. Single-Employer Enterprise Portals (12 Providers)
These adapters target specific massive employers that run bespoke career endpoints:

33. `alibaba` — Alibaba Group Careers API
34. `amazon` — Amazon.jobs API (`amazon.jobs/en/search.json`)
35. `dassault` — Dassault Systèmes 3DS careers portal
36. `deutschebahn` — Deutsche Bahn Karriere API
37. `feishu-jobs` — Feishu / Lark / ByteDance internal careers
38. `garena` — Garena / Sea Group careers
39. `hecklerkoch` — Heckler & Koch career site
40. `ibm` — IBM Careers / Kenexa API
41. `meituan` — Meituan recruiting portal
42. `rheinmetall` — Rheinmetall career portal
43. `tencent` — Tencent Careers API
44. `tkms` — ThyssenKrupp Marine Systems careers

### B3. Regional / Structured Search Portals (18 Providers)
These require search query terms, location IDs, or category filters:

45. `arbeitsagentur` — German Federal Employment Agency (requires query/region)
46. `builtin` — BuiltIn tech hubs (requires city hub / phenom parameters)
47. `careerviet` — CareerViet (requires search criteria)
48. `flowxtra` — FlowXtra recruiting portal
49. `getro` — Getro VC network boards (requires network collection slug)
50. `glints` — Glints Southeast Asia (requires GraphQL query & country code)
51. `higheredjobs` — HigherEdJobs (requires category/institution ID)
52. `itviec` — ITviec Vietnam (requires search filter parameters)
53. `jobbankca` — Job Bank Canada (requires search query)
54. `jobstreet` / `92996157` — JobStreet / SEEK Asia (requires siteKey / location)
55. `mycareersfuture` — Singapore MyCareersFuture (requires search payload)
56. `remotli` — Remotli Swiss Remote (requires target config)
57. `senjob` — SenJob Senegal (requires search query)
58. `solidjobs` — SolidJobs DACH (requires category filter)
59. `thehub` — The Hub Nordic startup ecosystem (requires hub ID)
60. `themuse` — The Muse (requires level/category query)
61. `torre` — Torre.co (requires search genome payload)
62. `vdab` — VDAB Flanders public employment service (requires search query)

---

## 4. Category C: Auth / Token / API-Key Required (1 Provider)

| Provider ID | Source File | Required Credentials | Behavior without Credential |
| :--- | :--- | :--- | :--- |
| `wttj` | `wttj.mjs` | `PUBLIC_ALGOLIA_API_KEY_CLIENT` | Throws error immediately if key is missing; cannot run unauthenticated. |

---

## 5. Category D: Plugin / Tool / Ecosystem Bridges (2 Providers)

| Provider ID | Source File | Purpose | Notes |
| :--- | :--- | :--- | :--- |
| `local-parser` | `local-parser.mjs` | Offline document/HTML resume/posting parser | Utility adapter; not an external job board. |
| `telegram-channel` | `telegram-channel.mjs` | Telegram channel scraper | Requires public channel preview or Telegram session credentials. |

---

## 6. Category E: Broken / Blocked / Anti-Bot in Headless HTTP (2 Providers)

| Provider ID | Source File | Failure Mode in Headless HTTP | Status |
| :--- | :--- | :--- | :--- |
| `landingjobs` | `landingjobs.mjs` | Cloudflare Turnstile anti-bot interstitial; returns HTTP 403 on raw fetch. | Blocked without real browser rendering engine. |
| `justjoin` | `justjoin.mjs` | Cloudflare bot management on API gateway; returns 403 in node-fetch. | Blocked without real browser rendering engine. |

---

## 7. Integration Mapping into forkOS

In forkOS, the CareerOps integration is architecturally mapped to avoid false advertising and ensure deterministic execution:

1. **`careerops:boards` Source**:
   - Executes only Category A providers and configured public boards in `portals.yml`.
   - Included in the periodic **normal** sync schedule because it has bounded execution.
2. **`careerops:companies` / `careerops:reverse-ats` Sources**:
   - Executes Category B multi-tenant ATS adapters against tracked employer targets in `portals.yml`.
   - Classified as **slow_optin / full-only**; runs during explicit user-initiated "Tam tarama" sweeps.
3. **Truthful API Exposure (`/sources/career-ops/providers`)**:
   - Exposes exact breakdown: `providers_installed: 89`, `providers_publicly_enumerable: 22`, `providers_target_based: 62`, `providers_auth_required: 1`, `providers_tools: 2`, `providers_blocked: 2`.
   - Distinguishes between installed modules and actually configured targets.
