"""Single canonical LinkedIn source: shared policy, native primary, JobSpy recovery."""

import asyncio as asyncio
import os
from dataclasses import asdict, replace

import httpx

from ..rich_text import merge_descriptions
from .base import USER_AGENT, ScrapeBatch, ScraperBase, ScraperPermanentError
from .linkedin_jobspy import (  # compatibility exports for existing callers/tests
    LinkedInConfig as LinkedInConfig,
)
from .linkedin_jobspy import (
    LinkedInJobSpyTransport,
    _merge_user_profiles,
    jobspy_version,
    load_proxies,
    resolve_linkedin_config,
)
from .linkedin_jobspy import (
    _deduplicate as _deduplicate,
)
from .linkedin_jobspy import (
    _import_jobspy_runner as _import_jobspy_runner,
)
from .linkedin_jobspy import (
    _run_jobspy_isolated as _run_jobspy_isolated,
)
from .linkedin_jobspy import (
    _text as _text,
)
from .linkedin_jobspy import (
    job_from_row as job_from_row,
)
from .linkedin_jobspy import (
    redact_proxy_secrets as redact_proxy_secrets,
)
from .linkedin_native import LinkedInNativeTransport
from .linkedin_policy import POLICY, LinkedInPolicyDenied
from .linkedin_types import LinkedInBudget

LAST_DIAGNOSTICS = {}


def linkedin_diagnostics():
    state = POLICY.state
    return {
        "preferred_transport": os.getenv("FORKJOB_LINKEDIN_TRANSPORT", "auto"),
        "policy": asdict(state) if state else None,
        "jobspy_version": jobspy_version(),
        "native_implemented": True,
        "fallback_available": jobspy_version() is not None,
        "last_transport_used": LAST_DIAGNOSTICS.get("transport_used"),
    }


class LinkedInScraper(ScraperBase):
    source_key = "linkedin"
    label = "LinkedIn"
    base_url = "https://www.linkedin.com/jobs"

    def __init__(
        self,
        config=None,
        *,
        searches=None,
        proxy_file_env="FORKJOB_LINKEDIN_PROXIES_FILE",
        allow_direct=None,
        ca_cert_env="FORKJOB_LINKEDIN_CA_CERT",
        user_agent_env="FORKJOB_LINKEDIN_USER_AGENT",
        runner=None,
        transport=None,
        policy_gate=None,
        native_transport=None,
        jobspy_transport=None,
        max_wall_seconds=180,
        max_requests=40,
        max_pages=10,
        detail_enrich_max=10,
    ):
        super().__init__(config)
        # Never allow an operator override to impersonate another crawler.
        self.config = replace(
            self.config,
            user_agent=USER_AGENT,
            allowed_hosts=("www.linkedin.com", "linkedin.com"),
            max_response_bytes=4 * 1024 * 1024,
        )
        self.searches = _merge_user_profiles([dict(p) for p in (searches or [])])
        self.transport = (
            transport if transport is not None else os.getenv("FORKJOB_LINKEDIN_TRANSPORT", "auto")
        )
        self.policy = policy_gate or POLICY
        self.linkedin_config = resolve_linkedin_config(
            proxy_file_env=proxy_file_env, allow_direct=allow_direct
        )
        self.native = native_transport or LinkedInNativeTransport(self.policy)
        self.jobspy = jobspy_transport or LinkedInJobSpyTransport(
            config,
            searches=[],
            proxy_file_env=proxy_file_env,
            allow_direct=allow_direct,
            ca_cert_env=ca_cert_env,
            user_agent_env=user_agent_env,
            runner=runner,
        )
        self.budget_options = dict(
            max_wall_seconds=max(1, min(900, float(max_wall_seconds))),
            max_requests=max(1, min(100, int(max_requests))),
            max_pages=max(1, min(100, int(max_pages))),
            max_details=max(0, min(25, int(detail_enrich_max))),
        )

    async def scrape(self, client):
        if self.transport not in {"auto", "native", "jobspy"}:
            raise ScraperPermanentError("Unknown LinkedIn transport; expected auto/native/jobspy")
        state = await self.policy.check(client)
        metadata = {
            key: 0
            for key in [
                "native_requests",
                "native_pages",
                "native_items",
                "jobspy_profiles",
                "jobspy_items",
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
                "deduped_items",
                "profiles_attempted",
                "profiles_succeeded",
                "profiles_failed",
            ]
        }
        metadata.update(
            {
                "transport_requested": self.transport,
                "transport_used": [],
                "policy_allowed": state.allowed,
                "policy_checked_at": state.checked_at.isoformat(),
                "policy_reason": state.reason,
                "fallback_used": False,
                "jobspy_version": jobspy_version(),
            }
        )
        if not state.allowed:
            self.record_telemetry(
                items_seen=0, items_returned=0, stop_reason="policy_denied", metadata=metadata
            )
            LAST_DIAGNOSTICS.update(metadata)
            raise LinkedInPolicyDenied(state.reason)
        if not self.searches:
            telemetry = self.record_telemetry(
                items_seen=0,
                items_returned=0,
                result_limit=0,
                cap_hit=False,
                stop_reason="no_profiles",
                metadata={
                    **metadata,
                    "profiles_attempted": 0,
                    "profiles_succeeded": 0,
                    "profiles_failed": 0,
                },
            )
            return ScrapeBatch([], ["LinkedIn has no configured search profiles"], 0, 0, telemetry)
        budget = LinkedInBudget(**self.budget_options)
        contributions = []
        if self.transport in {"auto", "native"}:
            proxies = load_proxies(self.linkedin_config, os.environ)
            if proxies:
                # One fixed route, never rotation on denial/challenge/429.
                original = client._client
                async with httpx.AsyncClient(
                    proxy=proxies[0], headers={"User-Agent": USER_AGENT}, follow_redirects=False
                ) as routed:
                    client._client = routed
                    try:
                        native = await self.native.search(self.searches, client, budget)
                    finally:
                        client._client = original
            else:
                native = await self.native.search(self.searches, client, budget)
            contributions.append(native)
            metadata.update(native.telemetry.metadata)
            if (
                self.transport == "auto"
                and native.fallback_profiles
                and not native.telemetry.metadata.get("fallback_forbidden")
                and budget.remaining > 0
            ):
                try:
                    await self.policy.require(client)
                    recovery = await self.jobspy.search(
                        [
                            {
                                **self.searches[i],
                                "name": self.searches[i].get("name") or f"profile-{i + 1}",
                            }
                            for i in native.fallback_profiles
                        ],
                        client,
                        budget,
                    )
                    contributions.append(recovery)
                    metadata["fallback_used"] = True
                except LinkedInPolicyDenied:
                    native.errors.append("fallback: policy_changed")
                    metadata.update(
                        policy_allowed=False, policy_reason="Policy changed before recovery"
                    )
                except Exception as exc:
                    # Recovery setup failure must not erase useful native cards.
                    native.errors.append(f"fallback: {type(exc).__name__}")
        else:
            await self.policy.require(client)
            contributions.append(await self.jobspy.search(self.searches, client, budget))
        jobs, errors = {}, []
        for result in contributions:
            metadata["transport_used"].append(result.transport)
            errors.extend(result.errors)
            if result.transport == "jobspy_v1":
                metadata.update(jobspy_profiles=result.attempted, jobspy_items=len(result.jobs))
            for job in result.jobs:
                key = job.external_id or job.url
                if key in jobs:
                    previous = jobs[key]
                    previous.description = merge_descriptions(previous.description, job.description)
                    if not previous.salary:
                        previous.salary = job.salary
                else:
                    jobs[key] = job
        primary = contributions[0]
        # Recovery is additive; it never rewrites an earlier failure as healthy.
        attempted, succeeded = primary.attempted, primary.succeeded
        if len(contributions) > 1:
            succeeded += contributions[1].succeeded
            succeeded = min(attempted, succeeded)
        metadata.update(
            profiles_attempted=attempted,
            profiles_succeeded=succeeded,
            profiles_failed=attempted - succeeded,
            deduped_items=len(jobs),
        )
        telemetry = self.record_telemetry(
            items_seen=sum(r.telemetry.items_seen or 0 for r in contributions),
            items_returned=len(jobs),
            pages_fetched=primary.telemetry.pages_fetched,
            page_limit=primary.telemetry.page_limit,
            result_limit=primary.telemetry.result_limit,
            cap_hit=any(r.telemetry.cap_hit for r in contributions),
            partial_reason="; ".join(
                [
                    *(
                        r.telemetry.partial_reason
                        for r in contributions
                        if r.telemetry.partial_reason
                    ),
                    *errors,
                ]
            )
            or None,
            stop_reason="transport_degraded" if errors else primary.telemetry.stop_reason,
            metadata=metadata,
        )
        LAST_DIAGNOSTICS.update(metadata)
        return ScrapeBatch(list(jobs.values()), errors, attempted, succeeded, telemetry)
