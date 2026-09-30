"""NAV SSR vacancy state and Workindenmark's public Jobnet search service."""

from urllib.parse import parse_qs, urlencode, urlsplit

from ..models import WorkMode
from .base import ScraperPermanentError
from .batch2_public import PublicPagedScraper, build, resolve_text, safe_record, state_nodes
from .remotecom import flight_records, walk


class ArbeidsplassenScraper(PublicPagedScraper):
    source_key = "arbeidsplassen"
    label = "NAV Arbeidsplassen"
    base_url = "https://arbeidsplassen.nav.no/stillinger"
    transport = "official_ssr_state"

    def listing(self, html, url):
        for node in state_nodes(html):
            data = node.get("searchResult")
            if (
                isinstance(data, dict)
                and isinstance(data.get("ads"), list)
                and isinstance(data.get("totalAds"), int)
            ):
                rows = data["ads"]
                if not rows and data["totalAds"]:
                    raise ScraperPermanentError("NAV empty page before reported total")
                jobs = [j for r in rows if isinstance(r, dict) and (j := self.record(r))]
                offset = int(parse_qs(urlsplit(url).query).get("from", ["0"])[0])
                next_url = (
                    f"{self.base_url}?from={offset + len(rows)}&sort=published"
                    if rows and offset + len(rows) < data["totalAds"]
                    else None
                )
                if rows and not jobs:
                    raise ScraperPermanentError("NAV nonempty response without valid ads")
                return jobs, len(rows), next_url
        raise ScraperPermanentError("NAV missing searchResult schema")

    @safe_record
    def record(self, row, *, detail=False, records=None):
        identifier = row.get("id") if detail else row.get("uuid")
        if not identifier or row.get("status") != "ACTIVE":
            return None
        places = row.get("locationList") or []
        locations = [
            ", ".join(str(p[k]) for k in ["city", "municipal", "county", "country"] if p.get(k))
            for p in places
            if isinstance(p, dict)
        ]
        country = (
            "NO"
            if any(p.get("country") == "NORGE" for p in places if isinstance(p, dict))
            else None
        )
        mode = {
            "Hjemmekontor ikke mulig": WorkMode.ONSITE,
            "Delvis hjemmekontor": WorkMode.HYBRID,
            "Hjemmekontor": WorkMode.REMOTE,
        }.get(row.get("remoteOptions"))
        application = row.get("application") or {}
        languages = row.get("workLanguages") or []
        return build(
            self.source,
            row,
            url=f"https://arbeidsplassen.nav.no/stillinger/stilling/{identifier}",
            title=row.get("title"),
            company=(row.get("employer") or {}).get("name"),
            location="; ".join(dict.fromkeys(locations)),
            country=country,
            mode=mode,
            description=resolve_text(row.get("adTextHtml"), records or {}) if detail else None,
            posted=row.get("published"),
            updated=row.get("updated"),
            external_id=identifier,
            language=", ".join(languages) or None,
            facts={
                "Original source": row.get("source"),
                "Expiry": row.get("expires"),
                "Application deadline": application.get("applicationDueDate")
                or row.get("applicationDue"),
                "Application URL": application.get("applicationUrl") or row.get("sourceUrl"),
                "Employment type": row.get("engagementType"),
                "Workload": ", ".join(row.get("extent") or []),
                "Workload percentage": row.get("jobPercentage"),
                "Language": ", ".join(languages),
                "Work model": row.get("remoteOptions"),
                "Occupation": row.get("jobTitle"),
            },
        )

    def detail(self, html, url):
        records = flight_records(html)
        for root in records.values():
            for node in walk(root):
                if isinstance(node.get("adData"), dict):
                    return self.record(node["adData"], detail=True, records=records)
        return None


class WorkInDenmarkScraper(PublicPagedScraper):
    source_key = "workindenmark"
    label = "Workindenmark"
    base_url = "https://workindenmark.jobnet.dk/bff/FindJob/Search"
    transport = "official_public_jobnet_json"

    @property
    def listing_urls(self):
        return [self.base_url + "?resultsPerPage=50&pageNumber=1&orderType=PublicationDate"]

    async def read_listing(self, client, url):
        # Same static anti-CSRF header as the public guest site; no cookie/session/login.
        data = await client.get_json(url, headers={"x-csrf": "1"})
        return self.listing(data, url)

    def listing(self, data, url):
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("jobAds"), list)
            or not isinstance(data.get("totalJobAdCount"), int)
        ):
            raise ScraperPermanentError("Workindenmark missing public jobAds schema")
        rows = data["jobAds"]
        if not rows and data["totalJobAdCount"]:
            raise ScraperPermanentError("Workindenmark empty page before reported total")
        jobs = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            job = build(
                self.source,
                r,
                url=r.get("jobAdUrl")
                or f"https://workindenmark.jobnet.dk/find-job/{r.get('jobAdId')}",
                title=r.get("title"),
                company=r.get("hiringOrgName"),
                external_id=r.get("jobAdId"),
                location=", ".join(
                    str(x) for x in [r.get("postalDistrictName"), r.get("country")] if x
                ),
                country="DK" if r.get("country") == "Danmark" else None,
                description=r.get("description"),
                posted=r.get("publicationDate"),
                facts={
                    "Application URL": r.get("jobAdUrl"),
                    "Application deadline": r.get("applicationDeadline"),
                    "Occupation": r.get("occupation"),
                    "Workload": "Part-time"
                    if r.get("workHourPartTime") is True
                    else "Full-time"
                    if r.get("workHourPartTime") is False
                    else None,
                    "Board context": "English-language Danish vacancies; requirements remain in employer text",
                },
            )
            if job:
                jobs.append(job)
        if rows and not jobs:
            raise ScraperPermanentError("Workindenmark nonempty malformed jobs")
        query = parse_qs(urlsplit(url).query)
        page = int(query.get("pageNumber", ["1"])[0])
        size = int(query.get("resultsPerPage", ["50"])[0])
        query = {k: v[0] for k, v in query.items()}
        query["pageNumber"] = page + 1
        next_url = (
            self.base_url + "?" + urlencode(query)
            if rows and page * size < data["totalJobAdCount"]
            else None
        )
        return jobs, len(rows), next_url

    def needs_detail(self, job):
        return False  # Search already contains the full employer description.
