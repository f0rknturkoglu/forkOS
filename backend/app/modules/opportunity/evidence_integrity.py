"""Deterministic fail-closed validation of candidate evidence references."""

from app.modules.opportunity.candidate_context import CandidateCareerContext
from app.modules.opportunity.reasoner.base import DeepEvaluationDraft


def claim_matches_fact(claim, fact) -> bool:
    if fact is None or not fact.verified:
        return False
    value = fact.value.get("text", "") if isinstance(fact.value, dict) else str(fact.value)
    supported = {value.strip().casefold()}
    if fact.key.startswith("skill:"):
        supported.add(f"technical proficiency in {value}".casefold())
    return claim.strip().casefold() in supported


def valid_refs(refs: list[str], context: CandidateCareerContext) -> bool:
    canonical = {f.key for f in context.facts if f.verified}
    return bool(refs) and all(ref in canonical for ref in refs)


def validate_evaluation(draft: DeepEvaluationDraft, context: CandidateCareerContext) -> None:
    for item in [*draft.must_have, *draft.nice_to_have]:
        if item.candidate_evidence_refs and not valid_refs(item.candidate_evidence_refs, context):
            item.candidate_evidence_refs = []
            item.classification = "unknown"
            item.reason = "Candidate evidence reference failed integrity validation."
            item.confidence = 0
        elif item.classification in ("strong", "partial") and not valid_refs(
            item.candidate_evidence_refs, context
        ):
            item.classification = "unknown"
            item.reason = "No verified canonical candidate evidence."
            item.confidence = 0
    # Free-form candidate assertions cannot be deterministically certified. Replace
    # strengths with canonical values; keep interpretation out of evidence fields.
    refs = list(
        dict.fromkeys(
            ref
            for item in [*draft.must_have, *draft.nice_to_have]
            for ref in item.candidate_evidence_refs
        )
    )
    draft.evidence = refs
    draft.strengths = [
        str(context.get_fact(ref).value)
        for ref in refs
        if context.get_fact(ref) and ref.startswith("skill:")
    ]
    for field in ("work_authorization", "sponsorship", "compensation"):
        setattr(
            draft,
            field,
            {
                "status": "unknown",
                "warning": "Candidate claim requires explicit verified evidence.",
            },
        )
