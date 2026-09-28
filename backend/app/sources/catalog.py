"""Canonical opportunity source inventory for every queue and runner."""

from __future__ import annotations

from app.config import settings
from app.sources.announcements import SOURCES as ANNOUNCEMENT_SOURCES
from app.sources.forkjob_port import forkjob_sources


def opportunity_sources() -> list:
    """Return all configured sources, including explicit opt-in sources.

    Scheduling policy belongs to each caller; inventory must not drift between
    the UI, manual refresh, periodic polling, and lease estimation.
    """
    sources = [*forkjob_sources(include_opt_in=True), *ANNOUNCEMENT_SOURCES]
    if settings.career_ops_enabled and settings.career_ops_discovery_enabled:
        from app.sources.career_ops_sources import (
            get_career_ops_provider_sources,
            get_career_ops_sources,
        )

        sources.extend(get_career_ops_sources())
        sources.extend(get_career_ops_provider_sources())

    ids = [source.id for source in sources]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate opportunity source id in catalog")
    return sources
