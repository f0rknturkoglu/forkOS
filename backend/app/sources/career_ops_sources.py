from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.config import settings
from app.integrations.career_ops.adapter import REVERSE_ATS_PROVIDERS, CareerOpsAdapter
from app.integrations.career_ops.config import (
    CAREER_OPS_PINNED_COMMIT,
    CAREER_OPS_PINNED_VERSION,
)
from app.integrations.career_ops.provider_targets import build_provider_targets
from app.sources.base import FetchOutcome, RawItem, SourceClass
from app.sources.forkjob_core.models import cluster_key as compute_cluster_key


@dataclass
class CareerOpsReverseSource:
    provider: str
    adapter: Any | None = None
    interval_minutes: int = 1440
    source_class: str = SourceClass.SLOW_OPTIN.value
    timeout_seconds: float = 300.0
    skip_closure_sweep: bool = True

    @property
    def id(self) -> str:
        return f"careerops:{self.provider}"

    @property
    def label(self) -> str:
        return f"career-ops Reverse ATS ({self.provider.capitalize()})"

    @property
    def category(self) -> str:
        return "reverse_ats"

    async def fetch(self) -> FetchOutcome:
        adapter = self.adapter or CareerOpsAdapter()
        since_days = settings.career_ops_discovery_since_days
        limit = settings.career_ops_discovery_limit
        if self.provider == "workday":
            # The 200-board sweep repeatedly exceeds even the extended budget.
            # A bounded partial result is preferable to losing every Workday offer.
            limit = min(limit, 50)

        res = await adapter.reverse_scan(
            provider=self.provider,
            since_days=since_days,
            limit=limit,
        )

        items: list[RawItem] = []
        for offer in res.offers:
            pub_date = None
            if offer.posted_at:
                try:
                    pub_date = datetime.fromisoformat(offer.posted_at)
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=UTC)
                except ValueError:
                    pub_date = None

            ckey = compute_cluster_key(offer.company, offer.title, offer.location)

            items.append(
                RawItem(
                    external_id=offer.url,
                    title=offer.title,
                    url=offer.url,
                    summary=None,
                    published_at=pub_date,
                    extra={
                        "organization": offer.company,
                        "location": offer.location,
                        "kind": "job",
                        "cluster_key": ckey,
                        "forkjob": {
                            "cluster_key": ckey,
                            "company": offer.company,
                            "title": offer.title,
                            "location": offer.location,
                        },
                        "career_ops": {
                            "engine_version": CAREER_OPS_PINNED_VERSION,
                            "engine_commit": CAREER_OPS_PINNED_COMMIT,
                            "provider": self.provider,
                            "upstream_source": offer.source,
                            "date_status": offer.date_status,
                        },
                    },
                )
            )


        return FetchOutcome(
            items=items,
            partial=res.is_partial,
            detail=res.partial_detail,
        )


def get_career_ops_sources(adapter: Any | None = None) -> list[CareerOpsReverseSource]:
    return [
        CareerOpsReverseSource(
            provider=provider,
            adapter=adapter,
            timeout_seconds=630.0 if provider == "workday" else 300.0,
        )
        for provider in sorted(REVERSE_ATS_PROVIDERS)
    ]


@dataclass
class CareerOpsProviderSource:
    """One bounded scan for a category of configured upstream provider targets."""

    mode: str
    adapter: Any | None = None
    interval_minutes: int = 1440
    source_class: str = SourceClass.SLOW_OPTIN.value
    timeout_seconds: float = 300.0
    skip_closure_sweep: bool = True

    @property
    def id(self) -> str:
        return f"careerops:{self.mode}"

    @property
    def label(self) -> str:
        return "career-ops açık panolar" if self.mode == "boards" else "career-ops takip edilen şirketler"

    @property
    def category(self) -> str:
        return "provider_board" if self.mode == "boards" else "provider_company"

    async def fetch(self) -> FetchOutcome:
        targets = build_provider_targets()
        if self.mode == "boards":
            targets["tracked_companies"] = []
        else:
            targets["job_boards"] = []
        receipt = await (self.adapter or CareerOpsAdapter()).provider_scan(targets=targets)
        items: list[RawItem] = []
        for offer in receipt.offers:
            company = offer.company or offer.target
            ckey = compute_cluster_key(company, offer.title, offer.location)
            items.append(RawItem(
                external_id=offer.url,
                title=offer.title,
                url=offer.url,
                summary=offer.description,
                published_at=offer.posted_at,
                extra={
                    "organization": company,
                    "location": offer.location,
                    "compensation": offer.salary,
                    "description": offer.description,
                    "kind": "job",
                    "cluster_key": ckey,
                    "forkjob": {
                        "cluster_key": ckey,
                        "company": company,
                        "title": offer.title,
                        "location": offer.location,
                    },
                    "career_ops": {
                        "engine_version": CAREER_OPS_PINNED_VERSION,
                        "engine_commit": CAREER_OPS_PINNED_COMMIT,
                        "provider": offer.provider,
                        "target": offer.target,
                        "target_kind": offer.kind,
                    },
                },
            ))
        details = [f"{error.get('target')}: {error.get('error')}" for error in receipt.errors]
        bounded = [result for result in receipt.target_results if result.cap_hit or result.status == "partial"]
        if bounded:
            details.append(
                "Sonuç sınırı: "
                + ", ".join(
                    f"{result.target} ({result.found} görüldü, sınır {result.result_limit or '?'})"
                    for result in bounded[:4]
                )
            )
        return FetchOutcome(items=items, partial=receipt.partial, detail="; ".join(details[:5]))


def get_career_ops_provider_sources(adapter: Any | None = None) -> list[CareerOpsProviderSource]:
    return [CareerOpsProviderSource(mode=mode, adapter=adapter) for mode in ("boards", "companies")]
