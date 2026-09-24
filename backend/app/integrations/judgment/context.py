"""A5.1: H3-first, rerank-only local context judgment orchestration."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.agent.evidence import retrieve_evidence
from app.integrations.agent.evidence_models import EvidenceBundle, EvidenceScope

from .contracts import JudgmentProvider
from .jevmlx import ContextProviderError, JevMlxProvider
from .models import (
    ContextCandidate,
    ContextJudgmentRequest,
    ContextVerdict,
    JudgmentMode,
    JudgmentStatus,
)
from .policy import (
    PurposeModes,
    context_verdicts_valid,
    may_affect_selection,
    may_invoke,
    revalidate_snapshots,
)
from .snapshots import capture_snapshots

DegradedReason = Literal[
    "CONTEXT_JUDGE_DISABLED", "CONTEXT_JUDGE_EMPTY", "CONTEXT_JUDGE_UNAVAILABLE",
    "CONTEXT_JUDGE_TIMEOUT", "CONTEXT_JUDGE_BUSY", "CONTEXT_JUDGE_INVALID_RESPONSE",
    "CONTEXT_JUDGE_INVALID_ENDPOINT", "CONTEXT_JUDGE_SOURCE_STALE",
    "CONTEXT_JUDGE_SNAPSHOT_UNAVAILABLE", "CONTEXT_JUDGE_UNSUPPORTED_CAPABILITY",
]

USEFULNESS_PRIORITY = {"essential": 0, "useful": 1, "weak": 2, "uncertain": 3, "irrelevant": 4}
REDUNDANCY_PRIORITY = {"unique": 0, "uncertain": 1, "redundant": 2}


class ContextJudgeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: JudgmentMode
    status: JudgmentStatus
    bundle: EvidenceBundle
    baseline_order: tuple[str, ...] = Field(max_length=15)
    advisory_order: tuple[str, ...] = Field(max_length=15)
    effective_order: tuple[str, ...] = Field(max_length=15)
    verdicts: tuple[ContextVerdict, ...] = Field(max_length=15)
    degraded_reasons: tuple[DegradedReason, ...] = Field(default_factory=tuple, max_length=3)


def semantic_order(bundle: EvidenceBundle, verdicts: tuple[ContextVerdict, ...]) -> tuple[str, ...]:
    positions = {item.evidence_id: position for position, item in enumerate(bundle.evidence)}
    if len(verdicts) != len(positions) or {v.evidence_id for v in verdicts} != set(positions):
        raise ValueError("incomplete context verdict coverage")
    return tuple(v.evidence_id for v in sorted(
        verdicts,
        key=lambda v: (
            USEFULNESS_PRIORITY[v.usefulness], REDUNDANCY_PRIORITY[v.redundancy],
            positions[v.evidence_id],
        ),
    ))


def _uncertain(bundle: EvidenceBundle, status: JudgmentStatus) -> tuple[ContextVerdict, ...]:
    return tuple(ContextVerdict(
        evidence_id=item.evidence_id, status=status,
        usefulness="uncertain", redundancy="uncertain",
    ) for item in bundle.evidence)


def _baseline(bundle: EvidenceBundle, mode: JudgmentMode, status: JudgmentStatus, reason: DegradedReason) -> ContextJudgeResponse:
    order = tuple(item.evidence_id for item in bundle.evidence)
    return ContextJudgeResponse(
        mode=mode, status=status, bundle=bundle,
        baseline_order=order, advisory_order=order, effective_order=order,
        verdicts=_uncertain(bundle, status), degraded_reasons=(reason,),
    )


async def judge_context(
    session: AsyncSession,
    *,
    query: str,
    entity_id: str | None = None,
    scope: EvidenceScope = "all",
    since: str | None = None,
    until: str | None = None,
    max_depth: int = 1,
    limit: int = 12,
    mode: JudgmentMode | None = None,
    provider: JudgmentProvider | None = None,
) -> ContextJudgeResponse:
    bundle = await retrieve_evidence(
        session, query=query, entity_id=entity_id, scope=scope, since=since, until=until,
        max_depth=max_depth, limit=limit,
    )
    effective_mode = mode or settings.a5_context_mode
    baseline = tuple(item.evidence_id for item in bundle.evidence)
    if not bundle.evidence:
        return _baseline(bundle, effective_mode, "abstained", "CONTEXT_JUDGE_EMPTY")
    if effective_mode == "off":
        return _baseline(bundle, effective_mode, "abstained", "CONTEXT_JUDGE_DISABLED")

    try:
        before = await capture_snapshots(session, bundle.evidence)
    except Exception:
        # Snapshot reads are optional to H3; any failure forbids model use.
        return _baseline(bundle, effective_mode, "invalid", "CONTEXT_JUDGE_SNAPSHOT_UNAVAILABLE")
    try:
        candidates = tuple(ContextCandidate(
            evidence_id=item.evidence_id, source_type=item.source_type, title=item.title,
            excerpt=item.excerpt, retrieval_position=position, snapshot=before[position],
        ) for position, item in enumerate(bundle.evidence))
        request = ContextJudgmentRequest(
            request_id=str(uuid.uuid4()), query=bundle.query, candidates=candidates,
            truncated=bundle.truncated, omitted_total=bundle.omitted_total,
        )
    except ValueError:
        return _baseline(bundle, effective_mode, "invalid", "CONTEXT_JUDGE_INVALID_RESPONSE")
    try:
        active_provider = provider or JevMlxProvider(
            settings.a5_jevmlx_base_url, timeout_seconds=settings.a5_context_timeout_seconds,
        )
        if active_provider.locality != "local":
            return _baseline(bundle, effective_mode, "unavailable", "CONTEXT_JUDGE_UNAVAILABLE")
        preflight = may_invoke(
            purpose="context", modes=PurposeModes(context=effective_mode),
            locality=active_provider.locality, capabilities=active_provider.capabilities,
            remote_allowed=tuple(candidate.remote_allowed for candidate in candidates),
            mechanically_eligible=True, provider_available=True,
        )
        if not preflight.allowed:
            reason: DegradedReason = (
                "CONTEXT_JUDGE_UNSUPPORTED_CAPABILITY" if preflight.reason == "unsupported_capability"
                else "CONTEXT_JUDGE_UNAVAILABLE"
            )
            return _baseline(bundle, effective_mode, preflight.status, reason)
        ready = await active_provider.health()
        decision = may_invoke(
            purpose="context", modes=PurposeModes(context=effective_mode),
            locality=active_provider.locality, capabilities=active_provider.capabilities,
            remote_allowed=tuple(candidate.remote_allowed for candidate in candidates),
            mechanically_eligible=True, provider_available=ready,
        )
        if not decision.allowed:
            reason: DegradedReason = (
                "CONTEXT_JUDGE_UNSUPPORTED_CAPABILITY" if decision.reason == "unsupported_capability"
                else "CONTEXT_JUDGE_UNAVAILABLE"
            )
            return _baseline(bundle, effective_mode, decision.status, reason)
        verdicts = await active_provider.judge_context(request)
        if not context_verdicts_valid(request, verdicts) or any(v.status != "success" for v in verdicts):
            return _baseline(bundle, effective_mode, "invalid", "CONTEXT_JUDGE_INVALID_RESPONSE")
    except ContextProviderError as exc:
        reason: DegradedReason = exc.code if exc.code in {
            "CONTEXT_JUDGE_UNAVAILABLE", "CONTEXT_JUDGE_TIMEOUT", "CONTEXT_JUDGE_BUSY",
            "CONTEXT_JUDGE_INVALID_RESPONSE", "CONTEXT_JUDGE_INVALID_ENDPOINT",
            "CONTEXT_JUDGE_UNSUPPORTED_CAPABILITY",
        } else "CONTEXT_JUDGE_UNAVAILABLE"
        status: JudgmentStatus = "unavailable" if reason in {
            "CONTEXT_JUDGE_UNAVAILABLE", "CONTEXT_JUDGE_TIMEOUT", "CONTEXT_JUDGE_BUSY"
        } else "invalid"
        return _baseline(bundle, effective_mode, status, reason)
    except Exception:
        # Optional semantic judgment must never make a successful H3 retrieval fail.
        return _baseline(bundle, effective_mode, "unavailable", "CONTEXT_JUDGE_UNAVAILABLE")

    try:
        after = await capture_snapshots(session, bundle.evidence)
    except Exception:
        return _baseline(bundle, effective_mode, "stale", "CONTEXT_JUDGE_SOURCE_STALE")
    if revalidate_snapshots(before, after) != "success":
        return _baseline(bundle, effective_mode, "stale", "CONTEXT_JUDGE_SOURCE_STALE")
    try:
        advisory = semantic_order(bundle, verdicts)
    except (KeyError, ValueError):
        return _baseline(bundle, effective_mode, "invalid", "CONTEXT_JUDGE_INVALID_RESPONSE")
    effective = advisory if may_affect_selection(mode=effective_mode, status="success", sources_current=True) else baseline
    return ContextJudgeResponse(
        mode=effective_mode, status="success", bundle=bundle,
        baseline_order=baseline, advisory_order=advisory, effective_order=effective,
        verdicts=verdicts,
    )
