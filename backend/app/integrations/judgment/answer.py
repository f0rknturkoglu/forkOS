"""A5.3: H3-first, read-only local answer evidence support judgment orchestration."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.agent.evidence import retrieve_evidence
from app.integrations.agent.evidence_models import EvidenceItem, EvidenceScope
from app.integrations.obsidian.evidence import read_note_lines
from app.integrations.obsidian.security import is_evidence_path
from app.integrations.obsidian.vault import vault_context

from .answer_models import (
    AnswerDegradedReason,
    AnswerJudgeProvenance,
    AnswerJudgeResponse,
)
from .models import (
    MAX_EXCERPT,
    MAX_TOTAL_EXCERPT,
    AnswerEvidenceItem,
    AnswerEvidenceRequest,
    JudgmentMode,
    JudgmentStatus,
    SupportVerdict,
)
from .policy import (
    PurposeModes,
    answer_baseline,
    may_affect_selection,
    may_invoke,
    revalidate_snapshots,
)
from .poorjev_answer import AnswerProviderError, PoorJevAnswerProvider
from .snapshots import bind_evidence_to_snapshots, capture_snapshots


def derive_h3_query(claim: str, explicit_query: str | None = None) -> str:
    """Derive bounded H3 query (2..200 chars); explicit query takes precedence."""
    if explicit_query is not None and explicit_query.strip():
        q = explicit_query.strip()
        if len(q) < 2 or len(q) > 200:
            raise ValueError("explicit retrieval_query must be between 2 and 200 characters")
        return q
    claim = claim.strip()
    if len(claim) <= 200:
        return claim
    truncated = claim[:200]
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return truncated.strip() or claim[:200]


def _extract_surrounding_context(item: EvidenceItem) -> str:
    """Bounded, source-specific deterministic context projection."""
    if item.source_type == "vault":
        parts: list[str] = []
        if item.locator.heading:
            parts.append(f"Heading: {item.locator.heading}")
        if item.locator.relative_path and item.locator.line_start and item.locator.line_end:
            root, _ = vault_context()
            if root and is_evidence_path(item.locator.relative_path):
                lines = read_note_lines(root, item.locator.relative_path)
                if lines:
                    start_idx = max(0, item.locator.line_start - 1 - 3)
                    end_idx = min(len(lines), item.locator.line_end + 3)
                    before_lines = lines[start_idx : max(0, item.locator.line_start - 1)]
                    after_lines = lines[min(len(lines), item.locator.line_end) : end_idx]
                    ctx_lines = []
                    if before_lines:
                        ctx_lines.append("\n".join(before_lines))
                    if after_lines:
                        ctx_lines.append("\n".join(after_lines))
                    if ctx_lines:
                        parts.append("\n".join(ctx_lines))
        return "\n".join(parts)[:MAX_EXCERPT]
    elif item.source_type == "event":
        parts = []
        if item.occurred_at:
            parts.append(f"Occurred: {item.occurred_at}")
        if item.locator.entity_id:
            parts.append(f"Entity: {item.locator.entity_id}")
        if item.retrieval_reason:
            parts.append(f"Reason: {item.retrieval_reason}")
        return " | ".join(parts)[:MAX_EXCERPT]
    elif item.source_type == "entity":
        parts = []
        if item.title:
            parts.append(f"Title: {item.title}")
        if item.updated_at:
            parts.append(f"Updated: {item.updated_at}")
        return " | ".join(parts)[:MAX_EXCERPT]
    return ""


def _baseline(
    claim: str,
    mode: JudgmentMode,
    status: JudgmentStatus,
    reason: AnswerDegradedReason,
    *,
    context_complete: bool = True,
    evidence_count: int = 0,
    truncated: bool = False,
    omitted_total: int = 0,
) -> AnswerJudgeResponse:
    baseline_verdict = answer_baseline(
        evidence_current=(status != "invalid" and reason != "ANSWER_JUDGE_SOURCE_STALE"),
        locator_valid=(status != "invalid"),
        context_complete=context_complete,
    )
    return AnswerJudgeResponse(
        claim=claim[:1000],
        mode=mode,
        status=status,
        baseline_support=baseline_verdict.support,
        observed_support=baseline_verdict.support,
        effective_support=baseline_verdict.support,
        context_complete=context_complete,
        evidence_count=evidence_count,
        truncated=truncated,
        omitted_total=omitted_total,
        verdict=baseline_verdict,
        degraded_reasons=(reason,),
        provenance=None,
    )


async def judge_answer(
    session: AsyncSession,
    *,
    claim: str,
    retrieval_query: str | None = None,
    entity_id: str | None = None,
    scope: EvidenceScope = "all",
    since: str | None = None,
    until: str | None = None,
    max_depth: int = 1,
    limit: int = 12,
    mode: JudgmentMode | None = None,
    provider: Any | None = None,
) -> AnswerJudgeResponse:
    claim_str = (claim or "").strip()
    effective_mode = mode or settings.a5_answer_mode
    if not claim_str or len(claim_str) > 1000:
        return _baseline(claim_str, effective_mode, "invalid", "ANSWER_JUDGE_INVALID_RESPONSE")

    try:
        query = derive_h3_query(claim_str, retrieval_query)
    except ValueError:
        return _baseline(claim_str, effective_mode, "invalid", "ANSWER_JUDGE_INVALID_RESPONSE")

    bundle = await retrieve_evidence(
        session,
        query=query,
        entity_id=entity_id,
        scope=scope,
        since=since,
        until=until,
        max_depth=max_depth,
        limit=limit,
    )

    if not bundle.evidence:
        return _baseline(
            claim_str, effective_mode, "abstained", "ANSWER_JUDGE_EMPTY",
            context_complete=True, evidence_count=0,
        )

    context_complete_val = not bundle.truncated and bundle.omitted_total == 0 and not any(item.truncated for item in bundle.evidence)

    if effective_mode == "off":
        return _baseline(
            claim_str,
            effective_mode,
            "abstained",
            "ANSWER_JUDGE_DISABLED",
            context_complete=context_complete_val,
            evidence_count=len(bundle.evidence),
            truncated=bundle.truncated,
            omitted_total=bundle.omitted_total,
        )

    try:
        before = await capture_snapshots(session, bundle.evidence)
    except Exception:
        return _baseline(
            claim_str,
            effective_mode,
            "invalid",
            "ANSWER_JUDGE_SNAPSHOT_UNAVAILABLE",
            context_complete=context_complete_val,
            evidence_count=len(bundle.evidence),
            truncated=bundle.truncated,
            omitted_total=bundle.omitted_total,
        )

    if not bind_evidence_to_snapshots(bundle.evidence, before):
        return _baseline(
            claim_str,
            effective_mode,
            "invalid",
            "ANSWER_JUDGE_SOURCE_BINDING_FAILED",
            context_complete=context_complete_val,
            evidence_count=len(bundle.evidence),
            truncated=bundle.truncated,
            omitted_total=bundle.omitted_total,
        )

    evidence_items: list[AnswerEvidenceItem] = []
    total_chars = 0
    for position, item in enumerate(bundle.evidence):
        excerpt = item.excerpt[:MAX_EXCERPT]
        surrounding = _extract_surrounding_context(item)[:MAX_EXCERPT]
        item_chars = len(excerpt) + len(surrounding)
        if total_chars + item_chars > MAX_TOTAL_EXCERPT:
            budget_left = MAX_TOTAL_EXCERPT - total_chars - len(excerpt)
            if budget_left > 0:
                surrounding = surrounding[:budget_left]
            else:
                break
        evidence_items.append(
            AnswerEvidenceItem(
                evidence_id=item.evidence_id,
                excerpt=excerpt,
                surrounding_context=surrounding,
                snapshot=before[position],
                remote_allowed=False,
            )
        )
        total_chars += len(excerpt) + len(surrounding)

    if not evidence_items:
        return _baseline(
            claim_str,
            effective_mode,
            "invalid",
            "ANSWER_JUDGE_INVALID_RESPONSE",
            context_complete=context_complete_val,
            evidence_count=len(bundle.evidence),
            truncated=bundle.truncated,
            omitted_total=bundle.omitted_total,
        )

    context_complete = context_complete_val and len(evidence_items) == len(bundle.evidence)

    try:
        request = AnswerEvidenceRequest(
            request_id=str(uuid.uuid4()),
            claim=claim_str,
            evidence=tuple(evidence_items),
            context_complete=context_complete,
        )
    except ValueError:
        return _baseline(
            claim_str,
            effective_mode,
            "invalid",
            "ANSWER_JUDGE_INVALID_RESPONSE",
            context_complete=context_complete,
            evidence_count=len(bundle.evidence),
            truncated=bundle.truncated,
            omitted_total=bundle.omitted_total,
        )

    active_provider = provider or PoorJevAnswerProvider(
        settings.a5_answer_model_path or settings.a5_memory_model_path,
        timeout_seconds=settings.a5_answer_timeout_seconds,
    )
    if active_provider.locality != "local":
        return _baseline(
            claim_str,
            effective_mode,
            "unavailable",
            "ANSWER_JUDGE_UNAVAILABLE",
            context_complete=context_complete,
            evidence_count=len(bundle.evidence),
            truncated=bundle.truncated,
            omitted_total=bundle.omitted_total,
        )

    preflight = may_invoke(
        purpose="answer_evidence",
        modes=PurposeModes(answer_evidence=effective_mode),
        locality=active_provider.locality,
        capabilities=active_provider.capabilities,
        remote_allowed=tuple(item.remote_allowed for item in evidence_items),
        mechanically_eligible=True,
        provider_available=True,
    )
    if not preflight.allowed:
        reason: AnswerDegradedReason = (
            "ANSWER_JUDGE_UNSUPPORTED_CAPABILITY"
            if preflight.reason == "unsupported_capability"
            else "ANSWER_JUDGE_UNAVAILABLE"
        )
        return _baseline(
            claim_str,
            effective_mode,
            preflight.status,
            reason,
            context_complete=context_complete,
            evidence_count=len(bundle.evidence),
            truncated=bundle.truncated,
            omitted_total=bundle.omitted_total,
        )

    ready = await active_provider.health()
    decision = may_invoke(
        purpose="answer_evidence",
        modes=PurposeModes(answer_evidence=effective_mode),
        locality=active_provider.locality,
        capabilities=active_provider.capabilities,
        remote_allowed=tuple(item.remote_allowed for item in evidence_items),
        mechanically_eligible=True,
        provider_available=ready,
    )
    if not decision.allowed:
        reason = (
            "ANSWER_JUDGE_UNSUPPORTED_CAPABILITY"
            if decision.reason == "unsupported_capability"
            else "ANSWER_JUDGE_UNAVAILABLE"
        )
        return _baseline(
            claim_str,
            effective_mode,
            decision.status,
            reason,
            context_complete=context_complete,
            evidence_count=len(bundle.evidence),
            truncated=bundle.truncated,
            omitted_total=bundle.omitted_total,
        )

    provenance: AnswerJudgeProvenance | None = None
    try:
        verdict_res = await active_provider.judge_support(request)
        if isinstance(verdict_res, tuple) and len(verdict_res) == 2:
            verdict, provenance = verdict_res
        elif isinstance(verdict_res, SupportVerdict):
            verdict = verdict_res
        else:
            return _baseline(
                claim_str,
                effective_mode,
                "invalid",
                "ANSWER_JUDGE_INVALID_RESPONSE",
                context_complete=context_complete,
                evidence_count=len(bundle.evidence),
                truncated=bundle.truncated,
                omitted_total=bundle.omitted_total,
            )
        if not isinstance(verdict, SupportVerdict):
            return _baseline(
                claim_str,
                effective_mode,
                "invalid",
                "ANSWER_JUDGE_INVALID_RESPONSE",
                context_complete=context_complete,
                evidence_count=len(bundle.evidence),
                truncated=bundle.truncated,
                omitted_total=bundle.omitted_total,
            )
    except AnswerProviderError as exc:
        reason_map: dict[str, AnswerDegradedReason] = {
            "ANSWER_PROVIDER_TIMEOUT": "ANSWER_JUDGE_TIMEOUT",
            "ANSWER_PROVIDER_BUSY": "ANSWER_JUDGE_BUSY",
            "ANSWER_INVALID_RESPONSE": "ANSWER_JUDGE_INVALID_RESPONSE",
            "ANSWER_MODEL_UNAVAILABLE": "ANSWER_JUDGE_UNAVAILABLE",
            "ANSWER_DEPENDENCY_ABSENT": "ANSWER_JUDGE_UNAVAILABLE",
            "ANSWER_PROVIDER_VERSION_MISMATCH": "ANSWER_JUDGE_UNAVAILABLE",
        }
        deg_reason = reason_map.get(exc.code, "ANSWER_JUDGE_UNAVAILABLE")
        status_val: JudgmentStatus = (
            "unavailable"
            if deg_reason in {"ANSWER_JUDGE_UNAVAILABLE", "ANSWER_JUDGE_TIMEOUT", "ANSWER_JUDGE_BUSY"}
            else "invalid"
        )
        return _baseline(
            claim_str,
            effective_mode,
            status_val,
            deg_reason,
            context_complete=context_complete,
            evidence_count=len(bundle.evidence),
            truncated=bundle.truncated,
            omitted_total=bundle.omitted_total,
        )
    except Exception:
        return _baseline(
            claim_str,
            effective_mode,
            "unavailable",
            "ANSWER_JUDGE_UNAVAILABLE",
            context_complete=context_complete,
            evidence_count=len(bundle.evidence),
            truncated=bundle.truncated,
            omitted_total=bundle.omitted_total,
        )

    # Revalidation of sources after inference
    try:
        after = await capture_snapshots(session, bundle.evidence)
    except Exception:
        return _baseline(
            claim_str,
            effective_mode,
            "stale",
            "ANSWER_JUDGE_SOURCE_STALE",
            context_complete=context_complete,
            evidence_count=len(bundle.evidence),
            truncated=bundle.truncated,
            omitted_total=bundle.omitted_total,
        )

    if revalidate_snapshots(before, after) != "success":
        return _baseline(
            claim_str,
            effective_mode,
            "stale",
            "ANSWER_JUDGE_SOURCE_STALE",
            context_complete=context_complete,
            evidence_count=len(bundle.evidence),
            truncated=bundle.truncated,
            omitted_total=bundle.omitted_total,
        )

    baseline_support = answer_baseline(
        evidence_current=True, locator_valid=True, context_complete=context_complete
    ).support
    effective_support = (
        verdict.support
        if may_affect_selection(mode=effective_mode, status="success", sources_current=True)
        else baseline_support
    )

    return AnswerJudgeResponse(
        claim=claim_str,
        mode=effective_mode,
        status="success",
        baseline_support=baseline_support,
        observed_support=verdict.support,
        effective_support=effective_support,
        context_complete=context_complete,
        evidence_count=len(bundle.evidence),
        truncated=bundle.truncated,
        omitted_total=bundle.omitted_total,
        verdict=verdict,
        degraded_reasons=(),
        provenance=provenance,
    )
