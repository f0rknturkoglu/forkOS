"""Bounded, local interview assistance. User reports never become employer facts."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.core.models import Entity
from app.modules.opportunity.candidate_context import build_candidate_career_context
from app.modules.opportunity.evaluation_service import CareerEvaluationService
from app.modules.opportunity.listing_context import build_career_listing_context
from app.modules.opportunity.models import Application, CareerStory, Interview, Opportunity


def revision(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class StoryRecommendation(BaseModel):
    story_id: str
    why_relevant: str
    likely_question_types: list[str]
    evidence_refs: list[str]
    adaptation_notes: str = "Yalnızca doğrulayabildiğin ayrıntıları kullan."


class InterviewPrep(BaseModel):
    interview_id: str
    opportunity_id: str
    listing_fingerprint: str
    evaluation_revision: str
    candidate_context_revision: str
    input_revision: str
    company_summary: str
    role_summary: str
    interview_stage: str | None
    focus_areas: list[str]
    technical_topics: list[str]
    behavioral_topics: list[str]
    likely_questions: list[str]
    story_recommendations: list[StoryRecommendation]
    questions_to_ask: list[str]
    risks: list[str]
    unknowns: list[str]
    evidence_refs: list[str]
    provider: str = "deterministic"
    model: str = "evidence-rules-v1"
    created_at: str
    is_stale: bool = False


class PracticeIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    candidate_answer: str = Field(min_length=1, max_length=8000)


class InterviewPracticeSession(PracticeIn):
    interview_id: str
    stage: str | None
    feedback: dict[str, str]
    strengths: list[str]
    gaps: list[str]
    evidence_refs: list[str]
    created_at: str
    prep_input_revision: str = ""
    candidate_context_revision: str = ""
    provider: str = "deterministic"
    model: str = "review-hints-v1"


BoundedNote = Annotated[str, Field(max_length=2000)]


class StoryProposal(BaseModel):
    situation: BoundedNote
    task: BoundedNote
    action: BoundedNote
    result: BoundedNote


class DebriefIn(BaseModel):
    occurred_at: datetime
    questions_asked: list[BoundedNote] = Field(default_factory=list, max_length=30)
    topics: list[BoundedNote] = Field(default_factory=list, max_length=30)
    candidate_notes: str = Field(default="", max_length=12000)
    perceived_strengths: list[BoundedNote] = Field(default_factory=list, max_length=30)
    perceived_gaps: list[BoundedNote] = Field(default_factory=list, max_length=30)
    follow_up_items: list[BoundedNote] = Field(default_factory=list, max_length=30)
    story_updates: list[str] = Field(default_factory=list, max_length=10)
    outcome_if_known: str | None = Field(default=None, max_length=1000)
    employer_feedback: str | None = Field(default=None, max_length=8000)
    new_story_proposals: list[StoryProposal] = Field(default_factory=list, max_length=5)


class InterviewDebrief(DebriefIn):
    interview_id: str
    skill_signals: list[str]
    source_type: Literal["user_report"] = "user_report"
    interpretation: str = "Öz değerlendirme; işverenin karar nedeni değildir."
    story_update_status: str = "proposal_requires_approval"
    follow_up_status: str = "draft_requires_approval"
    employer_feedback_source: str = "user_reported_quote_not_independently_verified"
    evidence_refs: list[str]
    created_at: str


class InterviewIntelligence(BaseModel):
    prep: InterviewPrep | None = None
    practice: list[InterviewPracticeSession] = Field(default_factory=list)
    debrief: InterviewDebrief | None = None


async def _inputs(session: AsyncSession, row: Interview):
    opp = await session.get(Opportunity, row.opportunity_id)
    if opp is None:
        raise ValueError("Fırsat bulunamadı.")
    listing = await build_career_listing_context(session, opp)
    candidate = await build_candidate_career_context(session)
    evaluation = await CareerEvaluationService().get_evaluation(session, opp.id)
    app = await session.get(Application, opp.id)
    stories = list(
        (
            await session.scalars(
                select(CareerStory)
                .join(Entity, Entity.id == CareerStory.id)
                .where(Entity.archived_at.is_(None))
                .order_by(CareerStory.id)
            )
        ).all()
    )
    previous = list(
        (
            await session.scalars(
                select(Interview)
                .where(Interview.opportunity_id == opp.id, Interview.id != row.id)
                .order_by(Interview.id)
            )
        ).all()
    )
    signature = revision(
        {
            "listing": listing.model_dump(),
            "candidate": candidate.revision,
            "evaluation": evaluation.model_dump(exclude={"is_stale", "stale_reasons"})
            if evaluation
            else None,
            "package": app.package if app else None,
            "company": app.company_research if app else None,
            "stage": row.stage,
            "mode": row.mode,
            "notes": row.notes,
            "stories": [
                {
                    "id": str(s.id),
                    "tags": s.tags,
                    "provenance": s.provenance,
                    "content": [s.situation, s.task, s.action, s.result],
                }
                for s in stories
            ],
            "previous": [
                {
                    "id": str(p.id),
                    "notes": p.notes,
                    "debrief": (p.intelligence or {}).get("debrief"),
                }
                for p in previous
            ],
        }
    )
    return listing, candidate, evaluation, app, stories, signature


async def get_intelligence(session: AsyncSession, interview_id: uuid.UUID) -> InterviewIntelligence:
    row = await session.get(Interview, interview_id)
    if row is None:
        raise ValueError("Görüşme bulunamadı.")
    result = InterviewIntelligence.model_validate(row.intelligence or {})
    if result.prep:
        listing, _, evaluation, _, _, signature = await _inputs(session, row)
        result.prep.is_stale = (
            signature != result.prep.input_revision
            or not listing.is_jd_valid
            or not evaluation
            or evaluation.is_stale
        )
    return result


async def prepare(session: AsyncSession, interview_id: uuid.UUID) -> InterviewPrep:
    row = await session.scalar(
        select(Interview).where(Interview.id == interview_id).with_for_update()
    )
    if row is None:
        raise ValueError("Görüşme bulunamadı.")
    listing, candidate, evaluation, app, stories, signature = await _inputs(session, row)
    if not listing.is_jd_valid or not evaluation or evaluation.is_stale:
        raise ValueError("Geçerli ilan ve güncel derin değerlendirme gerekiyor.")
    if not candidate.base_cv or not candidate.base_cv.get("content_available"):
        raise ValueError("Gerçek CV içeriği gerekiyor.")
    requirements = (evaluation.must_have + evaluation.nice_to_have)[:6]
    focus = [
        r.requirement for r in sorted(requirements, key=lambda r: r.classification == "strong")
    ]
    recommendations = []
    for story in stories:
        if story.provenance not in {"existing", "supported"}:
            continue
        matches = [
            t for t in (story.tags or []) if any(t.casefold() in f.casefold() for f in focus)
        ]
        if matches and story.action and story.result:
            recommendations.append(
                StoryRecommendation(
                    story_id=str(story.id),
                    why_relevant=", ".join(matches),
                    likely_question_types=["behavioral"],
                    evidence_refs=[f"story:{story.id}"],
                )
            )
        if len(recommendations) == 3:
            break
    refs = sorted({ref for r in requirements for ref in r.candidate_evidence_refs})
    result = InterviewPrep(
        interview_id=str(row.id),
        opportunity_id=str(row.opportunity_id),
        listing_fingerprint=listing.listing_fingerprint,
        evaluation_revision=revision(evaluation.model_dump(exclude={"is_stale", "stale_reasons"})),
        candidate_context_revision=candidate.revision,
        input_revision=signature,
        company_summary=app.company_research
        if app and app.company_research
        else "Şirket araştırması yok.",
        role_summary=listing.title,
        interview_stage=None if row.stage in {"", "genel", "unknown"} else row.stage,
        focus_areas=focus,
        technical_topics=[
            topic
            for topic in focus
            if not any(
                term in topic.casefold()
                for term in (
                    "years",
                    "degree",
                    "authorization",
                    "sponsor",
                    "salary",
                    "clearance",
                    "location",
                )
            )
        ],
        behavioral_topics=["Kanıtlanabilir katkı, sonuç ve öğrendiklerin"],
        likely_questions=[
            f"{topic} konusunda doğrulayabildiğin bir örnek anlatır mısın?" for topic in focus
        ],
        story_recommendations=recommendations,
        questions_to_ask=[
            f"İlanda geçen {topic} ekipte nasıl kullanılıyor?" for topic in focus[:3]
        ],
        risks=evaluation.risks,
        unknowns=["Görüşme formatı doğrulanmadı."]
        + ([] if recommendations else ["missing_story_gap"]),
        evidence_refs=refs
        + [f"listing:{listing.jd_hash}"]
        + [f"evaluation:{revision(evaluation.model_dump(exclude={'is_stale', 'stale_reasons'}))}"]
        + (
            [f"application:{row.opportunity_id}:company_research"]
            if app and app.company_research
            else []
        ),
        created_at=datetime.now(UTC).isoformat(),
    )
    if (await _inputs(session, row))[-1] != signature:
        raise ValueError("Hazırlık sırasında kanıt değişti; tekrar dene.")
    row.intelligence = {**(row.intelligence or {}), "prep": result.model_dump(mode="json")}
    await log_event(
        session,
        verb="opportunity.interview_prepared",
        entity_id=row.opportunity_id,
        payload={"interview_id": str(row.id)},
    )
    await session.flush()
    return result


async def practice(
    session: AsyncSession, interview_id: uuid.UUID, body: PracticeIn
) -> InterviewPracticeSession:
    row = await session.scalar(
        select(Interview).where(Interview.id == interview_id).with_for_update()
    )
    if row is None:
        raise ValueError("Görüşme bulunamadı.")
    current = await get_intelligence(session, interview_id)
    if not current.prep or current.prep.is_stale:
        raise ValueError("Önce güncel hazırlık oluştur.")
    if len(current.practice) >= 50:
        raise ValueError("Görüşme başına 50 deneme sınırı doldu.")
    candidate = await build_candidate_career_context(session)
    refs = [
        f.key
        for f in candidate.facts
        if f.verified
        and isinstance(f.value, dict)
        and f.value.get("text")
        and str(f.value["text"]).casefold() in body.candidate_answer.casefold()
    ]
    answer = body.candidate_answer.casefold()
    star = all(
        any(word in answer for word in group)
        for group in [
            ("durum", "situation"),
            ("görev", "task"),
            ("yapt", "action"),
            ("sonuç", "result"),
        ]
    )
    result = InterviewPracticeSession(
        **body.model_dump(),
        interview_id=str(row.id),
        stage=current.prep.interview_stage,
        feedback={
            "clarity": "needs_review",
            "specificity": "details_present" if len(answer.split()) >= 30 else "add_details",
            "evidence_use": "source_text_present" if refs else "unverified",
            "technical_correctness": "needs_review",
            "star_structure": "markers_present" if star else "add_context_action_result",
        },
        strengths=["Kaynak metni içeriyor."] if refs else [],
        gaps=[
            "unsupported_claim: Kaynağa bağlı olmayan aday iddiaları kullanıcı incelemesi gerektiriyor."
        ],
        evidence_refs=refs,
        created_at=datetime.now(UTC).isoformat(),
        prep_input_revision=current.prep.input_revision,
        candidate_context_revision=candidate.revision,
    )
    row.intelligence = {
        **(row.intelligence or {}),
        "practice": [p.model_dump(mode="json") for p in current.practice]
        + [result.model_dump(mode="json")],
    }
    await log_event(
        session,
        verb="opportunity.interview_practiced",
        entity_id=row.opportunity_id,
        payload={"interview_id": str(row.id)},
    )
    await session.flush()
    return result


async def debrief(
    session: AsyncSession, interview_id: uuid.UUID, body: DebriefIn
) -> InterviewDebrief:
    row = await session.scalar(
        select(Interview).where(Interview.id == interview_id).with_for_update()
    )
    if row is None:
        raise ValueError("Görüşme bulunamadı.")
    if body.occurred_at.tzinfo is None or body.occurred_at > datetime.now(UTC):
        raise ValueError("Gerçekleşme zamanı saat dilimi içermeli ve gelecekte olmamalı.")
    for story_id in body.story_updates:
        try:
            story = await session.get(CareerStory, uuid.UUID(story_id))
        except ValueError:
            story = None
        if story is None:
            raise ValueError("Hikâye önerisi mevcut bir hikâyeyi referanslamalı.")
    result = InterviewDebrief(
        **body.model_dump(),
        interview_id=str(row.id),
        skill_signals=body.perceived_gaps,
        evidence_refs=[f"user_report:interview:{row.id}"],
        created_at=datetime.now(UTC).isoformat(),
    )
    row.intelligence = {**(row.intelligence or {}), "debrief": result.model_dump(mode="json")}
    await log_event(
        session,
        verb="opportunity.interview_debriefed",
        entity_id=row.opportunity_id,
        payload={"interview_id": str(row.id)},
    )
    await session.flush()
    return result
