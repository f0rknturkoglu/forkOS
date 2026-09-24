"""Optional local poorjev adapter; no ML import, network, or load at API startup."""

from __future__ import annotations

import asyncio
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from app.integrations.agent.evidence_revision import projection_digest

from .memory_models import (
    MemoryJudgeProvenance,
    MemorySignals,
    RelatedMemoryRelation,
)

PROVIDER_ID = "poorjev-local-nli"
PROVIDER_VERSION = "0.1.0"
MODEL_ID = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"
MODEL_REVISION = "8e7e5af5983a0ddb1a5b45a38b129ab69e2258e8"
QUESTION_VERSION = "a5-memory-questions-v1"
MODEL_MANIFEST = "forkos-poorjev-model.json"

# Values are full NLI hypotheses, not vague one-word class names. Changing
# wording requires a new question version and frozen evaluation fixture.
HYPOTHESES: dict[str, dict[str, str]] = {
    "evidence_support": {
        "supported": "The source fully supports this claim: {candidate}",
        "partially_supported": "The source only partly supports this claim: {candidate}",
        "unsupported": "The source does not support this claim: {candidate}",
        "uncertain": "It is unclear whether the source supports this claim: {candidate}",
    },
    "intent": {
        "explicit": "The person explicitly decided or requested: {candidate}",
        "implicit": "This is inferred, not explicitly decided by the person: {candidate}",
        "tentative": "The person may or might decide this, but has not settled it: {candidate}",
        "uncertain": "The person's intent about this is unclear: {candidate}",
    },
    "durability": {
        "durable": "This is a lasting preference or decision: {candidate}",
        "temporary": "This is only a temporary state or short-lived plan: {candidate}",
        "uncertain": "The duration of this claim is unknown: {candidate}",
    },
    "scope_relation": {
        "same_scope": "The source supports this claim in exactly the stated scope: {candidate}",
        "narrower_scope": "This claim is narrower than the source: {candidate}",
        "broader_scope": "This claim is broader than the source: {candidate}",
        "different_scope": "This claim concerns a different scope from the source: {candidate}",
        "uncertain": "The scope of this claim cannot be compared to the source: {candidate}",
    },
    "conditions_preserved": {
        "yes": "This claim preserves every condition in the source: {candidate}",
        "no": "This claim omits a condition from the source: {candidate}",
        "not_applicable": "The source contains no material condition for this claim: {candidate}",
        "uncertain": "Condition preservation is unclear for this claim: {candidate}",
    },
    "exceptions_preserved": {
        "yes": "This claim preserves every exception in the source: {candidate}",
        "no": "This claim omits an exception from the source: {candidate}",
        "not_applicable": "The source contains no material exception for this claim: {candidate}",
        "uncertain": "Exception preservation is unclear for this claim: {candidate}",
    },
    "relation": {
        "duplicate": "This adds no meaningful information to the prior memory: {candidate}",
        "same_claim": "This states the same core claim as the prior memory: {candidate}",
        "narrows": "This is a narrower version of the prior memory: {candidate}",
        "elaborates": "This adds compatible detail to the prior memory: {candidate}",
        "incompatible": "This conflicts with the prior memory in the same scope and time: {candidate}",
        "changed_decision": "The source explicitly replaces the prior decision with this newer decision: {candidate}",
        "unrelated": "This is unrelated to the prior memory: {candidate}",
        "uncertain": "The relation to the prior memory is unclear: {candidate}",
    },
}
QUESTION_HASH = projection_digest(HYPOTHESES)


class MemoryProviderError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class MemoryJudgePacket:
    statement: str
    kind: str
    scope: str
    scope_project: str | None
    conditions: tuple[str, ...]
    exceptions: tuple[str, ...]
    source_texts: tuple[str, ...]
    related: tuple[tuple[str, str], ...]
    candidate_snapshot: str
    source_snapshot: str
    related_snapshot: str
    policy_snapshot: str


def _premise(packet: MemoryJudgePacket, related: str | None = None) -> str:
    # Do not put the candidate in the premise: it would support itself.
    lines = [f"Source {i}: {source}" for i, source in enumerate(packet.source_texts)]
    if related is not None:
        lines.append(f"Prior memory: {related}")
    return "\n".join(lines)


def _question_specs(packet: MemoryJudgePacket) -> dict[str, tuple[str, ...]]:
    specs = {name: tuple(options) for name, options in HYPOTHESES.items() if name != "relation"}
    for index, _ in enumerate(packet.related):
        specs[f"relation_{index}"] = tuple(HYPOTHESES["relation"])
    return specs


class PoorJevMemoryProvider:
    """One local NLI model, lazy and serialized; failure never switches provider."""

    def __init__(self, model_path: str, *, timeout_seconds: float = 20.0) -> None:
        self.model_path = Path(model_path).expanduser()
        self.timeout_seconds = min(max(float(timeout_seconds), 0.1), 60.0)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="poorjev-memory")
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
            raise MemoryProviderError("MEMORY_MODEL_UNAVAILABLE") from exc

    def _ask(self, packet: MemoryJudgePacket):
        # The default forkOS image has none of these optional dependencies.
        # Upstream calls from_pretrained() without local_files_only; force the
        # underlying Hugging Face stack offline before it is imported.
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        try:
            from poorjev import Choice
            from poorjev.backends.local_nli import LocalNLIBackend
        except ImportError as exc:
            raise MemoryProviderError("MEMORY_DEPENDENCY_ABSENT") from exc
        try:
            if version("poorjev") != PROVIDER_VERSION:
                raise MemoryProviderError("MEMORY_PROVIDER_VERSION_MISMATCH")
        except PackageNotFoundError as exc:
            raise MemoryProviderError("MEMORY_DEPENDENCY_ABSENT") from exc
        if self._client is None:
            self._client = LocalNLIBackend(model_name=str(self.model_path.resolve(strict=True)))
        specs = _question_specs(packet)
        pairs: list[tuple[str, str]] = []
        plan = {}
        for name, labels in specs.items():
            family = "relation" if name.startswith("relation_") else name
            related = packet.related[int(name.split("_")[1])][1] if family == "relation" else None
            premise = _premise(packet, related)
            hypotheses = [
                HYPOTHESES[family][label].format(candidate=packet.statement) for label in labels
            ]
            plan[name] = (Choice(hypotheses), len(pairs), len(hypotheses))
            pairs.extend((premise, hypothesis) for hypothesis in hypotheses)
        probabilities = self._client.entail_probs(pairs)  # one local batched pass
        if len(probabilities) != len(pairs):
            raise MemoryProviderError("MEMORY_INVALID_RESPONSE")
        return {
            name: question.decide(probabilities[start : start + count], kind="probs")
            for name, (question, start, count) in plan.items()
        }

    async def judge(self, packet: MemoryJudgePacket) -> tuple[MemorySignals, MemoryJudgeProvenance]:
        manifest = self._read_manifest()
        async with self._lock:
            if self._pending is not None and not self._pending.done():
                raise MemoryProviderError("MEMORY_PROVIDER_BUSY")
            started = time.perf_counter()
            loop = asyncio.get_running_loop()
            self._pending = loop.run_in_executor(self._executor, self._ask, packet)
            try:
                answers = await asyncio.wait_for(asyncio.shield(self._pending), self.timeout_seconds)
            except TimeoutError as exc:
                raise MemoryProviderError("MEMORY_PROVIDER_TIMEOUT") from exc
            except MemoryProviderError:
                raise
            except Exception as exc:
                raise MemoryProviderError("MEMORY_PROVIDER_UNAVAILABLE") from exc
        specs = _question_specs(packet)
        if set(answers) != set(specs):
            raise MemoryProviderError("MEMORY_INVALID_RESPONSE")
        labels: dict[str, str] = {}
        confidences: dict[str, float] = {}
        abstained = False
        for name, options in specs.items():
            family = "relation" if name.startswith("relation_") else name
            answer = answers[name]
            inverse = {
                HYPOTHESES[family][label].format(candidate=packet.statement): label
                for label in options
            }
            value = inverse.get(getattr(answer, "value", None))
            confidence = getattr(answer, "confidence", None)
            if value is None or not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise MemoryProviderError("MEMORY_INVALID_RESPONSE")
            labels[name] = value
            confidences[name] = float(confidence)
            abstained = abstained or bool(getattr(answer, "abstained", False))
        signals = MemorySignals(
            evidence_support=labels["evidence_support"],
            intent=labels["intent"],
            durability=labels["durability"],
            scope_relation=labels["scope_relation"],
            conditions_preserved=labels["conditions_preserved"],
            exceptions_preserved=labels["exceptions_preserved"],
            relations=tuple(
                RelatedMemoryRelation(card_id=card_id, relation=labels[f"relation_{i}"])
                for i, (card_id, _) in enumerate(packet.related)
            ),
        )
        provenance = MemoryJudgeProvenance(
            provider_id=PROVIDER_ID,
            provider_version=PROVIDER_VERSION,
            model_id=manifest["model_id"],
            model_revision=manifest["revision"],
            calibration_id=None,
            question_version=QUESTION_VERSION,
            question_hash=QUESTION_HASH,
            candidate_snapshot=packet.candidate_snapshot,
            source_snapshot=packet.source_snapshot,
            related_snapshot=packet.related_snapshot,
            policy_snapshot=packet.policy_snapshot,
            latency_ms=int((time.perf_counter() - started) * 1000),
            judged_at=datetime.now(UTC),
            abstained=abstained,
            field_confidence=confidences,
            selected_source_count=len(packet.source_texts),
        )
        return signals, provenance
