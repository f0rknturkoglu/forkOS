from __future__ import annotations

import pytest

from app.sources.announcements import SOURCES as ANNOUNCEMENT_SOURCES
from app.sources.forkjob_port import forkjob_sources

pytestmark = pytest.mark.no_database


def test_automatic_catalog_has_unique_valid_adapter_metadata():
    sources = [*forkjob_sources(), *ANNOUNCEMENT_SOURCES]
    ids = [source.id for source in sources]

    assert ids
    assert len(ids) == len(set(ids))
    assert all(source_id.strip() for source_id in ids)
    assert all(source.interval_minutes > 0 for source in sources)


def test_opt_in_linkedin_is_manual_only():
    automatic = {source.id for source in forkjob_sources()}
    manual = {source.id for source in forkjob_sources(include_opt_in=True)}

    assert "jobhunter:linkedin" not in automatic
    assert "jobhunter:linkedin" in manual
