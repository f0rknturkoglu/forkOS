"""Conservative, source-independent real-world job identity evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from app.sources.forkjob_core.models import canonical_url


@dataclass(frozen=True)
class ListingIdentity:
    source: str
    external_id: str | None
    url: str | None
    apply_url: str | None
    provider: str | None
    requisition_id: str | None
    company: str | None
    title: str | None
    location: str | None
    description: str | None
    published_at: datetime | None


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def _url(value: str | None) -> str | None:
    return canonical_url(value) if isinstance(value, str) and value.strip() else None


def _published(value: Any) -> datetime | None:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _provider(source: str, raw: dict[str, Any]) -> str | None:
    career_ops = raw.get("career_ops") or {}
    if isinstance(career_ops, dict) and career_ops.get("provider"):
        return _text(career_ops["provider"])
    parts = source.split(":")
    if parts[0] == "forkjob_core" and len(parts) >= 3:
        return _text(parts[1])
    if parts[0] == "careerops" and len(parts) >= 2:
        return _text(parts[1])
    return None


def identity_from_stored(row: Any) -> ListingIdentity:
    raw = row.raw if isinstance(row.raw, dict) else {}
    forkjob = raw.get("forkjob") or {}
    if not isinstance(forkjob, dict):
        forkjob = {}
    return ListingIdentity(
        source=row.source,
        external_id=row.external_id,
        url=row.url,
        apply_url=raw.get("apply_url") or forkjob.get("apply_url"),
        provider=_provider(row.source, raw),
        requisition_id=raw.get("requisition_id") or forkjob.get("requisition_id"),
        company=row.organization,
        title=raw.get("title") or forkjob.get("title"),
        location=row.location,
        description=raw.get("description") or forkjob.get("description"),
        published_at=_published(row.published_at),
    )


def identity_from_incoming(job: Any, raw: dict[str, Any], source: str) -> ListingIdentity:
    forkjob = raw.get("forkjob") or {}
    if not isinstance(forkjob, dict):
        forkjob = {}
    return ListingIdentity(
        source=source,
        external_id=getattr(job, "external_id", None) or getattr(job, "job_id", None),
        url=getattr(job, "url", None),
        apply_url=raw.get("apply_url") or forkjob.get("apply_url"),
        provider=_provider(source, raw),
        requisition_id=raw.get("requisition_id") or forkjob.get("requisition_id"),
        company=getattr(job, "company", None),
        title=getattr(job, "title", None),
        location=getattr(job, "location", None),
        description=getattr(job, "description", None),
        published_at=_published(getattr(job, "published_at", None)),
    )


def same_real_world_posting(left: ListingIdentity, right: ListingIdentity) -> bool:
    """Merge only with a stable ID/URL or multiple independent strong signals."""
    if left.source == right.source and left.external_id and left.external_id == right.external_id:
        return True
    if _url(left.url) and _url(left.url) == _url(right.url):
        return True
    if _url(left.apply_url) and _url(left.apply_url) == _url(right.apply_url):
        return True

    same_company = bool(_text(left.company)) and _text(left.company) == _text(right.company)
    if not same_company:
        return False
    if left.requisition_id and right.requisition_id:
        if left.requisition_id != right.requisition_id:
            return False
        return bool(left.provider and left.provider == right.provider)
    if (
        left.provider
        and left.provider == right.provider
        and left.external_id
        and right.external_id
        and left.external_id == right.external_id
        and "://" not in left.external_id
    ):
        return True

    # A shared coarse cluster key is insufficient. Exact substantial JD text,
    # specific title, location and compatible publication dates are required.
    title = _text(left.title)
    description = _text(left.description)
    first_date = _published(left.published_at)
    second_date = _published(right.published_at)
    return bool(
        len(title.split()) >= 3
        and title == _text(right.title)
        and _text(left.location)
        and _text(left.location) == _text(right.location)
        and len(description) >= 200
        and description == _text(right.description)
        and first_date
        and second_date
        and abs(first_date - second_date) <= timedelta(days=14)
    )
