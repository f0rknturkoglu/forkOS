"""A5.2 Memory Judge: A4-gated, read-only semantic advice, never a write path."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.secret_safety import contains_high_confidence_secret
from app.integrations.agent.evidence_revision import projection_digest
from app.integrations.obsidian import semantic_memory as sem_storage
from app.modules.semantic_memory.models import AgentSemanticCandidate
from app.modules.semantic_memory.policy import is_privacy_blocked, normalize_statement

from .memory_models import MemoryJudgeProvenance, MemoryJudgeResponse, MemorySignals
from .memory_sources import MemorySource, read_memory_source
from .poorjev_memory import MemoryJudgePacket, MemoryProviderError, PoorJevMemoryProvider

MAX_SOURCES = 3
MAX_RELATED = 3
MAX_SOURCE_CHARS = 500
MAX_CARD_CHARS = 500
MAX_PACKET_CHARS = 6000
MEMORY_POLICY_VERSION = "a5-memory-policy-v1"


class MemoryProvider(Protocol):
    async def judge(
        self, packet: MemoryJudgePacket
    ) -> tuple[MemorySignals, MemoryJudgeProvenance]: ...


@dataclass(frozen=True)
class BoundState:
    candidate_digest: str
    source_digest: str
    related_digest: str
    policy_digest: str
    sources: tuple[MemorySource, ...]
    related: tuple[sem_storage.SemanticMemoryCard, ...]
    exact_duplicate: bool

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return (
            self.candidate_digest,
            self.source_digest,
            self.related_digest,
            self.policy_digest,
        )


_provider: PoorJevMemoryProvider | None = None


def _policy_digest(mode: str) -> str:
    return projection_digest(
        (
            MEMORY_POLICY_VERSION,
            MAX_SOURCES,
            MAX_RELATED,
            MAX_SOURCE_CHARS,
            MAX_CARD_CHARS,
            MAX_PACKET_CHARS,
            mode,
            settings.a5_memory_provider,
        )
    )


def _candidate_digest(candidate: AgentSemanticCandidate) -> str:
    return projection_digest(
        {column.name: getattr(candidate, column.name) for column in candidate.__table__.columns}
    )


def _related_cards(candidate: AgentSemanticCandidate) -> tuple[tuple[sem_storage.SemanticMemoryCard, ...], str, bool] | None:
    root = sem_storage.readable_root()
    if root is None:
        return None
    cards = sem_storage.scan_semantic_cards(root)
    relevant = [
        card
        for card in cards
        if card.kind == candidate.kind
        and card.scope == candidate.scope
        and card.scope_project == candidate.scope_project
        and card.subject_key == candidate.subject_key
    ]
    identity = projection_digest(
        sorted((card.card_id, card.revision, card.effective_status) for card in relevant)
    )
    active = sorted(
        (card for card in relevant if card.effective_status == "active"),
        key=lambda card: (card.updated_at, card.card_id),
        reverse=True,
    )
    duplicate = any(
        normalize_statement(card.statement) == normalize_statement(candidate.statement)
        for card in active
    )
    return tuple(active[:MAX_RELATED]), identity, duplicate


async def _bound_state(
    session: AsyncSession, candidate_id: uuid.UUID, mode: str
) -> tuple[AgentSemanticCandidate | None, BoundState | None, str | None]:
    session.expire_all()
    candidate = await session.get(AgentSemanticCandidate, candidate_id, populate_existing=True)
    if candidate is None:
        return None, None, "CANDIDATE_NOT_FOUND"
    if candidate.status not in ("proposed", "needs_review", "ready"):
        return candidate, None, "CANDIDATE_INELIGIBLE"
    if (
        candidate.sensitivity != "normal"
        or is_privacy_blocked(candidate.statement)
        or contains_high_confidence_secret(
            candidate.statement, *(candidate.conditions or []), *(candidate.exceptions or [])
        )
    ):
        return candidate, None, "SENSITIVITY_BLOCKED"
    refs = candidate.evidence_refs or []
    if not 1 <= len(refs) <= MAX_SOURCES:
        return candidate, None, "SOURCE_LIMIT_OR_MISSING"
    sources: list[MemorySource] = []
    for entry in refs:
        if not isinstance(entry, dict):
            return candidate, None, "SOURCE_INVALID"
        ref = entry.get("ref")
        expected = entry.get("source_revision")
        if not isinstance(ref, str) or not isinstance(expected, str) or len(expected) != 64:
            return candidate, None, "SOURCE_UNBOUND"
        source = await read_memory_source(session, ref)
        if source is None or source.revision != expected:
            return candidate, None, "SOURCE_STALE"
        if (
            len(source.text) > MAX_SOURCE_CHARS
            or is_privacy_blocked(source.text)
            or contains_high_confidence_secret(source.text)
            or entry.get("role") != source.role
            or entry.get("digest") != source.evidence_digest
        ):
            return candidate, None, "SOURCE_INVALID"
        sources.append(source)
    if len({source.ref for source in sources}) != len(sources):
        return candidate, None, "SOURCE_INVALID"
    related_state = _related_cards(candidate)
    if related_state is None:
        return candidate, None, "RELATED_UNAVAILABLE"
    related, related_digest, exact_duplicate = related_state
    if any(
        card.sensitivity != "normal"
        or len(card.statement) > MAX_CARD_CHARS
        or contains_high_confidence_secret(card.statement)
        for card in related
    ):
        return candidate, None, "RELATED_SENSITIVITY_BLOCKED"
    total_chars = len(candidate.statement) + sum(len(source.text) for source in sources) + sum(
        len(card.statement) for card in related
    )
    if total_chars > MAX_PACKET_CHARS:
        return candidate, None, "PACKET_LIMIT"
    return candidate, BoundState(
        candidate_digest=_candidate_digest(candidate),
        source_digest=projection_digest([(source.ref, source.revision) for source in sources]),
        related_digest=related_digest,
        policy_digest=_policy_digest(mode),
        sources=tuple(sources),
        related=related,
        exact_duplicate=exact_duplicate,
    ), None


def _review_flags(signals: MemorySignals) -> tuple[str, ...]:
    flags = []
    if signals.evidence_support in ("unsupported", "partially_supported"):
        flags.append("EVIDENCE_REVIEW")
    if signals.intent in ("tentative", "uncertain"):
        flags.append("INTENT_REVIEW")
    if signals.scope_relation in ("broader_scope", "different_scope"):
        flags.append("SCOPE_REVIEW")
    if signals.conditions_preserved == "no" or signals.exceptions_preserved == "no":
        flags.append("QUALIFIER_REVIEW")
    if any(item.relation in ("incompatible", "changed_decision", "duplicate") for item in signals.relations):
        flags.append("RELATION_REVIEW")
    return tuple(flags)


async def judge_memory(
    session: AsyncSession,
    candidate_id: uuid.UUID,
    *,
    provider: MemoryProvider | None = None,
    mode: str | None = None,
) -> MemoryJudgeResponse:
    """Read-only path. All modes leave the A4 candidate and cards untouched."""
    effective_mode = mode or settings.a5_memory_mode
    candidate = await session.get(AgentSemanticCandidate, candidate_id, populate_existing=True)
    if candidate is None:
        raise ValueError("CANDIDATE_NOT_FOUND")
    baseline_status = candidate.status
    baseline_destination = candidate.suggested_destination

    def baseline(status: str, reason: str) -> MemoryJudgeResponse:
        return MemoryJudgeResponse(
            candidate_id=candidate_id,
            mode=effective_mode,
            status=status,
            baseline_status=baseline_status,
            baseline_destination=baseline_destination,
            reason=reason,
        )

    if effective_mode == "off":
        return baseline("disabled", "MEMORY_JUDGE_DISABLED")
    try:
        current, before, reason = await _bound_state(session, candidate_id, effective_mode)
        if current is None or before is None:
            return baseline("degraded", reason or "SOURCE_UNAVAILABLE")
        statement = current.statement
        kind = current.kind
        scope = current.scope
        scope_project = current.scope_project
        conditions = tuple(current.conditions or [])
        exceptions = tuple(current.exceptions or [])
        # The A4 exact-identity gate runs before local inference.
        if before.exact_duplicate:
            return baseline("abstained", "EXACT_DUPLICATE")
        # First-bound candidate/source/card/policy state is re-read immediately
        # before inference to detect a mutation during packet assembly.
        _, confirmed, reason = await _bound_state(session, candidate_id, effective_mode)
        if confirmed is None or confirmed.identity != before.identity:
            return baseline("stale", reason or "FIRST_SNAPSHOT_MISMATCH")
        packet = MemoryJudgePacket(
            statement=statement,
            kind=kind,
            scope=scope,
            scope_project=scope_project,
            conditions=conditions,
            exceptions=exceptions,
            source_texts=tuple(source.text for source in before.sources),
            related=tuple((card.card_id, card.statement) for card in before.related),
            candidate_snapshot=before.candidate_digest,
            source_snapshot=before.source_digest,
            related_snapshot=before.related_digest,
            policy_snapshot=before.policy_digest,
        )
        global _provider
        active = provider
        if active is None:
            if settings.a5_memory_provider != "poorjev":
                return baseline("unavailable", "MEMORY_PROVIDER_UNAVAILABLE")
            if _provider is None or str(_provider.model_path) != settings.a5_memory_model_path:
                _provider = PoorJevMemoryProvider(
                    settings.a5_memory_model_path,
                    timeout_seconds=settings.a5_memory_timeout_seconds,
                )
            active = _provider
        signals, provenance = await active.judge(packet)
        _, after, reason = await _bound_state(session, candidate_id, effective_mode)
        if after is None or after.identity != before.identity:
            return baseline("stale", reason or "SOURCE_OR_POLICY_STALE")
        if (
            not isinstance(signals, MemorySignals)
            or provenance.candidate_snapshot != before.candidate_digest
            or provenance.source_snapshot != before.source_digest
            or provenance.related_snapshot != before.related_digest
            or provenance.policy_snapshot != before.policy_digest
            or tuple(item.card_id for item in signals.relations)
            != tuple(card.card_id for card in before.related)
        ):
            return baseline("invalid", "MEMORY_PROVIDER_RESPONSE_MISMATCH")
        if provenance.abstained:
            return baseline("abstained", "PROVIDER_ABSTAINED")
        return MemoryJudgeResponse(
            candidate_id=candidate_id,
            mode=effective_mode,
            status="success",
            baseline_status=baseline_status,
            baseline_destination=baseline_destination,
            signals=signals,
            review_flags=_review_flags(signals) if effective_mode in ("assist", "on") else (),
            provenance=provenance,
        )
    except MemoryProviderError as exc:
        return baseline("unavailable", exc.code)
    except Exception:
        return baseline("invalid", "MEMORY_JUDGE_INVALID")
