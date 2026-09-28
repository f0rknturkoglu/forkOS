"""Reproducible descriptive outcomes from canonical rows; no model or tracker."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from statistics import mean, median
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.modules.opportunity.interview_intelligence import revision
from app.modules.opportunity.models import (
    Application,
    ApplicationHistory,
    Interview,
    Opportunity,
    OpportunitySourceObservation,
)


class Conversion(BaseModel):
    numerator: int
    denominator: int
    rate: float | None
    status: str


class Cohort(BaseModel):
    dimension: str
    value: str
    sample_size: int
    counts: dict[str, int]
    interview_conversion: Conversion
    status: str


class SkillGapSignal(BaseModel):
    requirement: str
    opportunities_seen: int
    strong_count: int
    partial_count: int
    missing_count: int
    unknown_count: int
    interview_mentions: int
    explicit_feedback_mentions: int = 0
    role_families: list[str]
    trend: str = "unavailable_no_historical_snapshots"
    confidence: str
    evidence_refs: list[str]


class CareerAnalyticsSnapshot(BaseModel):
    period: dict[str, str]
    generated_at: str
    fingerprint: str
    population: int
    evaluated_population: int
    minimum_sample: int
    funnel: dict[str, int]
    conversions: dict[str, Conversion]
    durations: dict[str, dict[str, float | int | None]]
    cohorts: list[Cohort]
    rejection_patterns: list[dict[str, Any]]
    skill_gaps: list[SkillGapSignal]
    source_performance: list[Cohort]
    geography: list[Cohort]
    lineage: list[dict[str, Any]]
    calibration: list[dict[str, Any]]
    confidence_notes: list[str]
    evidence_refs: list[str]
    briefing: dict[str, str]


def normalize_requirement(value: str) -> str:
    name = " ".join(value.casefold().split())
    return {
        "postgres": "postgresql",
        "postgre sql": "postgresql",
        "k8s": "kubernetes",
        "js": "javascript",
        "ts": "typescript",
    }.get(name, name)


def conversion(numerator: int, denominator: int, minimum: int) -> Conversion:
    status = (
        "incomplete_history"
        if numerator > denominator
        else "insufficient_sample"
        if denominator < minimum
        else "descriptive_association"
    )
    return Conversion(
        numerator=numerator,
        denominator=denominator,
        rate=numerator / denominator if status == "descriptive_association" else None,
        status=status,
    )


def compute_snapshot(
    records: list[dict[str, Any]], *, days: int, minimum: int, now: datetime
) -> CareerAnalyticsSnapshot:
    """Pure reducer: rates use observed stage intersections, never assumed progression."""
    funnel = Counter(
        {
            key: 0
            for key in [
                "discovered",
                "prepared",
                "applied",
                "reply",
                "recruiter_screen",
                "interview",
                "offer",
                "rejected",
                "withdrawn",
            ]
        }
    )
    cohorts: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    durations: dict[str, list[float]] = defaultdict(list)
    gaps: dict[str, dict[str, Any]] = {}
    rejections, lineage, calibration = [], [], []
    stage_sets: dict[str, set[str]] = defaultdict(set)
    for record in records:
        oid = record["id"]
        stages = {h["to_status"] for h in record["history"]} | {
            h["from_status"] for h in record["history"] if h["from_status"]
        }
        if record["status"]:
            stages.add(record["status"])
        if record["applied_at"]:
            stages.add("applied")
        observed = {"discovered"}
        if record["package"]:
            observed.add("prepared")
        observed.update(stages & {"applied", "offer", "rejected", "withdrawn"})
        if record["interviews"]:
            observed.add("interview")
        if "interview" in stages:
            observed.add("interview")
        if any(i["stage"] == "recruiter_screen" for i in record["interviews"]):
            observed.add("recruiter_screen")
        # No persistent reply receipt exists: do not pretend an interview is a reply receipt.
        for stage in observed:
            funnel[stage] += 1
            stage_sets[stage].add(oid)
        record = {**record, "observed": observed}
        for dimension in [
            "role_family",
            "seniority",
            "country",
            "remote",
            "source",
            "company",
            "cv_version",
            "package_version",
            "time_period",
        ]:
            cohorts[dimension, str(record.get(dimension) or "unknown")].append(record)
        timestamps: dict[str, datetime] = {}
        for h in record["history"]:
            if h["at"] and h["to_status"] not in timestamps:
                timestamps[h["to_status"]] = h["at"]
        if record["applied_at"]:
            timestamps.setdefault("applied", record["applied_at"])
        for start, end in [
            ("preparing", "applied"),
            ("applied", "interview"),
            ("applied", "offer"),
            ("applied", "rejected"),
            ("applied", "withdrawn"),
        ]:
            if start in timestamps and end in timestamps and timestamps[end] >= timestamps[start]:
                durations[f"{start}_to_{end}"].append(
                    (timestamps[end] - timestamps[start]).total_seconds() / 86400
                )
        if "rejected" in observed:
            reason = record["rejection_reason"]
            feedback = [
                ((i.get("intelligence") or {}).get("debrief") or {}).get("employer_feedback")
                for i in record["interviews"]
            ]
            quote = next((q for q in feedback if q), None)
            rejections.append(
                {
                    "opportunity_id": oid,
                    "classification": "explicit_reason"
                    if quote
                    else "user_entered_reason"
                    if reason
                    else "unknown",
                    "reason": quote or reason,
                    "source_type": "user_reported_employer_quote"
                    if quote
                    else "user_report"
                    if reason
                    else "unknown",
                    "employer_cause_confirmed": False,
                    "evidence_refs": [
                        f"interview:{i['id']}:debrief:employer_feedback"
                        for i in record["interviews"]
                        if ((i.get("intelligence") or {}).get("debrief") or {}).get(
                            "employer_feedback"
                        )
                    ]
                    if quote
                    else [f"opportunity:{oid}:rejection_reason"]
                    if reason
                    else [],
                }
            )
        evaluation = record["evaluation"]
        if evaluation and not record["evaluation_stale"]:
            assessments = evaluation.get("must_have", []) + evaluation.get("nice_to_have", [])
            per_job: dict[str, dict] = {}
            for item in assessments:
                name = normalize_requirement(item.get("requirement", ""))
                if name:
                    if name in per_job and per_job[name].get("classification") != item.get(
                        "classification"
                    ):
                        per_job[name] = {**item, "classification": "unknown"}
                    else:
                        per_job.setdefault(name, item)
            for name, item in per_job.items():
                cohorts["technology_requirement", name].append(record)
                signal = gaps.setdefault(
                    name,
                    {
                        "count": 0,
                        "classes": Counter(),
                        "mentions": 0,
                        "feedback_mentions": 0,
                        "roles": set(),
                        "refs": [],
                    },
                )
                signal["count"] += 1
                signal["classes"][item.get("classification", "unknown")] += 1
                signal["roles"].add(record["role_family"] or "unknown")
                signal["refs"].append(f"evaluation:{oid}:{revision(evaluation)}")
                for interview in record["interviews"]:
                    report = (interview.get("intelligence") or {}).get("debrief") or {}
                    if any(
                        normalize_requirement(t) == name
                        for t in report.get("topics", []) + report.get("perceived_gaps", [])
                    ):
                        signal["mentions"] += 1
                    if name in normalize_requirement(report.get("employer_feedback") or ""):
                        signal["feedback_mentions"] += 1
        lineage.append(
            {
                "opportunity_id": oid,
                "base_cv_document_id": record["cv_version"],
                "package_revision": record["package_version"],
                "derivative_documents": record["package"].get("generated_documents", []),
                "observed_outcomes": sorted(observed - {"discovered"}),
            }
        )
        calibration.append(
            {
                "opportunity_id": oid,
                "rule_score": record["score"],
                "deep_assessment": evaluation.get("overall_assessment") if evaluation else None,
                "evaluation_stale": record["evaluation_stale"],
                "observed_outcomes": sorted(observed),
                "status": "descriptive_only_no_historical_score_snapshot",
                "weights_changed": False,
            }
        )
    output_cohorts = []
    for (dimension, value), members in sorted(cohorts.items()):
        counts = Counter(stage for member in members for stage in member["observed"])
        applied = {m["id"] for m in members if "applied" in m["observed"]}
        interviewed = {m["id"] for m in members if "interview" in m["observed"]}
        output_cohorts.append(
            Cohort(
                dimension=dimension,
                value=value,
                sample_size=len(members),
                counts=dict(counts),
                interview_conversion=conversion(len(applied & interviewed), len(applied), minimum),
                status="insufficient_sample"
                if len(members) < minimum
                else "descriptive_association",
            )
        )
    skill_gaps = [
        SkillGapSignal(
            requirement=name,
            opportunities_seen=g["count"],
            strong_count=g["classes"]["strong"],
            partial_count=g["classes"]["partial"],
            missing_count=g["classes"]["missing"],
            unknown_count=g["classes"]["unknown"],
            interview_mentions=g["mentions"],
            explicit_feedback_mentions=g["feedback_mentions"],
            role_families=sorted(g["roles"]),
            confidence="insufficient_sample" if g["count"] < minimum else "observed_association",
            evidence_refs=sorted(g["refs"]),
        )
        for name, g in sorted(gaps.items())
    ]
    applied = stage_sets["applied"]
    return CareerAnalyticsSnapshot(
        period={
            "start": (now - timedelta(days=days)).isoformat(),
            "end": now.isoformat(),
            "basis": "opportunity.found_at; cohort outcomes observed as of generation",
        },
        generated_at=now.isoformat(),
        fingerprint=revision({"records": records, "days": days, "minimum": minimum, "end": now}),
        population=len(records),
        evaluated_population=sum(
            bool(r["evaluation"]) and not r["evaluation_stale"] for r in records
        ),
        minimum_sample=minimum,
        funnel=dict(funnel),
        conversions={
            "applied_to_interview": conversion(
                len(applied & stage_sets["interview"]), len(applied), minimum
            ),
            "applied_to_offer": conversion(
                len(applied & stage_sets["offer"]), len(applied), minimum
            ),
            "prepared_to_applied": conversion(
                len(stage_sets["prepared"] & applied), len(stage_sets["prepared"]), minimum
            ),
        },
        durations={
            name: {
                "sample_size": len(values),
                "mean_days": mean(values) if len(values) >= minimum else None,
                "median_days": median(values) if len(values) >= minimum else None,
            }
            for name, values in sorted(durations.items())
        },
        cohorts=output_cohorts,
        rejection_patterns=rejections,
        skill_gaps=skill_gaps,
        source_performance=[c for c in output_cohorts if c.dimension == "source"],
        geography=[c for c in output_cohorts if c.dimension in {"country", "remote"}],
        lineage=lineage,
        calibration=calibration,
        confidence_notes=[
            "Korelasyon neden değildir; puan ağırlıkları değiştirilmedi.",
            "Beceri sıklığı yalnızca güncel değerlendirilmiş ilanlarda ölçülür; tüm keşif havuzuna genellenmez.",
            "Yanıt makbuzu ve yanıt süresi kanonik olarak izlenmiyor: reply=0 gözlem yok demektir, yanıtsızlık değildir.",
            "Eksik geçmişten önceki aşamalar tahmin edilmez; oranlar gözlenen aşamaların kesişimini kullanır.",
            "Eski veya revizyonu doğrulanamayan değerlendirmeler beceri sinyallerine dahil edilmez.",
            "CV ve paket sürümleri mevcut kayıtlardır; başvuru anı tarihçesi yoksa nedensel performans iddiası yapılamaz.",
        ],
        evidence_refs=[f"opportunity:{r['id']}" for r in records],
        briefing={
            "what_changed": "Önceki snapshot olmadığı için değişim hesaplanmadı.",
            "what_is_working": f"{funnel['interview']} görüşme ve {funnel['offer']} teklif gözlemi var.",
            "friction": "Ret nedenleri yalnızca kullanıcı raporu veya bilinmiyor olarak gösterilir.",
            "repeated_gaps": ", ".join(
                g.requirement for g in skill_gaps if g.missing_count >= minimum
            )
            or "Yeterli örnekli tekrarlayan açık yok.",
            "investigate_next": "Eksik aşama tarihlerini ve açık işveren geri bildirimlerini doğrula; otomatik görev oluşturulmadı.",
        },
    )


async def snapshot(
    session: AsyncSession, *, days: int = 30, minimum: int = 3, now: datetime | None = None
) -> CareerAnalyticsSnapshot:
    if not 1 <= days <= 3650 or not 3 <= minimum <= 100:
        raise ValueError("Dönem 1–3650 gün, minimum örnek 3–100 olmalı.")
    now = now or datetime.now(UTC)
    from app.modules.opportunity.candidate_context import build_candidate_career_context
    from app.modules.opportunity.listing_context import build_career_listing_context

    candidate = await build_candidate_career_context(session)
    opportunities = list(
        (
            await session.scalars(
                select(Opportunity)
                .where(
                    Opportunity.kind == "job",
                    Opportunity.trashed_at.is_(None),
                    Opportunity.found_at >= now - timedelta(days=days),
                    Opportunity.found_at <= now,
                )
                .order_by(Opportunity.id)
            )
        ).all()
    )
    ids = [o.id for o in opportunities]
    titles = dict(
        (await session.execute(select(Entity.id, Entity.title).where(Entity.id.in_(ids)))).all()
    )
    apps = {
        a.opportunity_id: a
        for a in (
            await session.scalars(select(Application).where(Application.opportunity_id.in_(ids)))
        ).all()
    }
    history = list(
        (
            await session.scalars(
                select(ApplicationHistory)
                .where(
                    ApplicationHistory.opportunity_id.in_(ids),
                    ApplicationHistory.scope == "application",
                    ApplicationHistory.at <= now,
                )
                .order_by(ApplicationHistory.at, ApplicationHistory.id)
            )
        ).all()
    )
    interviews = list(
        (
            await session.scalars(
                select(Interview).where(Interview.opportunity_id.in_(ids)).order_by(Interview.id)
            )
        ).all()
    )
    observations = list(
        (
            await session.scalars(
                select(OpportunitySourceObservation)
                .where(OpportunitySourceObservation.opportunity_id.in_(ids))
                .order_by(OpportunitySourceObservation.id)
            )
        ).all()
    )
    grouped_history, grouped_interviews, grouped_observations = (
        defaultdict(list),
        defaultdict(list),
        defaultdict(list),
    )
    for item in history:
        grouped_history[item.opportunity_id].append(item)
    for item in interviews:
        grouped_interviews[item.opportunity_id].append(item)
    for item in observations:
        grouped_observations[item.opportunity_id].append(item)
    records = []
    for opp in opportunities:
        app = apps.get(opp.id)
        package = app.package or {} if app else {}
        evaluation = opp.evaluation or {}
        listing = await build_career_listing_context(
            session,
            opp,
            title=titles.get(opp.id) or "",
            source_observations=grouped_observations[opp.id],
        )
        records.append(
            {
                "id": str(opp.id),
                "status": app.status if app else None,
                "applied_at": opp.applied_at,
                "history": [
                    {"from_status": h.from_status, "to_status": h.to_status, "at": h.at}
                    for h in grouped_history[opp.id]
                ],
                "interviews": [
                    {
                        "id": str(i.id),
                        "stage": i.stage,
                        "scheduled_at": i.scheduled_at,
                        "intelligence": i.intelligence,
                    }
                    for i in grouped_interviews[opp.id]
                ],
                "package": package,
                "evaluation": evaluation,
                "evaluation_stale": not listing.is_jd_valid
                or evaluation.get("listing_fingerprint") != listing.listing_fingerprint
                or evaluation.get("candidate_context_revision") != candidate.revision,
                "role_family": opp.category,
                "seniority": None,
                "country": opp.country,
                "remote": opp.remote,
                "source": opp.source,
                "company": opp.organization,
                "score": opp.score,
                "rejection_reason": opp.rejection_reason,
                "cv_version": package.get("base_cv_document_id")
                or (str(app.cv_document_id) if app and app.cv_document_id else None),
                "package_version": revision(package) if package else None,
                "time_period": opp.found_at.strftime("%Y-%m"),
                "source_observations": [
                    {"source": o.source, "status": o.source_status, "last_seen_at": o.last_seen_at}
                    for o in grouped_observations[opp.id]
                ],
            }
        )
    return compute_snapshot(records, days=days, minimum=minimum, now=now)
