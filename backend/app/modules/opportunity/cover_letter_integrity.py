"""Keep application cover text and package approval bound to one exact draft."""

from __future__ import annotations

import hashlib

from app.modules.opportunity.models import Application

REVIEW_REQUIRED_WARNING = "Cover letter changed; explicit review required."


def cover_letter_hash(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def sync_application_cover_letter(app: Application, text: str) -> bool:
    """Update both copies, invalidating review only for changed normalized content."""
    app.cover_letter = text
    if not app.package:
        return False

    package = dict(app.package)
    changed = cover_letter_hash(text) != cover_letter_hash(package.get("cover_letter") or "")
    package["cover_letter"] = text
    if changed:
        package["cover_letter_review"] = {
            "status": "pending",
            "reviewed_at": None,
            "content_hash": None,
        }
        if package.get("readiness") == "READY":
            package["readiness"] = "NEEDS_INPUT"
        for key in ("warnings", "readiness_reasons"):
            messages = list(package.get(key) or [])
            if REVIEW_REQUIRED_WARNING not in messages:
                messages.append(REVIEW_REQUIRED_WARNING)
            package[key] = messages
        package["generated_documents"] = [
            ref
            for ref in package.get("generated_documents") or []
            if ref.get("doc_type") != "cover_letter"
        ]
    app.package = package
    return changed
