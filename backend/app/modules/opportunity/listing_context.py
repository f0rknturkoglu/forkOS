"""CareerListingContext: Canonical, C3/C3.2 evidence-only listing context for C4/C5.

Consume C3/C3.2 canonical evidence only:
- opportunity_id, title, company, location, remote, salary
- VALID canonical JD and JD hash
- Source provenance, liveness receipts, listing health, repost signals
- Enforces: Rejected/generic/error-page extractions must NEVER enter Specialist JD context.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.modules.opportunity.intelligence import listing_fingerprint
from app.modules.opportunity.listing_service import OpportunityListingService, compute_jd_hash
from app.modules.opportunity.models import Opportunity, OpportunitySourceObservation


class CareerListingContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    opportunity_id: str
    title: str
    company: str
    location: str
    remote: str
    salary: str | None = None
    canonical_jd: str = ""
    jd_hash: str = ""
    listing_fingerprint: str = ""
    is_jd_valid: bool = True
    jd_rejection_reason: str | None = None
    source_provenance: list[dict[str, Any]] = Field(default_factory=list)
    liveness: dict[str, Any] = Field(default_factory=dict)
    listing_health: dict[str, Any] = Field(default_factory=dict)
    repost_signals: dict[str, Any] = Field(default_factory=dict)
    published_at: str | None = None
    source_urls: list[str] = Field(default_factory=list)


async def build_career_listing_context(
    session: AsyncSession,
    opportunity: Opportunity,
    *,
    title: str | None = None,
) -> CareerListingContext:
    """Build CareerListingContext strictly from canonical C3/C3.2 verified evidence."""
    if title is None:
        entity = await session.get(Entity, opportunity.id)
        title = entity.title if entity else ""

    # Fetch source observations
    res = await session.execute(
        select(OpportunitySourceObservation).where(
            OpportunitySourceObservation.opportunity_id == opportunity.id
        )
    )
    observations = list(res.scalars().all())

    raw = dict(opportunity.raw or {})
    canonical_desc = str(raw.get("description") or opportunity.notes or "").strip()

    # Provenance tracking
    source_provenance: list[dict[str, Any]] = []
    source_urls: list[str] = []
    liveness_aggregate: dict[str, Any] = {
        "source_status": opportunity.source_status,
        "observations": [],
    }

    # Inspect JD extraction status from observations
    is_rejected = False
    rejection_reason = None
    for obs in observations:
        if obs.canonical_url:
            source_urls.append(obs.canonical_url)
        enrichment = dict(obs.enrichment or {})
        jd_ext = enrichment.get("jd_extraction")
        if jd_ext:
            ident_status = jd_ext.get("identity_status")
            if ident_status in ("invalid_non_job", "uncertain_identity"):
                # Non-job error/redirect extraction was recorded
                if not canonical_desc or len(canonical_desc) < 200:
                    is_rejected = True
                    rejection_reason = jd_ext.get("promotion_reason") or ident_status
            source_provenance.append({
                "source": obs.source,
                "url": obs.canonical_url,
                "jd_extraction": jd_ext,
            })
        liv = enrichment.get("liveness")
        if liv:
            liveness_aggregate["observations"].append({
                "source": obs.source,
                "status": liv.get("status"),
                "checked_at": liv.get("checked_at"),
                "method": liv.get("method"),
            })

    # Validate JD substantive content
    if not canonical_desc or len(canonical_desc) < 100:
        is_jd_valid = False
        jd_rejection_reason = rejection_reason or "missing_or_insufficient_jd"
    elif is_rejected and len(canonical_desc) < 200:
        is_jd_valid = False
        jd_rejection_reason = rejection_reason or "rejected_non_job"
    else:
        is_jd_valid = True
        jd_rejection_reason = None

    jd_hash_val = compute_jd_hash(canonical_desc) if is_jd_valid else ""
    lp = listing_fingerprint(opportunity, title=title)

    # Compute deterministic listing health
    health = 100
    if not canonical_desc or len(canonical_desc) < 300:
        health -= 30
    if not opportunity.compensation:
        health -= 15
    if opportunity.source_status == "closed":
        health -= 30
    elif opportunity.source_status in ("likely_closed", "uncertain"):
        health -= 15
    health_score = max(0, min(100, health))
    listing_health = {
        "health_score": health_score,
        "jd_completeness": "complete" if len(canonical_desc) >= 300 else "stub",
        "salary_transparency": "stated" if opportunity.compensation else "missing",
        "liveness_status": "live" if opportunity.source_status == "active" else (opportunity.source_status or "uncertain"),
        "repost_frequency": "single",
    }
    repost_signals = {
        "repost_detected": bool(raw.get("repost_cluster")),
        "repost_cluster": raw.get("repost_cluster"),
    }

    return CareerListingContext(
        opportunity_id=str(opportunity.id),
        title=title,
        company=opportunity.organization or "",
        location=opportunity.location or "",
        remote=opportunity.remote or "",
        salary=opportunity.compensation,
        canonical_jd=canonical_desc if is_jd_valid else "",
        jd_hash=jd_hash_val,
        listing_fingerprint=lp,
        is_jd_valid=is_jd_valid,
        jd_rejection_reason=jd_rejection_reason,
        source_provenance=source_provenance,
        liveness=liveness_aggregate,
        listing_health=listing_health,
        repost_signals=repost_signals,
        published_at=opportunity.published_at.isoformat() if opportunity.published_at else None,
        source_urls=source_urls,
    )
