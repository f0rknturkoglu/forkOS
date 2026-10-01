"""Bounded native guest transport; endpoints are never accessed without policy."""

import asyncio
import random
from urllib.parse import urlencode

import httpx

from ..rich_text import merge_descriptions
from .base import ScraperPermanentError, ScrapeTelemetry
from .detail_evidence import richness_metadata
from .linkedin_parsing import LinkedInResponseError, detail_job, fingerprint, parse_cards
from .linkedin_policy import DETAIL_PATH, GEO_PATH, ROOT, SEARCH_PATH, LinkedInPolicyDenied
from .linkedin_types import LinkedInBudgetExceeded, LinkedInTransportResult


def search_url(profile, start, geo_id=None):
    params = {"keywords": profile["term"], "start": start}
    if geo_id:
        params["geoId"] = geo_id
    elif profile.get("location"):
        params["location"] = profile["location"]
    if profile.get("is_remote") is True:
        params["f_WT"] = "2"
    if profile.get("hours_old") is not None:
        params["f_TPR"] = "r" + str(int(profile["hours_old"]) * 3600)
    return ROOT + SEARCH_PATH + "?" + urlencode(params)


class LinkedInRateController:
    """One controller for the entire run; no parallel profile request storms."""

    def __init__(self, minimum=4, jitter=0.2):
        self.minimum, self.jitter = max(0, minimum), max(0, jitter)
        self.delay = self.minimum
        self.next_at = 0

    async def wait(self, budget):
        loop = asyncio.get_running_loop()
        delay = max(0, self.next_at - loop.time())
        if delay >= budget.remaining:
            raise LinkedInBudgetExceeded("run_budget_reached")
        if delay:
            await asyncio.sleep(delay)
        self.next_at = loop.time() + self.delay + random.uniform(0, self.jitter)

    def throttle(self, retry_after=None):
        self.delay = min(60, max(self.minimum, self.delay * 2))
        self.next_at = asyncio.get_running_loop().time() + max(self.delay, retry_after or 0)

    def recover(self):
        self.delay = max(self.minimum, self.delay / 2)


class LinkedInNativeTransport:
    def __init__(self, policy, *, minimum=4, jitter=0.2, max_retries=2):
        self.policy = policy
        self.rate = LinkedInRateController(minimum, jitter)
        self.max_retries = min(3, max(0, max_retries))
        self.geo_cache = {}
        self.metadata = {}

    async def request(self, client, url, budget, *, json=False):
        from app.sources.base import retry_after_seconds

        for attempt in range(self.max_retries + 1):
            await self.policy.require(client, url)
            await self.rate.wait(budget)
            budget.reserve()
            self.metadata["native_requests"] += 1
            try:
                response = await asyncio.wait_for(
                    client._bounded_request("GET", url, timeout=min(30, budget.remaining)),
                    timeout=budget.remaining,
                )
            except ScraperPermanentError:
                raise LinkedInResponseError("unsafe_response") from None
            except (httpx.TransportError, TimeoutError):
                if attempt >= self.max_retries:
                    raise LinkedInResponseError("transport", eligible=True) from None
                self.rate.throttle()
                continue
            if response.status_code == 403:
                self.metadata["403_count"] += 1
                raise LinkedInResponseError("403")
            if response.status_code in {429, 503}:
                if response.status_code == 429:
                    self.metadata["429_count"] += 1
                wait = retry_after_seconds(response.headers.get("Retry-After"))
                # Never shorten server enforcement to fit a local retry cap.
                if wait is not None and wait >= budget.remaining:
                    raise LinkedInResponseError(str(response.status_code))
                self.rate.throttle(wait)
                if attempt >= self.max_retries:
                    raise LinkedInResponseError(
                        str(response.status_code), eligible=response.status_code == 503
                    )
                continue
            if response.status_code >= 500:
                if attempt >= self.max_retries:
                    raise LinkedInResponseError("transport", eligible=True)
                self.rate.throttle()
                continue
            if response.status_code != 200:
                raise LinkedInResponseError("http_" + str(response.status_code))
            mime = response.headers.get("content-type", "").lower()
            if json and "text/html" in mime:
                fingerprint(response.text)  # login/challenge is not a geo miss
            if ("application/json" if json else "text/html") not in mime:
                raise LinkedInResponseError("content_type", eligible=True)
            self.rate.recover()
            return response
        raise LinkedInResponseError("transport", eligible=True)

    async def geo(self, profile, client, budget):
        location = profile.get("location")
        if not location:
            return None
        if location in self.geo_cache:
            return self.geo_cache[location]
        self.metadata["geo_requested"] += 1
        identifier = None
        try:
            response = await self.request(
                client,
                ROOT + GEO_PATH + "?" + urlencode({"query": location, "typeaheadType": "GEO"}),
                budget,
                json=True,
            )
            rows = response.json()
            if isinstance(rows, list):
                # Exact human-readable match only; never silently choose another city.
                matches = [
                    r
                    for r in rows
                    if isinstance(r, dict)
                    and str(r.get("displayName", "")).casefold() == location.casefold()
                    and str(r.get("id", "")).isdigit()
                ]
                if len(matches) == 1:
                    identifier = str(matches[0]["id"])
        except LinkedInResponseError as exc:
            if exc.kind in {"403", "429", "login", "challenge"}:
                raise
        except (ValueError, TypeError):
            pass
        if identifier:
            self.metadata["geo_resolved"] += 1
        else:
            self.metadata["geo_failed"] += 1
            self.metadata["geo_fallback"] += 1
        if len(self.geo_cache) >= 128:
            self.geo_cache.pop(next(iter(self.geo_cache)))
        self.geo_cache[location] = identifier
        return identifier

    async def search(self, profiles, client, budget):
        self.metadata = {
            key: 0
            for key in [
                "native_requests",
                "native_pages",
                "native_items",
                "geo_requested",
                "geo_resolved",
                "geo_failed",
                "geo_fallback",
                "detail_candidates",
                "detail_attempted",
                "detail_succeeded",
                "detail_failed",
                "429_count",
                "403_count",
                "soft_block_count",
                "schema_error_count",
            ]
        }
        jobs, cards_by_id, errors, failed, eligible, caps = {}, {}, [], [], [], []
        succeeded = 0
        result_limit = 0
        halted = False
        seen_count = 0
        for index, profile in enumerate(profiles):
            start, profile_ids, last_ids = 0, set(), None
            name = profile.get("name") or f"profile-{index + 1}"
            try:
                if not isinstance(profile.get("term"), str) or not profile["term"].strip():
                    raise LinkedInResponseError("invalid_profile")
                try:
                    wanted = max(1, int(profile.get("results_wanted") or 50))
                    if profile.get("hours_old") is not None:
                        int(profile["hours_old"])
                except (ValueError, TypeError):
                    raise LinkedInResponseError("invalid_profile") from None
                result_limit += wanted
                geo_id = await self.geo(profile, client, budget)
                for page in range(budget.max_pages):
                    response = await self.request(
                        client, search_url(profile, start, geo_id), budget
                    )
                    cards, count = parse_cards(response.text)
                    self.metadata["native_pages"] += 1
                    seen_count += count
                    if not count:
                        break
                    ids = {c.job_id or c.url for c in cards}
                    if ids == last_ids or ids <= profile_ids:
                        raise LinkedInResponseError("repeated_page")
                    last_ids = ids
                    for card in cards:
                        identity = card.job_id or card.url
                        if identity not in profile_ids and len(profile_ids) < wanted:
                            profile_ids.add(identity)
                            jobs.setdefault(identity, card.to_job())
                            if profile.get("fetch_description"):
                                cards_by_id.setdefault(identity, card)
                    if len(profile_ids) >= wanted:
                        caps.append("profile_limit_reached")
                        break
                    if page + 1 == budget.max_pages:
                        caps.append("page_budget_reached")
                    start += count  # measured raw response cardinality, not a fixed page size
                succeeded += 1
            except (LinkedInResponseError, LinkedInBudgetExceeded, LinkedInPolicyDenied) as exc:
                kind = (
                    exc.kind
                    if isinstance(exc, LinkedInResponseError)
                    else "policy_changed"
                    if isinstance(exc, LinkedInPolicyDenied)
                    else "run_budget_reached"
                )
                errors.append(f"{name}: {kind}")
                failed.append(index)
                if isinstance(exc, LinkedInResponseError) and exc.eligible:
                    eligible.append(index)
                if kind in {"login", "challenge", "shell"}:
                    self.metadata["soft_block_count"] += 1
                if kind in {"schema", "content_type", "malformed_cards"}:
                    self.metadata["schema_error_count"] += 1
                if kind in {
                    "403",
                    "429",
                    "policy_changed",
                    "run_budget_reached",
                    "login",
                    "challenge",
                }:
                    halted = True
                    self.metadata["fallback_forbidden"] = True
                    # No alternate-IP/transport retry for access or enforcement failures.
                    failed.extend(range(index + 1, len(profiles)))
                    break
        self.metadata["detail_candidates"] = len(cards_by_id)
        listing_errors = list(errors)
        for card in [] if halted else list(cards_by_id.values())[: budget.max_details]:
            try:
                self.metadata["detail_attempted"] += 1
                response = await self.request(
                    client, ROOT + DETAIL_PATH + card.job_id if card.job_id else card.url, budget
                )
                richer = detail_job(response.text, card)
                richer.description = merge_descriptions(
                    jobs[card.job_id or card.url].description, richer.description
                )
                jobs[card.job_id or card.url] = richer
                self.metadata["detail_succeeded"] += 1
            except (LinkedInResponseError, LinkedInBudgetExceeded, LinkedInPolicyDenied) as exc:
                kind = (
                    exc.kind if isinstance(exc, LinkedInResponseError) else "run_budget_or_policy"
                )
                errors.append(f"detail: {kind}")
                self.metadata["detail_failed"] += 1
                if kind in {"challenge", "login", "shell"}:
                    self.metadata["soft_block_count"] += 1
                if kind in {"403", "429", "challenge", "login", "run_budget_or_policy"}:
                    self.metadata["fallback_forbidden"] = True
                    break
        self.metadata.update(richness_metadata(
            len(cards_by_id), self.metadata["detail_succeeded"], budget.max_details,
            errors[len(listing_errors):],
        ))
        self.metadata["listing_complete"] = not caps and not listing_errors
        self.metadata["native_items"] = len(jobs)
        partial = bool(caps or listing_errors)
        telemetry = ScrapeTelemetry(
            items_seen=seen_count,
            items_returned=len(jobs),
            pages_fetched=self.metadata["native_pages"],
            page_limit=budget.max_pages * len(profiles),
            result_limit=result_limit,
            cap_hit=bool(caps),
            partial_reason="; ".join([*dict.fromkeys(caps), *listing_errors]) or None,
            stop_reason=caps[0] if caps else "native_degraded" if listing_errors else "exhausted",
            metadata={**self.metadata, "transport": "native_v2", "partial": partial},
        )
        return LinkedInTransportResult(
            list(jobs.values()),
            errors,
            telemetry,
            "native_v2",
            len(profiles),
            succeeded,
            list(dict.fromkeys(failed)),
            eligible,
        )
