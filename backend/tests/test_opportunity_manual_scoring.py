from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.modules.opportunity import service
from app.modules.opportunity.candidate_fit import ALGORITHM as FAST_SCORE_ALGORITHM
from app.modules.opportunity.candidate_match import ALGORITHM as CANDIDATE_MATCH_ALGORITHM
from app.modules.opportunity.schemas import OpportunityIn, OpportunityPatch
from app.sources import forkjob_port
from app.sources.forkjob_core.config import Config


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_manual_job_create_gets_canonical_fast_score_and_match(db_session: AsyncSession, monkeypatch):
    """Manual job creation runs score_canonical_opportunity and apply_candidate_match."""
    monkeypatch.setattr(forkjob_port, "SCORING", Config())

    job_in = OpportunityIn(
        title="Senior Platform Engineer",
        kind="job",
        organization="Acme Corp",
        location="Remote, Germany",
        remote="remote",
        compensation="90000 EUR",
        notes="Applied manually through referral",
        raw={"description": "Distributed systems, Python, Kubernetes and platform tooling at scale."},
    )
    created = await service.create(db_session, job_in)

    assert created.id is not None
    assert created.score is not None
    assert created.score_source == FAST_SCORE_ALGORITHM
    assert created.score_computed_at is not None
    assert created.raw.get("candidate_fit", {}).get("algorithm") == FAST_SCORE_ALGORITHM
    assert created.raw.get("candidate_match", {}).get("algorithm") == CANDIDATE_MATCH_ALGORITHM


@pytest.mark.asyncio
async def test_manual_job_patch_refreshes_score_on_ranking_relevant_fields(db_session: AsyncSession, monkeypatch):
    """Patching title, location, or description refreshes fast score and candidate match."""
    monkeypatch.setattr(forkjob_port, "SCORING", Config())

    job_in = OpportunityIn(
        title="Junior Developer",
        kind="job",
        organization="Acme",
        location="London, UK",
        remote="onsite",
    )
    created = await service.create(db_session, job_in)
    initial_score = created.score
    initial_computed_at = created.score_computed_at

    # 1. Title change refreshes fast score
    patched_title = await service.patch(
        db_session,
        created.id,
        OpportunityPatch(title="Senior Platform Engineer"),
    )
    assert patched_title is not None
    assert patched_title.title == "Senior Platform Engineer"
    assert patched_title.score_computed_at is not None
    assert patched_title.score_computed_at >= initial_computed_at
    assert patched_title.score_source == FAST_SCORE_ALGORITHM

    # 2. Location change refreshes fast score
    after_title_computed_at = patched_title.score_computed_at
    patched_loc = await service.patch(
        db_session,
        created.id,
        OpportunityPatch(location="Remote, Germany", remote="remote"),
    )
    assert patched_loc is not None
    assert patched_loc.location == "Remote, Germany"
    assert patched_loc.score_computed_at >= after_title_computed_at

    # 3. Description update in raw refreshes candidate match and fast score
    after_loc_computed_at = patched_loc.score_computed_at
    patched_desc = await service.patch(
        db_session,
        created.id,
        OpportunityPatch(raw={"description": "Python Kubernetes platform engineering " * 5}),
    )
    assert patched_desc is not None
    assert patched_desc.score_computed_at >= after_loc_computed_at
    assert patched_desc.raw.get("candidate_fit", {}).get("completeness") == "full_jd"


@pytest.mark.asyncio
async def test_manual_job_status_only_patch_does_not_falsely_invalidate_ranking(db_session: AsyncSession, monkeypatch):
    """Workflow-only patches (status, notes, follow_up_at) preserve score without recomputing."""
    monkeypatch.setattr(forkjob_port, "SCORING", Config())

    job_in = OpportunityIn(
        title="Staff Engineer",
        kind="job",
        organization="Acme",
        location="Remote, Germany",
        remote="remote",
        raw={"description": "Platform engineering systems."},
    )
    created = await service.create(db_session, job_in)
    score_before = created.score
    computed_at_before = created.score_computed_at
    match_before = created.raw.get("candidate_match")
    skill_match_ratio_before = created.profile_match_ratio

    assert score_before is not None
    assert computed_at_before is not None

    # Patch ONLY status and notes
    patched = await service.patch(
        db_session,
        created.id,
        OpportunityPatch(status="shortlisted", notes="First round scheduled next week"),
    )
    assert patched is not None
    assert patched.status == "shortlisted"
    assert patched.notes == "First round scheduled next week"

    # Score and candidate match MUST remain untouched
    assert patched.score == score_before
    assert patched.score_source == FAST_SCORE_ALGORITHM
    assert patched.score_computed_at == computed_at_before
    assert patched.profile_match_ratio == skill_match_ratio_before
    assert patched.raw.get("candidate_match") == match_before


@pytest.mark.asyncio
async def test_manual_job_receives_candidate_match_using_current_candidate_context(db_session: AsyncSession, monkeypatch):
    """Manual job create evaluates against candidate context without fake zero."""
    monkeypatch.setattr(forkjob_port, "SCORING", Config())

    job_in = OpportunityIn(
        title="Backend Python Engineer",
        kind="job",
        organization="Acme",
        raw={"description": "FastAPI, PostgreSQL, Docker, Python backend developer."},
    )
    created = await service.create(db_session, job_in)

    match = created.raw.get("candidate_match")
    assert isinstance(match, dict)
    assert match.get("algorithm") == CANDIDATE_MATCH_ALGORITHM
    assert "candidate_revision" in match
    assert "listing_fingerprint" in match
    # Ratio is None or float in [0..1]
    ratio = created.profile_match_ratio
    assert ratio is None or (0.0 <= ratio <= 1.0)
