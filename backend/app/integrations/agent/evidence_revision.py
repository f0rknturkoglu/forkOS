"""Internal content identities for H3 source projections; never model scores."""

from __future__ import annotations

import hashlib
import json

from app.core.models import Event


def projection_digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def event_source_revision(event: Event, entity_title: str) -> str:
    # Event rows are append-only, but H3 also renders the mutable entity title.
    return projection_digest(
        (
            event.id,
            event.entity_id,
            event.entity_type,
            event.verb,
            event.payload,
            event.occurred_at,
            entity_title,
        )
    )
