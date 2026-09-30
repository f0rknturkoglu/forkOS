"""Canonical, source-independent fast candidate-fit scoring for jobs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from app.sources import forkjob_port
from app.sources.forkjob_core.models import DateSource, Job, Layer, Region, WorkMode
from app.sources.forkjob_core.normalize import parse_location
from app.sources.forkjob_core.score import score_job

ALGORITHM = "forkjob_core-candidate-fit-v2"


def scoring_revision() -> str:
    payload = json.dumps(asdict(forkjob_port.SCORING.scoring), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def canonical_description(raw: dict[str, Any] | None) -> str | None:
    """Read one normalized JD path, falling back to older source payloads."""
    data = raw if isinstance(raw, dict) else {}
    forkjob = data.get("forkjob") if isinstance(data.get("forkjob"), dict) else {}
    for value in (data.get("description"), forkjob.get("description"), data.get("summary")):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def score_canonical_opportunity(opportunity: Any, title: str, *, now: datetime) -> None:
    """Score the merged canonical listing, regardless of acquisition source."""
    if opportunity.kind != "job" or not title.strip():
        return
    raw = opportunity.raw if isinstance(opportunity.raw, dict) else {}
    forkjob = raw.get("forkjob") if isinstance(raw.get("forkjob"), dict) else {}
    description = canonical_description(raw)
    location = parse_location(opportunity.location, description=description)
    region_value = opportunity.region
    region = Region(region_value) if region_value in Region._value2member_map_ else location.region
    mode_value = opportunity.remote
    mode = WorkMode(mode_value) if mode_value in WorkMode._value2member_map_ else location.work_mode
    posted_at = opportunity.published_at
    if posted_at is not None and posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=UTC)
    scored = Job.build(
        url=opportunity.url or f"https://invalid.local/opportunity/{opportunity.id}",
        source="canonical",
        layer=Layer.B,
        company=opportunity.organization or "?",
        title=title,
        external_id=opportunity.external_id,
        location=opportunity.location,
        city=raw.get("city") or forkjob.get("city") or location.city,
        country=opportunity.country or location.country,
        region=region,
        remote=mode is WorkMode.REMOTE if mode is not WorkMode.UNKNOWN else None,
        work_mode=mode,
        department=raw.get("department") or forkjob.get("department"),
        description=description,
        salary=opportunity.compensation,
        language=raw.get("language") or forkjob.get("language"),
        posted_at=posted_at,
        date_source=(DateSource(forkjob["date_source"])
                     if forkjob.get("date_source") in DateSource._value2member_map_
                     else DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED),
        first_seen=opportunity.found_at or now,
    )
    score_job(scored, forkjob_port.SCORING)
    opportunity.score = scored.score
    opportunity.score_source = ALGORITHM
    opportunity.score_computed_at = now
    opportunity.raw = {
        **raw,
        "candidate_fit": {
            "algorithm": ALGORITHM,
            "scoring_revision": scoring_revision(),
            "reasons": scored.reasons,
            "completeness": "full_jd" if description and len(description) >= 100 else "basic",
        },
    }
