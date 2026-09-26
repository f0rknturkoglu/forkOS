"""Opportunity Listing Service: headless JD extraction, liveness verification, and listing intelligence."""

from __future__ import annotations

import hashlib
import unicodedata
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import touch_entity
from app.core.events import log_event
from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.modules.opportunity.models import Opportunity, OpportunitySourceObservation

LIVENESS_CACHE_TTL = timedelta(hours=24)
LIVENESS_CLOSE_CONFIRMATION_INTERVAL = timedelta(hours=12)


def normalize_jd_text(text: str | None) -> str:
    """Normalize whitespace and newlines for stable content comparison and hashing."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", text)
    lines = [line.strip() for line in norm.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    collapsed: list[str] = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                collapsed.append("")
                prev_blank = True
        else:
            collapsed.append(" ".join(line.split()))
            prev_blank = False
    return "\n".join(collapsed).strip()


def compute_jd_hash(text: str | None) -> str:
    """Deterministic hash of normalized JD text."""
    norm = normalize_jd_text(text)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def should_promote_jd(existing: str | None, candidate: str | None) -> tuple[bool, str]:
    """Deterministic promotion policy: decide if candidate JD should overwrite canonical description."""
    existing_clean = (existing or "").strip()
    candidate_clean = (candidate or "").strip()

    if len(candidate_clean) < 200:
        return False, "candidate_too_short"

    if len(existing_clean) < 200:
        return True, "existing_is_stub_or_empty"

    existing_hash = compute_jd_hash(existing_clean)
    candidate_hash = compute_jd_hash(candidate_clean)
    if existing_hash == candidate_hash:
        return False, "identical_content"

    # Existing is substantive (>= 200 chars). Protect richer canonical content.
    if len(candidate_clean) < len(existing_clean) * 0.7:
        return False, "canonical_description_richer"

    # Candidate is substantially richer (e.g. existing was 400 chars, candidate is 7000 chars)
    if len(candidate_clean) >= len(existing_clean) * 1.5 and (len(candidate_clean) - len(existing_clean)) >= 300:
        return True, "candidate_substantially_richer"

    if len(candidate_clean) > len(existing_clean):
        return True, "candidate_richer"

    return False, "canonical_description_preferred"


def get_extraction_candidates(
    opportunity: Opportunity,
    observations: list[OpportunitySourceObservation],
    max_candidates: int = 3,
) -> list[tuple[str, OpportunitySourceObservation | None, str]]:
    """Deterministically order candidate source observations for JD extraction (up to max_candidates).

    Priority:
    1. Observation matching canonical Opportunity.url
    2. Preferred authoritative ATS observation (greenhouse, lever, ashby, workday, etc.)
    3. Company careers observation
    4. Safe fallback observations
    5. Canonical Opportunity.url without matching observation
    """
    candidates: list[tuple[str, OpportunitySourceObservation | None, str]] = []
    seen_urls: set[str] = set()

    def add_candidate(url: str | None, obs: OpportunitySourceObservation | None, reason: str) -> None:
        if not url:
            return
        cleaned = url.strip()
        if cleaned and cleaned not in seen_urls:
            seen_urls.add(cleaned)
            candidates.append((cleaned, obs, reason))

    opp_url = (opportunity.url or "").strip()

    # 1. Observation matching canonical Opportunity.url
    if opp_url:
        for obs in observations:
            if obs.canonical_url and obs.canonical_url.strip() == opp_url:
                add_candidate(obs.canonical_url, obs, "canonical_opportunity_url")

    # 2. Preferred authoritative ATS observation
    ats_domains = (
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "jobs.lever.co",
        "jobs.ashbyhq.com",
        "myworkdayjobs.com",
        "icims.com",
        "bamboohr.com",
        "smartrecruiters.com",
    )
    for obs in observations:
        url = (obs.canonical_url or "").strip()
        if url and any(domain in url for domain in ats_domains):
            add_candidate(url, obs, "preferred_authoritative_ats")

    # 3. Company careers observation
    for obs in observations:
        url = (obs.canonical_url or "").strip()
        if url and ("/careers" in url or "/jobs" in url or "career" in (obs.source or "")):
            add_candidate(url, obs, "company_careers")

    # 4. Safe fallback observation
    for obs in observations:
        url = (obs.canonical_url or "").strip()
        if url:
            add_candidate(url, obs, "fallback_observation")

    # 5. Canonical Opportunity url without matching observation
    if opp_url:
        add_candidate(opp_url, None, "canonical_opportunity_url_no_matching_observation")

    return candidates[:max_candidates]


def select_extraction_source(
    opportunity: Opportunity,
    observations: list[OpportunitySourceObservation],
) -> tuple[str | None, OpportunitySourceObservation | None, str]:
    """Deterministically select primary source observation to extract JD from."""
    candidates = get_extraction_candidates(opportunity, observations, max_candidates=1)
    if candidates:
        return candidates[0]
    return None, None, "no_url"


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
        """Verify multi-source liveness with 24h cache, safe 2-step closure confirmation, and reopen semantics."""
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
            is_cache_replay = False

            if not force and isinstance(cached_liveness, dict):
                checked_at_str = cached_liveness.get("checked_at")
                status_in_cache = cached_liveness.get("status")
                if checked_at_str:
                    try:
                        checked_at = datetime.fromisoformat(checked_at_str)
                        if checked_at.tzinfo is None:
                            checked_at = checked_at.replace(tzinfo=UTC)
                        else:
                            checked_at = checked_at.astimezone(UTC)
                        cache_age = now - checked_at
                        if status_in_cache == "expired" and obs.source_status == "likely_closed":
                            # Closure confirmation requires fresh evidence >= 12h later!
                            closure_conf = enrichment.get("closure_confirmation") or {}
                            first_exp_str = closure_conf.get("first_expired_checked_at") or enrichment.get("likely_closed_at")
                            if first_exp_str:
                                first_exp_at = datetime.fromisoformat(first_exp_str)
                                if first_exp_at.tzinfo is None:
                                    first_exp_at = first_exp_at.replace(tzinfo=UTC)
                                else:
                                    first_exp_at = first_exp_at.astimezone(UTC)
                                if (now - first_exp_at) >= LIVENESS_CLOSE_CONFIRMATION_INTERVAL:
                                    # Elapsed interval satisfied; must force fresh adapter call to confirm closure!
                                    receipt_data = None
                                elif cache_age < LIVENESS_CACHE_TTL:
                                    receipt_data = cached_liveness
                                    is_cache_replay = True
                            elif cache_age < LIVENESS_CACHE_TTL:
                                receipt_data = cached_liveness
                                is_cache_replay = True
                        elif cache_age < LIVENESS_CACHE_TTL:
                            receipt_data = cached_liveness
                            is_cache_replay = True
                    except Exception:
                        receipt_data = None

            if receipt_data is None:
                receipt = await self.adapter.check_liveness(url)
                receipt_data = receipt.model_dump()
                receipt_data["checked_at"] = receipt.checked_at.isoformat()
                enrichment["liveness"] = receipt_data
                obs.enrichment = enrichment
                is_cache_replay = False

            status = receipt_data.get("status")
            receipt_checked_at_str = receipt_data.get("checked_at")
            if receipt_checked_at_str:
                receipt_dt = datetime.fromisoformat(receipt_checked_at_str)
                if receipt_dt.tzinfo is None:
                    receipt_dt = receipt_dt.replace(tzinfo=UTC)
                else:
                    receipt_dt = receipt_dt.astimezone(UTC)
            else:
                receipt_dt = now

            # Clock skew protection (Section 26)
            MAX_CLOCK_SKEW = timedelta(minutes=5)
            is_future_skew = receipt_dt > (now + MAX_CLOCK_SKEW)
            if is_future_skew:
                enrichment.setdefault("warnings", []).append("clock_skew_future_timestamp")
                obs.enrichment = enrichment

            # Note: Do NOT mutate obs.last_seen_at or opportunity.last_seen_at on liveness checks.
            # Liveness checks are URL health probes, not discovery sightings.

            if status == "active" and not is_future_skew:
                obs.source_status = "active"
                obs.source_removed_at = None
                if "closure_confirmation" in enrichment:
                    enrichment.pop("closure_confirmation", None)
                if "likely_closed_at" in enrichment:
                    enrichment.pop("likely_closed_at", None)
                obs.enrichment = enrichment
            elif status == "expired" and not is_future_skew:
                if is_cache_replay:
                    # Cache replay cannot advance confirmation count or close
                    pass
                else:
                    # Fresh adapter result
                    closure_conf = dict(enrichment.get("closure_confirmation") or {})
                    first_exp_str = closure_conf.get("first_expired_checked_at") or enrichment.get("likely_closed_at")

                    if obs.source_status == "likely_closed" and first_exp_str:
                        first_exp_at = datetime.fromisoformat(first_exp_str)
                        if first_exp_at.tzinfo is None:
                            first_exp_at = first_exp_at.replace(tzinfo=UTC)
                        else:
                            first_exp_at = first_exp_at.astimezone(UTC)

                        prev_exp_str = closure_conf.get("last_expired_checked_at")
                        prev_exp_at = None
                        if prev_exp_str:
                            prev_exp_at = datetime.fromisoformat(prev_exp_str)
                            if prev_exp_at.tzinfo is None:
                                prev_exp_at = prev_exp_at.replace(tzinfo=UTC)
                            else:
                                prev_exp_at = prev_exp_at.astimezone(UTC)

                        # Monotonic confirmation rule (Section 24 & 25)
                        is_strictly_newer = prev_exp_at is None or receipt_dt > prev_exp_at
                        interval_elapsed = (receipt_dt - first_exp_at) >= LIVENESS_CLOSE_CONFIRMATION_INTERVAL

                        if is_strictly_newer and interval_elapsed:
                            # 2nd independent confirmation >= 12h apart and strictly newer
                            obs.source_status = "closed"
                            obs.source_removed_at = receipt_dt
                            closure_conf["confirmation_count"] = int(closure_conf.get("confirmation_count", 1)) + 1
                            closure_conf["last_expired_checked_at"] = receipt_dt.isoformat()
                            enrichment["closure_confirmation"] = closure_conf
                            obs.enrichment = enrichment
                        elif not is_strictly_newer:
                            # Reject time-travel / non-monotonic evidence! Keep likely_closed without advancing confirmation count
                            closure_conf.setdefault("warnings", []).append("stale_non_monotonic_evidence")
                            enrichment["closure_confirmation"] = closure_conf
                            obs.enrichment = enrichment
                        else:
                            # Newer, but interval not yet elapsed
                            obs.source_status = "likely_closed"
                            closure_conf["last_expired_checked_at"] = receipt_dt.isoformat()
                            enrichment["closure_confirmation"] = closure_conf
                            obs.enrichment = enrichment
                    else:
                        # 1st expired observation
                        obs.source_status = "likely_closed"
                        closure_conf = {
                            "first_expired_checked_at": receipt_dt.isoformat(),
                            "last_expired_checked_at": receipt_dt.isoformat(),
                            "confirmation_count": 1,
                        }
                        enrichment["closure_confirmation"] = closure_conf
                        enrichment["likely_closed_at"] = receipt_dt.isoformat()
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
        prev_opp_status = opportunity.source_status
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

        if overall_status == "closed":
            if opportunity.closed_at is None:
                opportunity.closed_at = now
            if prev_opp_status != "closed":
                await log_event(
                    session,
                    verb="opportunity.source_status_changed",
                    entity_id=opportunity.id,
                    entity_type="opportunity",
                    payload={"previous_status": prev_opp_status, "new_status": "closed", "reason": "all_sources_confirmed_closed"},
                )
        elif overall_status == "active":
            opportunity.closed_at = None
            if prev_opp_status in ("closed", "likely_closed"):
                await log_event(
                    session,
                    verb="opportunity.source_reopened",
                    entity_id=opportunity.id,
                    entity_type="opportunity",
                    payload={"previous_status": prev_opp_status, "new_status": "active", "reason": "source_verified_active"},
                )

        await session.flush()
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
        """Extract substantive JD text and promote to canonical Opportunity description non-destructively."""
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

        raw = dict(opportunity.raw or {})
        existing_desc = str(raw.get("description") or opportunity.notes or "").strip()

        # Fetch policy: skip network fetch if already substantive and not force
        if len(existing_desc) >= 200 and not force:
            return {
                "promoted": False,
                "reason": "already_has_substantive_description",
                "length": len(existing_desc),
            }

        candidates = get_extraction_candidates(opportunity, observations, max_candidates=3)
        if not candidates:
            return {"promoted": False, "reason": "no_url"}

        last_attempt = None
        for selected_url, selected_obs, source_reason in candidates:
            extract_res = await self.adapter.extract_job(selected_url)
            cleaned_text = (extract_res.text or "").strip()

            if extract_res.error or not cleaned_text:
                failed_meta = {
                    "source_url": selected_url,
                    "requested_url": getattr(extract_res, "requested_url", selected_url),
                    "returned_url": getattr(extract_res, "final_url", getattr(extract_res, "url", selected_url)),
                    "method": "browser_extract",
                    "jd_extracted_at": now.isoformat(),
                    "jd_text_length": len(cleaned_text),
                    "jd_hash": "",
                    "jd_title": extract_res.title or "",
                    "identity_status": getattr(extract_res, "job_identity_status", "invalid_non_job"),
                    "promoted": False,
                    "promotion_reason": extract_res.error or "empty_text",
                    "source_selection_reason": source_reason,
                }
                if selected_obs is not None:
                    obs_enrichment = dict(selected_obs.enrichment or {})
                    obs_enrichment["jd_extraction"] = failed_meta
                    selected_obs.enrichment = obs_enrichment
                else:
                    raw["jd_extraction"] = failed_meta
                    opportunity.raw = raw

                last_attempt = {
                    "promoted": False,
                    "error": extract_res.error or "empty_text",
                    "code": extract_res.code,
                    "identity_status": getattr(extract_res, "job_identity_status", "invalid_non_job"),
                    "reason": extract_res.error or "empty_text",
                    "promotion_reason": extract_res.error or "empty_text",
                    "requested_url": failed_meta["requested_url"],
                    "final_url": failed_meta["returned_url"],
                    "selected_url": selected_url,
                    "metadata": failed_meta,
                }
                continue

            # Identity verification: check if extracted text represents the requested posting
            identity_status = getattr(extract_res, "job_identity_status", "valid_job")
            identity_reason = getattr(extract_res, "identity_reason", "valid_specific_posting")

            if identity_status != "valid_job":
                # Rejected non-job or uncertain identity: store rejected evidence, do NOT promote!
                jd_hash = compute_jd_hash(cleaned_text)
                jd_meta = {
                    "source_url": selected_url,
                    "requested_url": getattr(extract_res, "requested_url", selected_url),
                    "returned_url": getattr(extract_res, "final_url", getattr(extract_res, "url", selected_url)),
                    "method": "browser_extract",
                    "jd_extracted_at": now.isoformat(),
                    "jd_text_length": len(cleaned_text),
                    "jd_hash": jd_hash,
                    "jd_title": extract_res.title,
                    "identity_status": identity_status,
                    "promoted": False,
                    "promotion_reason": identity_reason,
                    "source_selection_reason": source_reason,
                }
                if selected_obs is not None:
                    obs_enrichment = dict(selected_obs.enrichment or {})
                    obs_enrichment["jd_extraction"] = jd_meta
                    selected_obs.enrichment = obs_enrichment
                else:
                    raw["jd_extraction"] = jd_meta
                    opportunity.raw = raw

                last_attempt = {
                    "promoted": False,
                    "promotion_reason": identity_reason,
                    "reason": identity_reason,
                    "identity_status": identity_status,
                    "requested_url": jd_meta["requested_url"],
                    "final_url": jd_meta["returned_url"],
                    "title": extract_res.title,
                    "text_length": len(cleaned_text),
                    "selected_url": selected_url,
                    "metadata": jd_meta,
                }
                # Try next candidate!
                continue

            # Valid job posting -> Check substantive quality promotion policy
            promoted, promo_reason = should_promote_jd(existing_desc, cleaned_text)
            jd_hash = compute_jd_hash(cleaned_text)
            jd_meta = {
                "source_url": selected_url,
                "requested_url": getattr(extract_res, "requested_url", selected_url),
                "returned_url": getattr(extract_res, "final_url", getattr(extract_res, "url", selected_url)),
                "method": "browser_extract",
                "jd_extracted_at": now.isoformat(),
                "jd_text_length": len(cleaned_text),
                "jd_hash": jd_hash,
                "jd_title": extract_res.title,
                "identity_status": "valid_job",
                "promoted": promoted,
                "promotion_reason": promo_reason,
                "source_selection_reason": source_reason,
            }
            if selected_obs is not None:
                obs_enrichment = dict(selected_obs.enrichment or {})
                obs_enrichment["jd_extraction"] = jd_meta
                selected_obs.enrichment = obs_enrichment
            else:
                raw["jd_extraction"] = jd_meta
                opportunity.raw = raw

            if promoted:
                raw["description"] = cleaned_text
                opportunity.raw = raw

                search_parts = filter(
                    None,
                    [opportunity.organization, opportunity.location, cleaned_text, opportunity.url],
                )
                await touch_entity(session, opportunity.id, search_text=" ".join(search_parts))

                await log_event(
                    session,
                    verb="opportunity.updated",
                    entity_id=opportunity.id,
                    entity_type="opportunity",
                    payload={"action": "jd_enriched", **jd_meta},
                )

            await session.flush()
            return {
                "promoted": promoted,
                "promotion_reason": promo_reason,
                "reason": promo_reason,
                "identity_status": "valid_job",
                "requested_url": jd_meta["requested_url"],
                "final_url": jd_meta["returned_url"],
                "title": extract_res.title,
                "text_length": len(cleaned_text),
                "selected_url": selected_url,
                "metadata": jd_meta,
            }

        await session.flush()
        return last_attempt or {"promoted": False, "reason": "no_valid_candidate_found"}
