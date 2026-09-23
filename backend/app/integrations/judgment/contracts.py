"""Future provider boundary. No implementation or inference in A5.0."""

from __future__ import annotations

from typing import Protocol

from .models import (
    AnswerEvidenceRequest,
    ContextJudgmentRequest,
    ContextVerdict,
    JudgeCapability,
    MemoryRelationRequest,
    MemoryRelationVerdict,
    MemorySupportRequest,
    ProviderLocality,
    SupportVerdict,
)


class JudgmentProvider(Protocol):
    provider_id: str
    locality: ProviderLocality
    capabilities: frozenset[JudgeCapability]

    async def health(self) -> bool: ...

    async def judge_context(self, request: ContextJudgmentRequest) -> tuple[ContextVerdict, ...]: ...

    async def judge_relation(self, request: MemoryRelationRequest) -> MemoryRelationVerdict: ...

    async def judge_support(
        self, request: MemorySupportRequest | AnswerEvidenceRequest
    ) -> SupportVerdict: ...
