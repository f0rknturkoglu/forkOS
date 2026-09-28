from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.opportunity.candidate_fit import (
    ALGORITHM,
    canonical_description,
    score_canonical_opportunity,
)
from app.sources import forkjob_port
from app.sources.forkjob_core.config import Config

pytestmark = pytest.mark.no_database


def _opportunity(source: str, *, description: str | None = None):
    now = datetime(2026, 9, 1, tzinfo=UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        kind="job",
        source=source,
        external_id=None,
        url="https://example.com/jobs/1",
        organization="Acme",
        location="Remote, Germany",
        country="DE",
        region="EU",
        remote="remote",
        compensation=None,
        published_at=now,
        found_at=now,
        raw={"description": description} if description else {},
        score=None,
        score_source=None,
        score_computed_at=None,
    )


def test_equivalent_jobs_receive_same_fast_score_across_sources(monkeypatch):
    monkeypatch.setattr(forkjob_port, "SCORING", Config())
    now = datetime(2026, 9, 2, tzinfo=UTC)
    description = "Python and Kubernetes platform engineering with distributed systems. " * 4
    forkjob = _opportunity("forkjob_core:greenhouse:acme", description=description)
    career_ops = _opportunity("careerops:greenhouse", description=description)
    score_canonical_opportunity(forkjob, "Senior Platform Engineer", now=now)
    score_canonical_opportunity(career_ops, "Senior Platform Engineer", now=now)
    assert forkjob.score == career_ops.score
    assert forkjob.score is not None
    assert forkjob.score_source == career_ops.score_source == ALGORITHM
    assert forkjob.raw["candidate_fit"]["reasons"] == career_ops.raw["candidate_fit"]["reasons"]


def test_missing_jd_gets_basic_score_then_richer_jd_recomputes(monkeypatch):
    monkeypatch.setattr(forkjob_port, "SCORING", Config())
    now = datetime(2026, 9, 2, tzinfo=UTC)
    opportunity = _opportunity("careerops:boards")
    score_canonical_opportunity(opportunity, "Platform Engineer", now=now)
    assert opportunity.score is not None
    assert opportunity.raw["candidate_fit"]["completeness"] == "basic"
    opportunity.raw["description"] = "Python and Kubernetes platform engineering. " * 5
    score_canonical_opportunity(opportunity, "Platform Engineer", now=now)
    assert opportunity.raw["candidate_fit"]["completeness"] == "full_jd"
    assert canonical_description(opportunity.raw) == opportunity.raw["description"].strip()
