"""Deterministic job description identity validation for career-ops extractions.

Ensures extracted text represents the requested job posting rather than a generic
careers index, company board, error landing, or redirect trap.
"""

from __future__ import annotations

import re
from typing import Literal
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, Field

GENERIC_TITLE_PHRASES = (
    "current openings",
    "careers at",
    "open positions",
    "jobs at",
    "search jobs",
    "job opportunities",
    "explore opportunities",
    "join our team",
    "view open roles",
    "our open roles",
)

ERROR_TITLE_PHRASES = (
    "job not found",
    "position no longer available",
    "posting no longer available",
    "page not found",
    "404",
    "position closed",
    "job expired",
)

ERROR_PATH_SEGMENTS = (
    "/404",
    "/not-found",
    "/not_found",
    "/error",
    "/job-not-found",
    "/position-unavailable",
    "/closed",
)


class ExtractedJobIdentityAssessment(BaseModel):
    identity_status: Literal["valid_job", "invalid_non_job", "uncertain_identity"]
    reason: str
    is_valid_for_promotion: bool
    warnings: list[str] = Field(default_factory=list)


def _extract_job_slug(path: str) -> str | None:
    """Extract specific job requisition ID or slug from a URL path if present."""
    match = re.search(
        r"/(?:jobs|job|posting|postings|positions|position|career|careers)/([a-zA-Z0-9_\-\.]+)",
        path,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).lower()
    return None


def assess_extracted_job_identity(
    requested_url: str,
    final_url: str,
    title: str | None = None,
    text: str | None = None,
    *,
    liveness_status: str | None = None,
) -> ExtractedJobIdentityAssessment:
    """Deterministically assess whether an extracted page represents the requested job posting.

    Core Invariant:
    A piece of external text may become canonical job-description evidence only if forkOS
    can establish that the extracted page still represents the requested job rather than
    a generic board, error page, redirect landing page, or company openings index.
    """
    req_clean = (requested_url or "").strip()
    fin_clean = (final_url or "").strip() or req_clean
    title_clean = (title or "").strip().lower()
    text_clean = (text or "").strip()
    warnings: list[str] = []

    req_parsed = urlparse(req_clean)
    fin_parsed = urlparse(fin_clean)

    req_path = req_parsed.path.rstrip("/")
    fin_path = fin_parsed.path.rstrip("/")
    fin_query = parse_qs(fin_parsed.query)

    # 1. Error query parameters in final destination (e.g. ?error=true on Greenhouse)
    if fin_query.get("error") in (["true"], ["1"], ["error"]) or "job_not_found" in fin_query:
        return ExtractedJobIdentityAssessment(
            identity_status="invalid_non_job",
            reason="provider_error_redirect",
            is_valid_for_promotion=False,
            warnings=["Destination URL explicitly indicates error parameter (e.g. ?error=true)."],
        )

    # 2. Error path segments in final destination
    if any(fin_path.endswith(err_seg) for err_seg in ERROR_PATH_SEGMENTS):
        return ExtractedJobIdentityAssessment(
            identity_status="invalid_non_job",
            reason="provider_error_redirect",
            is_valid_for_promotion=False,
            warnings=["Destination URL path ends with an error/404 indicator."],
        )

    # 3. Explicit error titles
    if any(err_title in title_clean for err_title in ERROR_TITLE_PHRASES):
        return ExtractedJobIdentityAssessment(
            identity_status="invalid_non_job",
            reason="provider_error_redirect",
            is_valid_for_promotion=False,
            warnings=[f"Extracted page title '{title}' indicates error or unavailable job."],
        )

    # 4. ATS-specific structural validation
    req_host = req_parsed.netloc.lower()
    fin_host = fin_parsed.netloc.lower()

    # Greenhouse checks
    is_greenhouse_req = "greenhouse.io" in req_host
    is_greenhouse_fin = "greenhouse.io" in fin_host
    if is_greenhouse_req:
        req_slug = _extract_job_slug(req_path)
        if req_slug:
            # Requested a specific Greenhouse job (e.g. /gitlab/jobs/4279007005)
            fin_slug = _extract_job_slug(fin_path)
            if not is_greenhouse_fin:
                warnings.append("Greenhouse request redirected outside greenhouse.io.")
            if fin_slug != req_slug:
                # Redirected to company root or lost the job ID
                return ExtractedJobIdentityAssessment(
                    identity_status="invalid_non_job",
                    reason="redirected_to_board_root",
                    is_valid_for_promotion=False,
                    warnings=[f"Greenhouse job id '{req_slug}' lost in destination '{fin_clean}'."],
                )

    # Lever checks
    is_lever_req = "jobs.lever.co" in req_host
    if is_lever_req:
        req_parts = [p for p in req_path.split("/") if p]
        if len(req_parts) >= 2:
            req_job_id = req_parts[1].lower()
            fin_parts = [p for p in fin_path.split("/") if p]
            if len(fin_parts) < 2 or fin_parts[1].lower() != req_job_id:
                return ExtractedJobIdentityAssessment(
                    identity_status="invalid_non_job",
                    reason="redirected_to_board_root",
                    is_valid_for_promotion=False,
                    warnings=["Lever job id lost in destination."],
                )

    # Ashby checks
    is_ashby_req = "jobs.ashbyhq.com" in req_host
    if is_ashby_req:
        req_parts = [p for p in req_path.split("/") if p]
        if len(req_parts) >= 2:
            req_job_id = req_parts[1].lower()
            fin_parts = [p for p in fin_path.split("/") if p]
            if len(fin_parts) < 2 or fin_parts[1].lower() != req_job_id:
                return ExtractedJobIdentityAssessment(
                    identity_status="invalid_non_job",
                    reason="redirected_to_board_root",
                    is_valid_for_promotion=False,
                    warnings=["Ashby job id lost in destination."],
                )

    # Workday checks
    is_workday_req = "myworkdayjobs.com" in req_host
    if is_workday_req:
        req_slug = _extract_job_slug(req_path) or (req_path.split("/")[-1] if req_path else None)
        if req_slug and req_slug not in ("en-us", "jobs", "careers") and req_slug.lower() not in fin_path.lower():
            return ExtractedJobIdentityAssessment(
                identity_status="invalid_non_job",
                reason="redirected_to_board_root",
                is_valid_for_promotion=False,
                warnings=["Workday job requisition lost in destination."],
            )

    # 5. General specific job path -> board root loss
    req_slug = _extract_job_slug(req_path)
    if req_slug:
        fin_slug = _extract_job_slug(fin_path)
        # If destination path is root or generic board, but requested was specific
        if not fin_slug and fin_path in ("", "/", "/jobs", "/careers", "/openings"):
            return ExtractedJobIdentityAssessment(
                identity_status="invalid_non_job",
                reason="redirected_to_board_root",
                is_valid_for_promotion=False,
                warnings=[f"Specific job path '{req_path}' redirected to board root '{fin_path}'."],
            )
        if fin_slug and fin_slug != req_slug and req_slug not in fin_clean.lower():
            return ExtractedJobIdentityAssessment(
                identity_status="invalid_non_job",
                reason="requested_job_id_lost",
                is_valid_for_promotion=False,
                warnings=[f"Requested job slug '{req_slug}' replaced by '{fin_slug}'."],
            )

    # 6. Generic Title Check
    is_generic_title = any(phrase in title_clean for phrase in GENERIC_TITLE_PHRASES)
    if is_generic_title:
        # If title is explicitly "Current openings at ..." or "Careers at ..."
        return ExtractedJobIdentityAssessment(
            identity_status="invalid_non_job",
            reason="generic_openings_page",
            is_valid_for_promotion=False,
            warnings=[f"Title '{title}' is a generic job board index title."],
        )

    # 7. Text Length Floor
    if len(text_clean) < 200:
        return ExtractedJobIdentityAssessment(
            identity_status="valid_job" if not is_generic_title else "invalid_non_job",
            reason="text_too_short",
            is_valid_for_promotion=False,
            warnings=["Extracted text is under minimum substantive threshold (< 200 chars)."],
        )

    # 8. Legitimate Canonical Redirects
    # Exact match: same URL or identical scheme + netloc + path
    if req_clean == fin_clean or (
        req_parsed.scheme == fin_parsed.scheme
        and req_parsed.netloc == fin_parsed.netloc
        and req_parsed.path == fin_parsed.path
    ):
        return ExtractedJobIdentityAssessment(
            identity_status="valid_job",
            reason="valid_specific_posting",
            is_valid_for_promotion=True,
            warnings=warnings,
        )

    # Canonical redirect: scheme change (http -> https), host migration, or job slug preserved
    if (req_slug and req_slug in fin_clean.lower()) or (
        req_parsed.netloc == fin_parsed.netloc and req_parsed.path == fin_parsed.path
    ):
        return ExtractedJobIdentityAssessment(
            identity_status="valid_job",
            reason="canonical_redirect_preserved_identity",
            is_valid_for_promotion=True,
            warnings=warnings,
        )

    # If hosts match and paths are identical except schema or trailing slash
    if req_host == fin_host and req_path == fin_path:
        return ExtractedJobIdentityAssessment(
            identity_status="valid_job",
            reason="canonical_redirect_preserved_identity",
            is_valid_for_promotion=True,
            warnings=warnings,
        )

    # 9. Uncertain redirect
    if req_host != fin_host or req_path != fin_path:
        return ExtractedJobIdentityAssessment(
            identity_status="uncertain_identity",
            reason="identity_uncertain",
            is_valid_for_promotion=False,
            warnings=[f"Redirected from '{req_clean}' to '{fin_clean}' without verifiable job identity preservation."],
        )

    return ExtractedJobIdentityAssessment(
        identity_status="valid_job",
        reason="valid_specific_posting",
        is_valid_for_promotion=True,
        warnings=warnings,
    )
