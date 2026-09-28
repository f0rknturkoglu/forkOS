"""C6/C7 safety, lineage and observed-outcome regressions."""

import copy
from datetime import UTC, datetime, timedelta

import pytest

from app.db import SessionLocal
from app.modules.document import service as documents
from app.modules.opportunity import interview_intelligence as interviews
from app.modules.opportunity.candidate_context import build_candidate_career_context
from app.modules.opportunity.career_analytics import (
    compute_snapshot,
    conversion,
    normalize_requirement,
    snapshot,
)
from app.modules.opportunity.evaluation_service import CareerEvaluationService
from app.modules.opportunity.models import ApplicationHistory, CareerStory, Interview
from app.modules.opportunity.package_service import ApplicationPackageService
from app.modules.opportunity.reasoner.mock import DeterministicMockCareerReasoner
from tests.test_career_closure_documents import synthetic_cv
from tests.test_opportunity_application_package import _seed_test_opportunity


async def seed(session):
    await documents.create_local_document(
        session, title="fixture.docx", content=synthetic_cv(), category="cv", commit=False
    )
    opportunity = await _seed_test_opportunity(session)
    reasoner = DeterministicMockCareerReasoner()
    await CareerEvaluationService(reasoner).evaluate_opportunity(session, opportunity.id)
    await ApplicationPackageService(reasoner).prepare_application_package(session, opportunity.id)
    row = Interview(opportunity_id=opportunity.id, stage="genel")
    session.add(row)
    await session.flush()
    return opportunity, row


async def test_prep_current_evidence_unknown_stage_and_stale():
    async with SessionLocal() as session:
        opp, row = await seed(session)
        prep = await interviews.prepare(session, row.id)
        assert prep.interview_stage is None
        assert len(prep.focus_areas) <= 6
        assert prep.evaluation_revision
        assert prep.story_recommendations == []
        assert "missing_story_gap" in prep.unknowns
        assert not (await interviews.get_intelligence(session, row.id)).prep.is_stale
        opp.deep_evaluation = {
            **opp.deep_evaluation,
            "overall_assessment": "Changed material evaluation",
        }
        assert (await interviews.get_intelligence(session, row.id)).prep.is_stale
        row.stage = "technical_screen"
        assert (await interviews.prepare(session, row.id)).interview_stage == "technical_screen"
        opp.raw = {"description": "no valid job"}
        with pytest.raises(ValueError, match="güncel"):
            await interviews.prepare(session, row.id)


async def test_story_ids_are_canonical_and_not_created_by_prep():
    from sqlalchemy import func, select

    from app.core.entity import create_entity

    async with SessionLocal() as session:
        _, row = await seed(session)
        ent = await create_entity(session, type="career_story", title="Fixture story")
        story = CareerStory(
            id=ent.id,
            tags=["python"],
            action="Implemented fixture",
            result="Measured fixture",
            provenance="supported",
        )
        session.add(story)
        await session.flush()
        await CareerEvaluationService(DeterministicMockCareerReasoner()).evaluate_opportunity(
            session, row.opportunity_id, force=True
        )
        prep = await interviews.prepare(session, row.id)
        for recommendation in prep.story_recommendations:
            assert await session.get(CareerStory, __import__("uuid").UUID(recommendation.story_id))
            assert recommendation.evidence_refs == [f"career_story:{story.id}"]
            assert recommendation.evidence_refs[0] in prep.evidence_refs
            context = await build_candidate_career_context(session)
            assert context.get_fact(recommendation.evidence_refs[0]) is not None
        assert prep.story_recommendations
        assert await session.scalar(select(func.count()).select_from(CareerStory)) == 1
        assert story.action == "Implemented fixture"
        legacy = copy.deepcopy(row.intelligence)
        legacy["prep"]["story_recommendations"][0]["evidence_refs"] = [f"story:{story.id}"]
        legacy["prep"]["evidence_refs"] = [f"story:{story.id}"]
        row.intelligence = legacy
        loaded = await interviews.get_intelligence(session, row.id)
        assert loaded.prep.story_recommendations[0].evidence_refs == [f"career_story:{story.id}"]
        assert loaded.prep.evidence_refs == [f"career_story:{story.id}"]


async def test_practice_bounded_and_unverified_claim_flagged():
    async with SessionLocal() as session:
        _, row = await seed(session)
        await interviews.prepare(session, row.id)
        result = await interviews.practice(
            session,
            row.id,
            interviews.PracticeIn(
                question="Experience?", candidate_answer="I led 500 engineers for 20 years."
            ),
        )
        assert result.feedback["technical_correctness"] == "needs_review"
        assert result.gaps and "unsupported_claim" in result.gaps[0]
        row.intelligence = {**row.intelligence, "practice": [result.model_dump()] * 50}
        with pytest.raises(ValueError, match="50"):
            await interviews.practice(
                session, row.id, interviews.PracticeIn(question="q", candidate_answer="a")
            )


async def test_practice_with_canonical_source_text_does_not_claim_unsupported():
    async with SessionLocal() as session:
        _, row = await seed(session)
        await interviews.prepare(session, row.id)
        candidate = await build_candidate_career_context(session)
        source = next(
            fact for fact in candidate.facts
            if fact.verified and isinstance(fact.value, dict) and fact.value.get("text")
        )
        result = await interviews.practice(
            session,
            row.id,
            interviews.PracticeIn(question="Experience?", candidate_answer=str(source.value["text"])),
        )
        assert source.key in result.evidence_refs
        assert not any("unsupported_claim" in gap for gap in result.gaps)
        assert result.feedback["technical_correctness"] == "needs_review"


async def test_debrief_no_inferred_outcome_or_send_and_analytics_lineage():
    async with SessionLocal() as session:
        opp, row = await seed(session)
        prep = await interviews.prepare(session, row.id)
        now = datetime.now(UTC)
        report = await interviews.debrief(
            session,
            row.id,
            interviews.DebriefIn(
                occurred_at=now,
                candidate_notes="I struggled with PostgreSQL",
                topics=["Postgres"],
                perceived_gaps=["PostgreSQL"],
                follow_up_items=["Thank interviewer"],
            ),
        )
        assert report.source_type == "user_report"
        assert report.outcome_if_known is None
        assert report.follow_up_status == "draft_requires_approval"
        assert row.outcome is None
        assert opp.rejection_reason is None
        session.add(
            ApplicationHistory(
                opportunity_id=opp.id,
                to_status="applied",
                from_status="preparing",
                at=now - timedelta(days=3),
            )
        )
        session.add(
            ApplicationHistory(
                opportunity_id=opp.id, to_status="interview", from_status="applied", at=now
            )
        )
        await session.flush()
        result = await snapshot(session, now=now + timedelta(seconds=1))
        assert result.funnel["applied"] == 1 and result.funnel["interview"] == 1
        assert result.conversions["applied_to_interview"].rate is None
        assert result.lineage[0]["base_cv_document_id"]
        assert result.lineage[0]["derivative_documents"]
        assert prep.candidate_context_revision == opp.deep_evaluation["candidate_context_revision"]
        assert all(not c["weights_changed"] for c in result.calibration)


def record(i, *, status="rejected", reason=None, country="DE", source="fixture"):
    now = datetime(2026, 9, 26, tzinfo=UTC)
    return {
        "id": str(i),
        "status": status,
        "applied_at": now - timedelta(days=5),
        "history": [
            {"to_status": "applied", "from_status": "preparing", "at": now - timedelta(days=5)},
            {"to_status": "interview", "from_status": "applied", "at": now - timedelta(days=2)},
        ],
        "interviews": [],
        "package": {"generated_documents": [{"document_id": "real-id"}]},
        "evaluation": {
            "must_have": [
                {"requirement": "Postgres", "classification": "partial"},
                {"requirement": "PostgreSQL", "classification": "partial"},
            ],
            "nice_to_have": [{"requirement": "k8s", "classification": "missing"}],
        },
        "evaluation_stale": False,
        "role_family": "backend",
        "seniority": None,
        "country": country,
        "remote": "remote",
        "source": source,
        "company": "Fixture",
        "cv_version": "cv-version",
        "package_version": "package-rev",
        "time_period": "2026-09",
        "score": 90,
        "rejection_reason": reason,
    }


@pytest.mark.no_database
def test_funnel_denominators_durations_aliases_and_noncausal_cohorts():
    rows = [record(i, reason="User says salary mismatch" if i == 0 else None) for i in range(3)]
    before = copy.deepcopy(rows)
    result = compute_snapshot(rows, days=30, minimum=3, now=datetime(2026, 9, 26, tzinfo=UTC))
    assert rows == before
    assert (
        result.funnel["discovered"]
        == result.funnel["applied"]
        == result.funnel["interview"]
        == result.funnel["rejected"]
        == 3
    )
    assert result.funnel["reply"] == 0
    assert result.conversions["applied_to_interview"].rate == 1
    assert result.conversions["applied_to_interview"].denominator == 3
    assert result.durations["applied_to_interview"]["median_days"] == 3
    assert result.durations["applied_to_interview"]["mean_days"] == 3
    pg = next(s for s in result.skill_gaps if s.requirement == "postgresql")
    assert pg.opportunities_seen == pg.partial_count == 3
    assert next(s for s in result.skill_gaps if s.requirement == "kubernetes").missing_count == 3
    assert result.rejection_patterns[0]["reason"] == "User says salary mismatch"
    assert result.rejection_patterns[1]["classification"] == "unknown"
    assert not any(r["employer_cause_confirmed"] for r in result.rejection_patterns)
    assert result.source_performance[0].sample_size == 3
    assert next(c for c in result.geography if c.dimension == "country").value == "DE"
    assert all(not c["weights_changed"] for c in result.calibration)
    assert (
        result.fingerprint
        == compute_snapshot(
            rows, days=30, minimum=3, now=datetime(2026, 9, 26, tzinfo=UTC)
        ).fingerprint
    )


@pytest.mark.no_database
def test_small_samples_missing_history_and_stale_evidence():
    row = record(1)
    row["history"] = []
    row["applied_at"] = None
    row["evaluation_stale"] = True
    result = compute_snapshot([row], days=30, minimum=3, now=datetime(2026, 9, 26, tzinfo=UTC))
    assert result.funnel["rejected"] == 1 and result.funnel["applied"] == 0
    assert result.conversions["applied_to_interview"].rate is None
    assert not result.durations and not result.skill_gaps
    assert all(c.status == "insufficient_sample" for c in result.cohorts)
    assert conversion(4, 3, 3).status == "incomplete_history"
    assert normalize_requirement("  Postgres ") == "postgresql"


@pytest.mark.no_database
def test_explicit_feedback_preserved_as_quote_not_confirmed_cause():
    row = record(1)
    row["interviews"] = [
        {
            "id": "fixture",
            "stage": "technical_screen",
            "intelligence": {
                "debrief": {
                    "employer_feedback": "PostgreSQL experience required.",
                    "source_type": "user_report",
                }
            },
        }
    ]
    result = compute_snapshot([row], days=30, minimum=3, now=datetime(2026, 9, 26, tzinfo=UTC))
    rejection = result.rejection_patterns[0]
    assert rejection["classification"] == "explicit_reason"
    assert rejection["reason"] == "PostgreSQL experience required."
    assert rejection["source_type"] == "user_reported_employer_quote"
    assert not rejection["employer_cause_confirmed"]
    assert (
        next(
            s for s in result.skill_gaps if s.requirement == "postgresql"
        ).explicit_feedback_mentions
        == 1
    )


@pytest.mark.no_database
async def test_semantic_surface_annotations_and_bounds():
    from app.integrations.agent.mcp import mcp_server

    tools = {tool.name: tool for tool in await mcp_server.list_tools()}
    assert tools["forkos_career_interview"].annotations.read_only_hint is False
    assert tools["forkos_career_interview"].annotations.destructive_hint is False
    assert tools["forkos_career_insights"].annotations.read_only_hint is True
    assert tools["forkos_career_interview"].input_schema["properties"]["intent"]["enum"] == [
        "prepare",
        "practice",
        "debrief",
    ]


async def test_semantic_interview_and_read_only_insights_transport():
    from tests.agent_test_utils import capture_db_content_fingerprint, mcp_session, tool_payload

    async with SessionLocal() as session:
        _, row = await seed(session)
        ident = str(row.id)
        await session.commit()
    async with mcp_session() as client:
        prep = await client.call_tool(
            "forkos_career_interview", {"interview_id": ident, "intent": "prepare"}
        )
        assert not prep.is_error
        assert tool_payload(prep)["data"]["provider"] == "deterministic"
        report = await client.call_tool(
            "forkos_career_interview",
            {
                "interview_id": ident,
                "intent": "debrief",
                "payload": {
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "candidate_notes": "Fixture not actual interview",
                },
            },
        )
        assert not report.is_error
        assert tool_payload(report)["data"]["outcome_if_known"] is None
        async with SessionLocal() as session:
            before = await capture_db_content_fingerprint(session)
        result = await client.call_tool("forkos_career_insights", {"days": 30})
        assert not result.is_error
        assert tool_payload(result)["data"]["population"] == 1
        async with SessionLocal() as session:
            assert await capture_db_content_fingerprint(session) == before
