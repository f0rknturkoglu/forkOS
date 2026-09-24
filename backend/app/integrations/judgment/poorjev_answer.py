"""Optional local poorjev adapter for A5.3 Answer Evidence Judge.

Offline, zero-shot NLI using DeBERTa-v3-base-zeroshot-v2.0 via poorjev.
No ML import or network call at startup.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from app.integrations.agent.evidence_revision import projection_digest

from .answer_models import AnswerJudgeProvenance
from .models import (
    AnswerEvidenceRequest,
    EvidenceSupport,
    JudgmentMetadata,
    SupportVerdict,
)

PROVIDER_ID = "poorjev-local-nli"
PROVIDER_VERSION = "0.1.0"
MODEL_ID = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"
MODEL_REVISION = "8e7e5af5983a0ddb1a5b45a38b129ab69e2258e8"
QUESTION_VERSION = "a5-answer-questions-v1"
MODEL_MANIFEST = "forkos-poorjev-model.json"

LABELS: tuple[EvidenceSupport, ...] = (
    "supported",
    "contradicted",
    "insufficient",
    "uncertain",
)

HYPOTHESES: dict[EvidenceSupport, str] = {
    "supported": "The provided evidence directly supports this claim: {claim}",
    "contradicted": "The provided evidence directly contradicts this claim: {claim}",
    "insufficient": "The provided evidence is insufficient to verify or refute this claim: {claim}",
    "uncertain": "It is uncertain or ambiguous whether the provided evidence supports this claim: {claim}",
}
QUESTION_HASH = projection_digest(HYPOTHESES)


class AnswerProviderError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _premise(request: AnswerEvidenceRequest) -> str:
    lines = []
    for i, item in enumerate(request.evidence):
        meta_parts = [f"Source {i + 1} ({item.snapshot.source_type})"]
        if item.snapshot.source_version:
            meta_parts.append(f"version: {item.snapshot.source_version}")
        header = " - ".join(meta_parts)
        text = item.excerpt
        if item.surrounding_context:
            text = f"{text}\nContext: {item.surrounding_context}"
        lines.append(f"{header}:\n{text}")
    if not request.context_complete:
        lines.append("[Notice: The retrieved evidence is truncated or context is incomplete.]")
    return "\n\n".join(lines)


class PoorJevAnswerProvider:
    """One local NLI model for Answer Evidence, lazy and serialized; failure never switches provider."""

    provider_id = PROVIDER_ID
    locality = "local"
    capabilities = frozenset({"answer_support"})

    def __init__(self, model_path: str, *, timeout_seconds: float = 20.0) -> None:
        self.model_path = Path(model_path).expanduser()
        self.timeout_seconds = min(max(float(timeout_seconds), 0.1), 60.0)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="poorjev-answer")
        self._lock = asyncio.Lock()
        self._pending: asyncio.Future | None = None
        self._client = None
        self._manifest: dict[str, str] | None = None

    def _read_manifest(self) -> dict[str, str]:
        try:
            path = self.model_path.resolve(strict=True)
            if not path.is_dir() or not (path / "config.json").is_file():
                raise ValueError
            manifest_path = path / MODEL_MANIFEST
            if manifest_path.stat().st_size > 4096:
                raise ValueError
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            if data.get("model_id") != MODEL_ID or data.get("revision") != MODEL_REVISION:
                raise ValueError
            return {"model_id": MODEL_ID, "revision": MODEL_REVISION}
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise AnswerProviderError("ANSWER_MODEL_UNAVAILABLE") from exc

    def _ask(self, request: AnswerEvidenceRequest):
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        try:
            from poorjev import Choice
            from poorjev.backends.local_nli import LocalNLIBackend
        except ImportError as exc:
            raise AnswerProviderError("ANSWER_DEPENDENCY_ABSENT") from exc
        try:
            if version("poorjev") != PROVIDER_VERSION:
                raise AnswerProviderError("ANSWER_PROVIDER_VERSION_MISMATCH")
        except PackageNotFoundError as exc:
            raise AnswerProviderError("ANSWER_DEPENDENCY_ABSENT") from exc

        if self._client is None:
            self._client = LocalNLIBackend(model_name=str(self.model_path.resolve(strict=True)))

        premise = _premise(request)
        hypotheses = [HYPOTHESES[label].format(claim=request.claim) for label in LABELS]
        pairs = [(premise, hypothesis) for hypothesis in hypotheses]
        probabilities = self._client.entail_probs(pairs)
        if len(probabilities) != len(pairs):
            raise AnswerProviderError("ANSWER_INVALID_RESPONSE")

        decision = Choice(hypotheses).decide(probabilities, kind="probs")
        return decision, probabilities

    async def health(self) -> bool:
        try:
            self._read_manifest()
            return True
        except AnswerProviderError:
            return False

    async def judge_support(
        self, request: AnswerEvidenceRequest
    ) -> tuple[SupportVerdict, AnswerJudgeProvenance]:
        manifest = self._read_manifest()
        async with self._lock:
            if self._pending is not None and not self._pending.done():
                raise AnswerProviderError("ANSWER_PROVIDER_BUSY")
            started = time.perf_counter()
            loop = asyncio.get_running_loop()
            self._pending = loop.run_in_executor(self._executor, self._ask, request)
            try:
                answer, probabilities = await asyncio.wait_for(
                    asyncio.shield(self._pending), self.timeout_seconds
                )
            except TimeoutError as exc:
                raise AnswerProviderError("ANSWER_PROVIDER_TIMEOUT") from exc
            except AnswerProviderError:
                raise
            except Exception as exc:
                raise AnswerProviderError("ANSWER_PROVIDER_UNAVAILABLE") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)

        inverse = {
            HYPOTHESES[label].format(claim=request.claim): label for label in LABELS
        }
        selected_text = getattr(answer, "value", None)
        value = inverse.get(selected_text)
        confidence = getattr(answer, "confidence", None)
        abstained = bool(getattr(answer, "abstained", False))

        if (
            value is None
            or not isinstance(confidence, (int, float))
            or not math.isfinite(confidence)
            or not (0 <= confidence <= 1)
        ):
            raise AnswerProviderError("ANSWER_INVALID_RESPONSE")

        field_confidences = {
            label: float(prob)
            for label, prob in zip(LABELS, probabilities, strict=True)
            if math.isfinite(prob) and 0 <= prob <= 1
        }

        # Guard against false certainty when context is incomplete:
        final_support: EvidenceSupport = value
        reason_codes: tuple[str, ...] = ()
        if not request.context_complete and final_support in {"supported", "contradicted"}:
            final_support = "uncertain"
            reason_codes = ("context_incomplete",)

        verdict_status = "abstained" if abstained else "success"
        if verdict_status != "success":
            final_support = "uncertain"
            if not reason_codes:
                reason_codes = ("low_provider_margin",)

        metadata = JudgmentMetadata(
            provider_id=PROVIDER_ID,
            model_id=manifest["model_id"],
            latency_ms=latency_ms,
            provider_confidence=float(confidence),
            probability_margin=None,
            calibrated=False,
        )

        verdict = SupportVerdict(
            status=verdict_status,
            support=final_support,
            reason_codes=reason_codes,
            metadata=metadata,
        )

        claim_digest = hashlib.sha256(request.claim.encode("utf-8")).hexdigest()
        evidence_digest = projection_digest(
            tuple((item.evidence_id, item.snapshot.source_revision) for item in request.evidence)
        )

        provenance = AnswerJudgeProvenance(
            provider_id=PROVIDER_ID,
            provider_version=PROVIDER_VERSION,
            model_id=manifest["model_id"],
            model_revision=manifest["revision"],
            question_version=QUESTION_VERSION,
            question_hash=QUESTION_HASH,
            claim_digest=claim_digest,
            evidence_digest=evidence_digest,
            latency_ms=latency_ms,
            judged_at=datetime.now(UTC),
            abstained=abstained,
            provider_confidence=float(confidence),
            field_confidence=field_confidences,
        )
        return verdict, provenance

    async def judge_context(self, request):
        raise AnswerProviderError("ANSWER_JUDGE_UNSUPPORTED_CAPABILITY")

    async def judge_relation(self, request):
        raise AnswerProviderError("ANSWER_JUDGE_UNSUPPORTED_CAPABILITY")
