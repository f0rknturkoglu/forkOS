"""C8 read-model safety: stable evidence, bounded advice, explicit denominator."""

from datetime import UTC, datetime

import pytest

from app.modules.opportunity.career_analytics import CareerAnalyticsSnapshot, SkillGapSignal
from app.modules.opportunity.career_strategy import build_strategy

pytestmark = pytest.mark.no_database


NOW = datetime(2026, 9, 28, tzinfo=UTC)


def analytics(missing: int = 4) -> CareerAnalyticsSnapshot:
    return CareerAnalyticsSnapshot(
        period={
            "start": "2026-06-30T00:00:00+00:00",
            "end": "2026-09-28T00:00:00+00:00",
            "basis": "discovery",
        },
        generated_at=NOW.isoformat(),
        fingerprint="analytics-time-dependent",
        population=20,
        evaluated_population=20,
        minimum_sample=3,
        funnel={"discovered": 20, "applied": 8, "interview": 1},
        conversions={},
        durations={},
        cohorts=[],
        rejection_patterns=[],
        skill_gaps=[
            SkillGapSignal(
                requirement="kubernetes",
                opportunities_seen=20,
                strong_count=0,
                partial_count=0,
                missing_count=missing,
                unknown_count=20 - missing,
                interview_mentions=0,
                role_families=["backend"],
                confidence="observed_association",
                evidence_refs=[f"evaluation:{i}" for i in range(20)],
            )
        ],
        source_performance=[],
        geography=[],
        lineage=[],
        calibration=[],
        confidence_notes=[],
        evidence_refs=[],
        briefing={},
    )


def test_repeated_gap_is_descriptive_and_never_creates_a_canonical_goal():
    result = build_strategy(analytics(), projects=[], milestones=[], topics=[], todos=[], now=NOW)
    assert result.signals[0].evidence_type == "descriptive_pattern"
    assert result.signals[0].sample_size == 20
    assert "işveren gerekçesi" in result.signals[0].caveat
    assert result.primary_action is None
    assert result.goal_progress == []


def test_small_gap_is_not_promoted_and_evidence_change_updates_revision():
    first = build_strategy(analytics(), projects=[], milestones=[], topics=[], todos=[], now=NOW)
    weaker = build_strategy(analytics(2), projects=[], milestones=[], topics=[], todos=[], now=NOW)
    assert weaker.signals == []
    assert weaker.evidence_revision != first.evidence_revision


def test_revision_ignores_generation_time_but_progress_requires_denominator():
    project = [{"id": "p1", "title": "Backend", "status": "active", "next_action": "Deploy"}]
    first = build_strategy(
        analytics(), projects=project, milestones=[], topics=[], todos=[], now=NOW
    )
    later = build_strategy(
        analytics(), projects=project, milestones=[], topics=[], todos=[], now=NOW.replace(hour=1)
    )
    assert first.evidence_revision == later.evidence_revision
    assert first.project_progress[0].progress_percent is None
    milestone = [{"id": "m1", "project_id": "p1", "completed_at": NOW.isoformat()}]
    completed = build_strategy(
        analytics(), projects=project, milestones=milestone, topics=[], todos=[], now=NOW
    )
    assert completed.project_progress[0].progress_percent == 100
    assert completed.evidence_revision != first.evidence_revision


def test_what_now_is_bounded_and_due_first():
    todos = [
        {
            "id": str(i),
            "title": f"Task {i}",
            "status": "open",
            "due_at": f"2026-10-{i + 1:02d}T00:00:00+00:00",
        }
        for i in range(5)
    ]
    result = build_strategy(
        analytics(), projects=[], milestones=[], topics=[], todos=todos, now=NOW
    )
    assert result.primary_action.title == "Task 0"
    assert len(result.alternatives) <= 2
    assert all(action.evidence_refs for action in [result.primary_action, *result.alternatives])


def test_existing_goal_is_user_statement_and_changes_revision():
    original = build_strategy(analytics(), projects=[], milestones=[], topics=[], todos=[], now=NOW)
    with_goal = build_strategy(
        analytics(),
        projects=[],
        milestones=[],
        topics=[],
        todos=[],
        now=NOW,
        goals=[
            {
                "memory_id": "g1",
                "kind": "goal",
                "title": "Avrupa'da backend rolü",
                "text": "Avrupa'da backend rolü arıyorum",
                "source_mode": "explicit_user",
                "importance": 5,
                "revision": "v1",
                "effective_status": "active",
                "related_forkos_ids": [],
            }
        ],
    )
    assert with_goal.existing_goals[0].evidence_type == "user_statement"
    assert with_goal.existing_goals[0].evidence_refs == ["hot_memory:g1"]
    assert with_goal.evidence_revision != original.evidence_revision


def test_h2_source_modes_and_revision_are_truthful():
    goal = {
        "memory_id": "g1",
        "kind": "goal",
        "title": "Backend hedefi",
        "text": "Backend alanına yönel",
        "source_mode": "approved_candidate",
        "importance": 4,
        "revision": "v1",
        "effective_status": "active",
        "related_forkos_ids": [],
    }
    first = build_strategy(
        analytics(), projects=[], milestones=[], topics=[], todos=[], now=NOW, goals=[goal]
    )
    assert first.existing_goals[0].evidence_type == "approved_memory"
    assert "açık kullanıcı beyanı" in first.existing_goals[0].caveat
    changed = build_strategy(
        analytics(),
        projects=[],
        milestones=[],
        topics=[],
        todos=[],
        now=NOW,
        goals=[{**goal, "revision": "v2", "text": "Güncellenmiş yön"}],
    )
    assert changed.evidence_revision != first.evidence_revision


def test_retired_h2_and_a4_model_goal_cannot_impersonate_intent():
    excluded = [
        {
            "memory_id": "retired",
            "kind": "goal",
            "title": "Eski yön",
            "text": "Eski yön",
            "source_mode": "explicit_user",
            "revision": "v1",
            "effective_status": "retired",
        },
        {
            "memory_id": "expired",
            "kind": "goal",
            "title": "Süresi geçmiş",
            "text": "Süresi geçmiş",
            "source_mode": "explicit_user",
            "revision": "v1",
            "effective_status": "expired",
        },
        {
            "card_id": "a4-model-goal",
            "kind": "goal",
            "statement": "Model çıkarımı",
            "evidence_class": "model_derived",
            "revision": "v1",
        },
    ]
    result = build_strategy(
        analytics(), projects=[], milestones=[], topics=[], todos=[], now=NOW, goals=excluded
    )
    baseline = build_strategy(analytics(), projects=[], milestones=[], topics=[], todos=[], now=NOW)
    assert result.existing_goals == []
    assert result.evidence_revision == baseline.evidence_revision


def test_explicit_feedback_remains_one_unverified_report():
    source = analytics()
    source.rejection_patterns = [
        {
            "classification": "explicit_reason",
            "reason": "Kubernetes örneği zayıftı",
            "evidence_refs": ["interview:i1:debrief:employer_feedback"],
        }
    ]
    result = build_strategy(source, projects=[], milestones=[], topics=[], todos=[], now=NOW)
    feedback = next(
        signal for signal in result.signals if signal.evidence_type == "explicit_feedback"
    )
    assert feedback.sample_size == 1
    assert feedback.confidence == "low"
    assert "bağımsız doğrulama" in feedback.caveat


def test_goal_change_uses_only_comparable_weekly_snapshot():
    goal = {
        "id": "g1",
        "title": "Backend hedefi",
        "status": "active",
        "completed_milestones": 1,
        "milestone_count": 2,
        "progress_percent": 50,
        "milestones": [{"id": "m1", "completed_at": NOW.isoformat()}],
    }
    previous = [{"goal_id": "g1", "completed_milestones": 0, "milestone_count": 2}]
    result = build_strategy(
        analytics(),
        projects=[],
        milestones=[],
        topics=[],
        todos=[],
        now=NOW,
        canonical_goals=[goal],
        previous_goal_progress=previous,
    )
    assert result.goal_progress[0].changed_since_last_review == "+1 tamamlanan taş"
    assert "Backend hedefi" in result.what_changed
    previous[0]["milestone_count"] = 3
    changed_denominator = build_strategy(
        analytics(),
        projects=[],
        milestones=[],
        topics=[],
        todos=[],
        now=NOW,
        canonical_goals=[goal],
        previous_goal_progress=previous,
    )
    assert changed_denominator.goal_progress[0].changed_since_last_review is None
