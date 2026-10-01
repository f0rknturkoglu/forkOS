"""EURES (europa.eu/eures) — the EU's official job mobility portal.

Verified 2026-08-08. The largest single source in the project: 31 countries,
and postings that are on a public portal by mandate rather than by a company's
choice of ATS.

    POST https://europa.eu/eures/api/jv-searchengine/public/jv-search/search

Getting here took three captures, so the details are worth recording:

- **The old URL is dead.** `eures.europa.eu/eures-apps/searchengine/` returns
  404; the live app is an Angular SPA on `europa.eu` at `/eures/portal/jv-se/`.
- **The service name could not be guessed.** Eight plausible names
  (`jv-search-api`, `jvse-rest-api`, …) all returned 401, as did a deliberately
  invented one. The real name is `jv-searchengine` and the path is
  `/public/jv-search/search` — neither is derivable, and the search code sits
  in a lazy-loaded chunk rather than in main.js.
- **`Referer` and `Origin` are the headers that matter.** With them, an honest
  `forkjob/0.1` User-Agent gets a 200. No browser impersonation needed; the
  earlier 401/403s were missing headers, nothing more.
- **The `sessionId` in the captured body is not required** — the request works
  without it, so nothing session-bound is replayed here.
- **robots.txt permits this** and sets `Crawl-delay: 10`. That is five times
  the Layer B default, honoured via `min_interval: 10` in portals.yaml. Do not
  lower it.

Two things make this source unusually good:

- `numberRecords` gives the total up front, so paging stops exactly rather than
  running until a page comes back empty.
- **Occupations are filtered by ESCO URI, not by keyword.** Asking for ISCO
  `C25` targets the occupation itself, so results do not depend on a job title
  happening to contain the right word — which matters a great deal on a
  31-country portal where the titles are in 24 languages.

`creationDate` is a real publish timestamp, so `date_source` is `updated`.
"""

from __future__ import annotations

import html as html_lib
from dataclasses import dataclass, replace
from typing import Any

from ..geo import region_for
from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import html_to_text, parse_epoch_ms
from ..rich_text import enrich
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

BASE_URL = "https://europa.eu/eures"
SEARCH_API = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"
SEARCH_PAGE = "https://europa.eu/eures/portal/jv-se/search?lang=en"
DETAIL_URL = "https://europa.eu/eures/portal/jv-se/jv-details/{id}?lang=en"
FIXTURE = "data/fixtures/eures.sample.json"

#: europa.eu/robots.txt sets Crawl-delay: 10. Recorded so the number has a
#: source; enforced through portals.yaml.
CRAWL_DELAY_SECONDS = 10

#: ESCO/ISCO groups, taken from a live capture of the portal's own occupation
#: tree rather than from documentation.
ESCO_ICT_GROUPS = {
    "C25": "ICT professionals (whole branch)",
    "C251": "Software and applications developers and analysts",
    "C2511": "Systems analysts",
    "C2512": "Software developers",
    "C2513": "Web and multimedia developers",
    "C2514": "Applications programmers",
    "C2519": "Software and applications developers n.e.c.",
    "C252": "Database and network professionals",
    "C2522": "Systems administrators",
    "C2523": "Computer network professionals",
}
ESCO_URI = "http://data.europa.eu/esco/isco/{code}"

#: One branch covers the whole field, so one request per country is enough.
DEFAULT_OCCUPATIONS = ("C25",)
#: Target markets: Spain and Sweden first, then the second-priority countries.
DEFAULT_COUNTRIES = ("es", "se", "nl", "de", "pt", "ie", "pl")
DEFAULT_RESULTS_PER_PAGE = 50
DEFAULT_MAX_PAGES = 5

# ---------------------------------------------------------------------------
# Filter vocabularies
#
# Read out of the response's own `facets` block plus the portal's i18n bundle,
# so these are the real accepted values rather than guesses. Counts below are
# from 2026-08-08 across the seven target countries, ICT branch C25.
# ---------------------------------------------------------------------------

#: `requiredExperienceCodes`. The first two are the whole point of this project.
EXPERIENCE_CODES = {
    "none_required": "None required",
    "up_to_1_year": "Up to 1 year",
    "between_1_and_2_years": "1-2 years",
    "between_2_and_5_years": "2-5 years",
    "more_than_5_years": "More than 5 years",
    "NS": "Not specified",
}

#: `educationAndQualificationLevelCodes`.
EDUCATION_CODES = {
    "basic",
    "medium",
    "tertiary",
    "bachelor",
    "master",
    "doctoral",
    "not_classified",
    "NS",
}

#: `positionOfferingCodes` — contract type. `internship` and `apprenticeship`
#: are the entry-level ones.
OFFERING_CODES = {
    "internship",
    "apprenticeship",
    "contract",
    "directhire",
    "temporary",
    "temporarytohire",
    "contracttohire",
    "seasonal",
    "selfemployed",
    "volunteer",
    "oncall",
    "recruitmentreserve",
    "NS",
}

#: `positionScheduleCodes`.
SCHEDULE_CODES = {"fulltime", "parttime", "flextime", "NS"}

#: `euresFlagCodes`. The portal's own tooltip: "This blue flag means that the
#: employer is particularly interested in recruiting workers from other
#: European countries." That is the closest thing to a structured
#: relocation-friendly signal anywhere in this project — 154 postings had it.
EURES_FLAG_WITH = "WITH"

#: `otherBenefitsCodes`, decoded from the i18n bundle. Recorded for
#: completeness, but **not used**: filtering on the relocation-ish codes
#: (1/3/13/14) returned zero postings, and the portal's own tooltip admits
#: "the majority of vacancies do not provide any information about the extra
#: benefits offered". Filtering on it hides everything.
BENEFIT_CODES = {
    "1": "Accommodation included",
    "2": "Meals included",
    "3": "Relocation assisted",
    "4": "Travel expenses",
    "13": "Relocation assistance",
    "14": "Expatriate benefits",
    "15": "Other benefits",
}


@dataclass(slots=True)
class EuresSearch:
    """One filtered search. A run performs several and merges the results.

    Filtering at the source beats fetching everything and scoring it later:
    the whole ICT branch across the seven target countries is 38,329 postings,
    and at a 10s crawl delay that is days of requests for a haystack that is
    mostly senior roles. Two narrow slices carry nearly all the value.
    """

    name: str
    countries: tuple[str, ...] = DEFAULT_COUNTRIES
    occupations: tuple[str, ...] = DEFAULT_OCCUPATIONS
    experience: tuple[str, ...] = ()
    education: tuple[str, ...] = ()
    offering: tuple[str, ...] = ()
    schedule: tuple[str, ...] = ()
    eures_flag: str | None = None
    max_pages: int = DEFAULT_MAX_PAGES


#: What a default run fetches. Measured 2026-08-08 across the seven countries.
DEFAULT_SEARCHES = (
    # 1,226 postings. Exactly the target profile, and the portal states the
    # requirement itself rather than leaving it to be guessed from prose.
    EuresSearch(
        name="entry-level",
        experience=("none_required", "up_to_1_year"),
        max_pages=12,
    ),
    # 154 postings, small enough to take whole. The EURES flag means the
    # employer "is particularly interested in recruiting workers from other
    # European countries" — the only structured relocation signal in the
    # project, and it is exactly the constraint that matters most here.
    EuresSearch(name="eures-flag", eures_flag=EURES_FLAG_WITH, max_pages=5),
    # Internships and apprenticeships, which the seniority filter alone misses.
    EuresSearch(
        name="internship",
        offering=("internship", "apprenticeship"),
        max_pages=3,
    ),
)


class EuresScraper(ScraperBase):
    source_key = "eures"
    label = "EURES"
    base_url = BASE_URL

    def __init__(
        self,
        config: Any = None,
        *,
        searches: Any = None,
        countries: tuple[str, ...] | list[str] | None = None,
        results_per_page: int = DEFAULT_RESULTS_PER_PAGE,
    ) -> None:
        super().__init__(config)
        self.results_per_page = results_per_page
        self.searches = _load_searches(searches, countries)

    @property
    def scope(self) -> str:
        """Signature of the filters this run uses.

        Changing any of it means postings can drop out of the results while
        remaining perfectly open, so the close sweep must sit that run out.
        """
        parts = [
            "|".join(
                (
                    s.name,
                    ",".join(sorted(s.countries)),
                    ",".join(sorted(s.occupations)),
                    ",".join(sorted(s.experience)),
                    ",".join(sorted(s.education)),
                    ",".join(sorted(s.offering)),
                    ",".join(sorted(s.schedule)),
                    s.eures_flag or "",
                )
            )
            for s in self.searches
        ]
        return ";".join(sorted(parts))

    # -- network ------------------------------------------------------------

    def build_payload(self, search: EuresSearch, country: str, page: int) -> dict[str, Any]:
        """The search body. Every field name comes from a captured request."""
        return {
            "resultsPerPage": self.results_per_page,
            "page": page,
            "sortSearch": "BEST_MATCH",
            "keywords": [],
            "publicationPeriod": None,
            "occupationUris": [ESCO_URI.format(code=c) for c in search.occupations],
            "skillUris": [],
            "requiredExperienceCodes": list(search.experience),
            "positionScheduleCodes": list(search.schedule),
            "sectorCodes": [],
            "educationAndQualificationLevelCodes": list(search.education),
            "positionOfferingCodes": list(search.offering),
            "locationCodes": [country],
            "euresFlagCodes": [search.eures_flag] if search.eures_flag else [],
            # Deliberately empty: filtering on the relocation benefit codes
            # returns zero postings, because employers almost never fill them in.
            "otherBenefitsCodes": [],
            "requiredLanguages": [],
            "minNumberPost": None,
            "userPreferredLanguage": None,
            "requestLanguage": "en",
        }

    @property
    def headers(self) -> dict[str, str]:
        """Referer and Origin are required; the User-Agent stays honest."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://europa.eu",
            "Referer": SEARCH_PAGE,
        }

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        pages_fetched = 0
        items_seen = 0
        cap_hit = False
        page_limit = sum(search.max_pages * len(search.countries) for search in self.searches)

        for search in self.searches:
            for country in search.countries:
                for page in range(1, search.max_pages + 1):
                    payload = self.build_payload(search, country, page)
                    data = await self.isolate(
                        f"{country} page {page}", lambda payload=payload: client.post_json(
                            SEARCH_API, payload, headers=self.headers
                        )
                    )
                    if data is None:
                        break  # one slice failing must not sink the rest

                    pages_fetched += 1
                    page_jobs = self.parse(data)
                    items_seen += len(page_jobs)
                    # The searches overlap by design — an entry-level posting
                    # may also carry the EURES flag — so dedup across them.
                    jobs.extend(self.dedup_seen(seen, page_jobs))

                    total = data.get("numberRecords") if isinstance(data, dict) else None
                    if page == search.max_pages and isinstance(total, int) and page * self.results_per_page < total:
                        cap_hit = True

                    if not page_jobs or (
                        isinstance(total, int) and page * self.results_per_page >= total
                    ):
                        break

        stop_reason = "max_pages_reached" if cap_hit else "exhausted"
        self.record_telemetry(
            items_seen=items_seen,
            items_returned=len(jobs),
            pages_fetched=pages_fetched,
            page_limit=page_limit,
            result_limit=None,
            cap_hit=cap_hit,
            stop_reason=stop_reason,
            partial_reason="max_pages_reached" if cap_hit else None,
        )
        return jobs

    # -- pure parsing -------------------------------------------------------

    def parse(self, payload: Any) -> list[Job]:
        """Pure: search response in, Jobs out. Drives `--mock` and the tests."""
        if not isinstance(payload, dict) or "jvs" not in payload:
            raise ScraperPermanentError(
                f"eures: unexpected payload shape {type(payload).__name__}; "
                "expected an object with a 'jvs' list"
            )
        jobs: list[Job] = []
        for entry in payload.get("jvs") or []:
            if isinstance(entry, dict):
                job = self.build_job(entry)
                if job is not None:
                    jobs.append(job)
        return jobs

    def build_job(self, entry: dict[str, Any]) -> Job | None:
        posting_id = entry.get("id")
        title = (entry.get("title") or "").strip()
        if not posting_id or not title:
            return None

        employer = entry.get("employer")
        company = (employer.get("name") if isinstance(employer, dict) else None) or "?"

        country, city = _location(entry.get("locationMap"))
        description = html_to_text(html_lib.unescape(entry.get("description") or ""))

        languages = entry.get("availableLanguages")
        posting_languages = ", ".join(str(v) for v in languages) if isinstance(languages, list) else None

        posted_at = parse_epoch_ms(entry.get("creationDate"))

        return Job.build(
            url=DETAIL_URL.format(id=posting_id),
            source=self.source,
            layer=Layer.B,
            company=company.strip(),
            title=title,
            external_id=str(posting_id),
            location=city or country,
            city=city,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            # The feed says nothing about remote work, and inferring it from
            # prose in 24 languages would invent more than it found.
            work_mode=WorkMode.UNKNOWN,
            department=entry.get("positionOfferingCode") or None,
            description=enrich(description, self.source, {"Posting languages": posting_languages}),
            language=None,
            posted_at=posted_at,
            date_source=date_source_for(None, posted_at)[1],
        )


def _location(location_map: Any) -> tuple[str | None, str | None]:
    """(ISO country, city) from `locationMap`, e.g. {"ES": ["ES511"]}.

    The values are NUTS region codes, not city names. Translating them needs
    the portal's own i18n bundle (2129 `global.nuts.*` keys, a separate 260KB
    fetch), so the country is taken and the city left unknown rather than
    guessed. Region bucketing only needs the country.
    """
    if not isinstance(location_map, dict) or not location_map:
        return None, None
    country = next(iter(location_map))
    return (country.upper()[:2] if isinstance(country, str) else None), None


def _country_codes(values: Any) -> tuple[str, ...]:
    """Normalise country codes from YAML.

    Coerces rather than assuming strings: YAML 1.1 turns an unquoted `no`
    (Norway) into the boolean False, which crashed the whole source on
    `.lower()`. The codes are quoted in portals.yaml now, but a config typo
    should not be able to take a source down.
    """
    return tuple(str(v).lower() for v in (values or ()) if v is not None)


def _load_searches(searches: Any, countries: Any) -> tuple[EuresSearch, ...]:
    """Build the search list from portals.yaml, falling back to the defaults."""
    override = _country_codes(countries) if countries else None

    if not searches:
        if override:
            return tuple(replace(s, countries=override) for s in DEFAULT_SEARCHES)
        return DEFAULT_SEARCHES

    built: list[EuresSearch] = []
    for raw in searches:
        if not isinstance(raw, dict):
            continue
        built.append(
            EuresSearch(
                name=str(raw.get("name") or f"search-{len(built) + 1}"),
                countries=_country_codes(raw.get("countries") or override or DEFAULT_COUNTRIES),
                occupations=tuple(raw.get("occupations") or DEFAULT_OCCUPATIONS),
                experience=tuple(raw.get("experience") or ()),
                education=tuple(raw.get("education") or ()),
                offering=tuple(raw.get("offering") or ()),
                schedule=tuple(raw.get("schedule") or ()),
                eures_flag=raw.get("eures_flag"),
                max_pages=int(raw.get("max_pages") or DEFAULT_MAX_PAGES),
            )
        )
    return tuple(built) or DEFAULT_SEARCHES
