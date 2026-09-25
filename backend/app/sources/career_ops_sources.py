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
        CareerOpsReverseSource(provider=provider, adapter=adapter)
        for provider in sorted(REVERSE_ATS_PROVIDERS)
    ]
