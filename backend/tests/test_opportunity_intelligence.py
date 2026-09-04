from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.modules.opportunity.intelligence import (
    build_evaluation,
    classify_reply,
    detect_archetype,
    extract_requirements,
    parse_compensation,
    quick_signals,
    repost_counts,
    title_identity,
)
from app.modules.opportunity.schemas import EvaluationRequirementOut

pytestmark = pytest.mark.no_database


def _opportunity(**overrides):
    values = {
        "id": uuid.uuid4(),
        "organization": "Acme GmbH",
        "url": "https://jobs.example/one",
        "found_at": datetime.now(UTC),
        "published_at": None,
        "compensation": None,
        "remote": None,
        "country": None,
        "location": None,
        "raw": {},
        "notes": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_compensation_parser_and_transparency_signal():
    assert parse_compensation("€60k - €140k") == (60_000, 140_000, "EUR")
    assert parse_compensation("60.000 TL – 90.000 TL") == (60_000, 90_000, "TRY")

    result = quick_signals(
        _opportunity(compensation="$60k - $140k"),
        title="Backend Engineer",
    )
    assert result.pay_transparency_risk is True
    assert any(signal.code == "wide_pay_range" for signal in result.signals)


def test_repost_requires_same_title_identity_on_different_days_and_urls():
    now = datetime.now(UTC)
    current = _opportunity(found_at=now, url="https://jobs.example/one")
    older = _opportunity(found_at=now - timedelta(days=8), url="https://jobs.example/two")
    other_city = _opportunity(found_at=now - timedelta(days=7), url="https://jobs.example/three")

    counts = repost_counts(
        [(current, "Solutions Engineer Berlin")],
        [
            (current, "Solutions Engineer Berlin"),
            (older, "Berlin Solutions Engineer"),
            (other_city, "Solutions Engineer Munich"),
        ],
    )

    assert title_identity("Solutions Engineer Berlin") == title_identity(
        "Berlin Solutions Engineer"
    )
    assert counts[current.id] == 2


@pytest.mark.parametrize(
    ("text", "kind", "status"),
    [
        (
            "We would like to invite you to an interview. Please share your availability.",
            "interview_invite",
            "interview",
        ),
        (
            "Unfortunately, we are not moving forward with your application.",
            "rejection",
            "rejected",
        ),
        ("Please complete the attached take-home case study.", "take_home_assessment", None),
        (
            "Thank you for applying. Your application received successfully.",
            "auto_acknowledgement",
            "applied",
        ),
    ],
)
def test_reply_classifier(text: str, kind: str, status: str | None):
    result = classify_reply(text)
    assert result.kind == kind
    assert result.suggested_status == status
    assert result.confidence >= 0.58


def test_local_risk_signals_cover_geo_contract_and_sponsorship():
    result = quick_signals(
        _opportunity(
            remote="remote",
            raw={
                "description": (
                    "This is a 1099 role. Three days per week in the office are required. "
                    "Visa sponsorship is not available."
                )
            },
        ),
        title="Remote Platform Engineer",
    )
    assert {signal.code for signal in result.signals} >= {
        "contractor_misclassification",
        "geo_mismatch",
        "no_sponsorship",
    }


def test_pass_one_never_promotes_inferred_requirement_to_high_or_critical():
    requirements = extract_requirements(
        "Platform Engineer",
        "Our internal platform uses Kubernetes for workload orchestration.",
    )
    kubernetes = next(item for item in requirements if item.name == "Kubernetes")
    assert kubernetes.evidence == "inferred"
    assert kubernetes.importance == "low_signal"

    with pytest.raises(ValidationError, match="critical veya high olamaz"):
        EvaluationRequirementOut(
            id="req-invalid",
            name="Varsayılan teknoloji",
            importance="critical",
            evidence="inferred",
        )


def test_two_pass_evaluation_matches_profile_and_enforces_work_auth_gate():
    evaluation = build_evaluation(
        _opportunity(
            country="Germany",
            location="Berlin, Germany",
            remote="remote",
            raw={
                "description": (
                    "C# and .NET are required. Strong experience with Kubernetes is required. "
                    "You will build agentic multi-agent systems with human-in-the-loop controls. "
                    "Candidates must be authorized to work without sponsorship."
                )
            },
        ),
        title="Remote Agentic Software Engineer",
        profile={
            "current_location": "Ankara, Türkiye",
            "authorized_countries": ["Türkiye"],
            "willing_to_relocate": False,
        },
    )

    match_by_name = {item.requirement: item.match for item in evaluation.matches}
    assert match_by_name["C#"] == "strong"
    assert match_by_name["Kubernetes"] in {"partial", "missing"}
    assert evaluation.archetype == "agentic"
    assert evaluation.gate.authorized_to_work is False
    assert evaluation.gate.sponsorship_status == "no_sponsorship"
    assert evaluation.gate.hard_blocker is True
    assert evaluation.recommendation == "skip"
    assert evaluation.score <= 25


def test_two_pass_evaluation_prefers_candidate_document_evidence():
    document_id = uuid.uuid4()
    evaluation = build_evaluation(
        _opportunity(
            raw={
                "description": (
                    "Strong experience with Kubernetes is required. "
                    "Experience with Terraform is preferred."
                )
            }
        ),
        title="Platform Engineer",
        candidate_document_id=document_id,
        candidate_document_title="furkan-cv.txt",
        candidate_text=(
            "Platform engineer. Built and operated Kubernetes clusters and Terraform modules."
        ),
    )

    assert evaluation.candidate_source == "document"
    assert evaluation.candidate_document_id == document_id
    assert evaluation.candidate_document_title == "furkan-cv.txt"
    match_by_name = {item.requirement: item.match for item in evaluation.matches}
    assert match_by_name["Kubernetes"] == "strong"
    assert match_by_name["Terraform"] == "strong"
    assert all(
        "furkan-cv.txt" in item.evidence
        for item in evaluation.matches
        if item.requirement in {"Kubernetes", "Terraform"}
    )


def test_archetype_scoring_keeps_all_six_career_ops_archetypes():
    winner, scores = detect_archetype(
        "Solutions Architect",
        "Own solution architecture, system design and technical architecture decisions.",
    )
    assert winner == "sa"
    assert set(scores) == {"fde", "sa", "pm", "llmops", "agentic", "transformation"}


def test_quick_signals_includes_connection_signal():
    result = quick_signals(
        _opportunity(),
        title="Solutions Engineer",
        connection_count=3,
    )
    assert result.connection_count == 3
    conn_signal = next((s for s in result.signals if s.code == "connection"), None)
    assert conn_signal is not None
    assert conn_signal.severity == "neutral"
    assert "3 yerel LinkedIn bağlantınız var" in conn_signal.detail


def test_build_evaluation_warns_on_short_description():
    evaluation = build_evaluation(
        _opportunity(raw={"description": "Kısa iş tanımı."}),
        title="Yazılım Geliştirici",
    )
    assert evaluation.notes is not None
    assert "İlan metni çok kısa" in evaluation.notes

