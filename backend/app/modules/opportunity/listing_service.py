"""Opportunity Listing Service: headless JD extraction, liveness verification, and listing intelligence."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import touch_entity
from app.core.events import log_event
from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.modules.opportunity.models import Opportunity, OpportunitySourceObservation


class OpportunityListingService:
    def __init__(self, adapter: CareerOpsAdapter | None = None) -> None:
        self.adapter = adapter or CareerOpsAdapter()

    async def verify_opportunity_liveness(
        self,
        session: AsyncSession,
        opportunity_id: uuid.UUID,
        *,
        force: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Verify multi-source liveness with 24h cache and safe 2-step closure confirmation."""
        now = now or datetime.now(UTC)
        opportunity = await session.get(Opportunity, opportunity_id)
        if opportunity is None:
            raise ValueError(f"Opportunity not found: {opportunity_id}")

        res = await session.execute(
            select(OpportunitySourceObservation).where(
                OpportunitySourceObservation.opportunity_id == opportunity_id
            )
        )
        observations = list(res.scalars().all())

        if not observations:
            return {
                "opportunity_id": str(opportunity_id),
                "source_status": opportunity.source_status,
                "observations": [],
            }

        obs_results = []
        for obs in observations:
            url = obs.canonical_url or opportunity.url
            if not url:
                continue

            enrichment = dict(obs.enrichment or {})
            cached_liveness = enrichment.get("liveness")
            receipt_data = None

            if not force and isinstance(cached_liveness, dict):
                checked_at_str = cached_liveness.get("checked_at")
                if checked_at_str:
                    try:
                        checked_at = datetime.fromisoformat(checked_at_str)
                        if (now - checked_at) < timedelta(hours=24):
                            receipt_data = cached_liveness
                    except Exception:
                        pass

            if receipt_data is None:
                receipt = await self.adapter.check_liveness(url)
                receipt_data = receipt.model_dump()
                enrichment["liveness"] = receipt_data
                obs.enrichment = enrichment

            status = receipt_data.get("status")
            obs.last_seen_at = now

            if status == "active":
                obs.source_status = "active"
                obs.last_successful_seen_at = now
                obs.source_removed_at = None
                if "likely_closed_at" in enrichment:
                    enrichment.pop("likely_closed_at", None)
                    obs.enrichment = enrichment
            elif status == "expired":
                # Safe 2-step confirmation: requires 2 consecutive all-expired checks >= 12h apart
                likely_at_str = enrichment.get("likely_closed_at")
                if obs.source_status == "likely_closed" and likely_at_str:
                    try:
                        likely_at = datetime.fromisoformat(likely_at_str)
                        if (now - likely_at) >= timedelta(hours=12):
                            obs.source_status = "closed"
                            obs.source_removed_at = now
                        else:
                            obs.source_status = "likely_closed"
                    except Exception:
                        obs.source_status = "likely_closed"
                else:
                    obs.source_status = "likely_closed"
                    enrichment["likely_closed_at"] = now.isoformat()
                    obs.enrichment = enrichment
            elif status == "uncertain":
                # uncertain != expired. Never hard-close.
                pass

            obs_results.append({
                "source": obs.source,
                "url": url,
                "source_status": obs.source_status,
                "liveness": receipt_data,
            })

        # Multi-source aggregation policy:
        # 1. Any active source keeps canonical opportunity active
        # 2. All expired/closed -> closed if confirmed, else likely_closed
        # 3. Uncertain never triggers closure
        statuses = [obs.source_status for obs in observations]
        if any(s == "active" for s in statuses):
            overall_status = "active"
        elif all(s == "closed" for s in statuses):
            overall_status = "closed"
        elif any(s == "likely_closed" for s in statuses):
            overall_status = "likely_closed"
        else:
            overall_status = "active"

        opportunity.source_status = overall_status
        opportunity.last_seen_at = now

        if overall_status == "closed":
            if opportunity.closed_at is None:
                opportunity.closed_at = now
                await log_event(
                    session,
                    verb="opportunity.source_status_changed",
                    entity_id=opportunity.id,
                    entity_type="opportunity",
                    payload={"new_status": "closed", "reason": "all_sources_confirmed_closed"},
                )
        elif overall_status == "active":
            opportunity.closed_at = None

        return {
            "opportunity_id": str(opportunity_id),
            "source_status": overall_status,
            "observations": obs_results,
        }

    async def enrich_job_description(
        self,
        session: AsyncSession,
        opportunity_id: uuid.UUID,
        *,
        force: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Extract substantive JD text and promote to canonical Opportunity description if stub/empty."""
        now = now or datetime.now(UTC)
        opportunity = await session.get(Opportunity, opportunity_id)
        if opportunity is None:
            raise ValueError(f"Opportunity not found: {opportunity_id}")

        raw = dict(opportunity.raw or {})
        existing_desc = str(raw.get("description") or opportunity.notes or "").strip()
        if len(existing_desc) >= 200 and not force:
            return {
                "promoted": False,
                "reason": "already_has_substantive_description",
                "length": len(existing_desc),
            }

        url = opportunity.url
        if not url:
            res = await session.execute(
                select(OpportunitySourceObservation).where(
                    OpportunitySourceObservation.opportunity_id == opportunity_id
                )
            )
            obs = res.scalars().first()
            if obs and obs.canonical_url:
                url = obs.canonical_url

        if not url:
            return {"promoted": False, "reason": "no_url"}

        extract_res = await self.adapter.extract_job(url)
        if extract_res.error or not extract_res.text:
            return {
                "promoted": False,
                "error": extract_res.error or "empty_text",
                "code": extract_res.code,
            }

        cleaned_text = extract_res.text.strip()
        if len(cleaned_text) < 200:
            return {
                "promoted": False,
                "reason": "extracted_text_too_short",
                "length": len(cleaned_text),
            }

        raw["description"] = cleaned_text
        opportunity.raw = raw

        search_parts = filter(
            None,
            [opportunity.organization, opportunity.location, cleaned_text, opportunity.url],
        )
        await touch_entity(session, opportunity.id, search_text=" ".join(search_parts))

        jd_meta = {
            "jd_extracted_at": now.isoformat(),
            "jd_text_length": len(cleaned_text),
            "jd_hash": hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest(),
            "jd_title": extract_res.title,
        }

        res = await session.execute(
            select(OpportunitySourceObservation).where(
                OpportunitySourceObservation.opportunity_id == opportunity_id
            )
        )
        primary_obs = res.scalars().first()
        if primary_obs:
            obs_enrichment = dict(primary_obs.enrichment or {})
            obs_enrichment["jd_extraction"] = jd_meta
            primary_obs.enrichment = obs_enrichment

        await log_event(
            session,
            verb="opportunity.updated",
            entity_id=opportunity.id,
            entity_type="opportunity",
            payload={"action": "jd_enriched", **jd_meta},
        )

        return {
            "promoted": True,
            "title": extract_res.title,
            "text_length": len(cleaned_text),
            "metadata": jd_meta,
        }
