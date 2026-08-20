"""Discover company board tokens by probing ATS endpoints.

`discover` tries candidate tokens on every ATS platform until one returns a 200
with a non-empty job list. It never guesses at random — every candidate is
derived from the company name, and the probe actually hits the endpoint.

`verify` re-pings existing registry entries to confirm the board is still live.
"""

from __future__ import annotations

import asyncio
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from .models import Company, Region, utcnow
from .registry import KNOWN_ATS, UNDISCOVERABLE_ATS, Registry
from .sources.base import HttpClient, HttpConfig, PermanentError, TransientError


@dataclass(slots=True)
class ProbeResult:
    ats: str
    token: str
    url: str
    hit: bool = False
    job_count: int = 0
    error: str | None = None


#: Each ATS entry: (ats_key, url_template) where {token} is substituted.
#: The probe hits the URL and checks for a 200 with a recognisable key.
_PROBE_TARGETS: list[tuple[str, str, str]] = [
    # (ats, url_template, key_to_check_in_response)
    ("greenhouse", "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true", "jobs"),
    ("lever", "https://api.lever.co/v0/postings/{token}?mode=json", None),  # array
    ("ashby", "https://api.ashbyhq.com/posting-api/job-board/{token}", "jobs"),
    ("workable", "https://{token}.workable.com/spi/v3/jobs?state=published", "jobs"),
    ("smartrecruiters", "https://api.smartrecruiters.com/v1/companies/{token}/postings", "content"),
    ("recruitee", "https://{token}.recruitee.com/api/offers/", "offers"),
    ("personio", "https://{token}.jobs.personio.com/search.json", None),  # array or dict
    ("factorial", "https://{token}.factorialhr.com/api/v1/jobs", None),  # array or dict
]


def candidate_tokens(name: str) -> list[str]:
    """Generate plausible board tokens from a company name.

    Returns ordered candidates, most likely first. A single-word name like
    "Cabify" produces ["cabify"]. "Red Bull" produces
    ["redbull", "red-bull", "red_bull", "red", "bull"].
    """
    # Normalise: lowercase, strip accents, collapse whitespace.
    folded = unicodedata.normalize("NFKD", name.lower())
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    words = re.split(r"[\s\-_.,]+", folded.strip())
    words = [w for w in words if w]

    base = "".join(words)
    hyphenated = "-".join(words)
    underscored = "_".join(words)

    candidates = [base]
    if hyphenated != base:
        candidates.append(hyphenated)
    if underscored not in candidates:
        candidates.append(underscored)

    # Two-word names: try each word alone, but only if they're long enough.
    if len(words) >= 2:
        for w in words:
            if len(w) >= 4 and w not in candidates:
                candidates.append(w)

    # Common suffixes for companies that don't use their bare name.
    for suffix in ("careers", "jobs", "hq", "global", "tech", "com"):
        for prefix in candidates[:3]:
            candidate = f"{prefix}{suffix}"
            if candidate not in candidates:
                candidates.append(candidate)

    return candidates


async def probe_endpoint(
    client: HttpClient,
    ats: str,
    token: str,
    url_template: str,
    key: str | None,
) -> ProbeResult:
    """Hit one ATS endpoint and check if the response contains jobs."""
    url = url_template.format(token=token)
    result = ProbeResult(ats=ats, token=token, url=url)

    try:
        response = await client.request("GET", url)
    except TransientError as exc:
        result.error = str(exc)
        return result
    except PermanentError as exc:
        result.error = str(exc)
        return result

    if response.status_code != 200:
        result.error = f"HTTP {response.status_code}"
        return result

    try:
        data = response.json()
    except ValueError:
        result.error = "not JSON"
        return result

    jobs = _extract_jobs(data, key)
    if jobs is not None and len(jobs) > 0:
        result.hit = True
        result.job_count = len(jobs)
    else:
        result.error = "empty"
    return result


def _extract_jobs(data: Any, key: str | None) -> list[Any] | None:
    """Pull the job list out of an ATS response, or return None if unrecognised."""
    if key is None:
        # Response should be a list.
        if isinstance(data, list):
            return data
        # Some ATS wrap the list: {"jobs": [...]}, {"offers": [...]}
        if isinstance(data, dict):
            for candidate in ("jobs", "offers", "content", "data", "postings", "results"):
                if isinstance(data.get(candidate), list):
                    return data[candidate]
        return None

    if isinstance(data, dict):
        value = data.get(key)
        if isinstance(value, list):
            return value
    return None


async def discover_company(
    name: str,
    *,
    region: Region = Region.UNKNOWN,
    country: str | None = None,
    notes: str | None = None,
    http_config: HttpConfig | None = None,
) -> list[ProbeResult]:
    """Try every ATS platform with candidate tokens. Returns all probe results."""
    tokens = candidate_tokens(name)
    results: list[ProbeResult] = []

    async with HttpClient(http_config) as client:
        for ats, url_template, key in _PROBE_TARGETS:
            found = False
            for token in tokens[:6]:  # try first 6 candidates per platform
                result = await probe_endpoint(client, ats, token, url_template, key)
                results.append(result)
                if result.hit:
                    found = True
                    break  # first hit wins for this platform
            if not found and ats not in UNDISCOVERABLE_ATS:
                # Record the first attempt as the representative failure.
                pass

    return results


async def verify_entries(
    registry: Registry,
    *,
    all_entries: bool = False,
    http_config: HttpConfig | None = None,
) -> list[ProbeResult]:
    """Re-ping registry entries to confirm they are still live."""
    targets = registry.sorted() if all_entries else registry.unverified()
    if not targets:
        return []

    results: list[ProbeResult] = []

    async with HttpClient(http_config) as client:
        for company in targets:
            if company.ats == "workday":
                # Workday probe needs a POST; skip for now, always mark unverified.
                results.append(
                    ProbeResult(ats="workday", token=company.token or company.extra.get("tenant", ""),
                                url="", hit=False, error="workday probe not implemented")
                )
                continue

            url_template = _url_for_ats(company.ats)
            key = _key_for_ats(company.ats)
            if url_template is None:
                results.append(
                    ProbeResult(ats=company.ats, token=company.token, url="",
                                hit=False, error=f"no probe URL for {company.ats}")
                )
                continue

            result = await probe_endpoint(client, company.ats, company.token, url_template, key)
            results.append(result)

            registry.mark_verified(
                company.key,
                verified=result.hit,
                when=utcnow() if result.hit else None,
            )

    registry.save()
    return results


def _url_for_ats(ats: str) -> str | None:
    for a, url, _ in _PROBE_TARGETS:
        if a == ats:
            return url
    return None


def _key_for_ats(ats: str) -> str | None:
    for a, _, key in _PROBE_TARGETS:
        if a == ats:
            return key
    return None
