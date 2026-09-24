"""Frozen label mapping and local-provider fail-safe tests."""

import builtins
import time
from types import SimpleNamespace

import pytest

from app.integrations.judgment.memory_models import MemorySignals
from app.integrations.judgment.poorjev_memory import (
    HYPOTHESES,
    QUESTION_HASH,
    MemoryJudgePacket,
    MemoryProviderError,
    PoorJevMemoryProvider,
    _premise,
    _question_specs,
)
from scripts.eval_a5_memory import FIXTURE_SHA256, load_fixture

pytestmark = pytest.mark.no_database


def packet():
    return MemoryJudgePacket(
        statement="Use Rust for Atlas.", kind="decision", scope="project",
        scope_project="Atlas", conditions=(), exceptions=(),
        source_texts=("From now on use Rust for Atlas.",),
        related=(("prior-1", "Use Python for Atlas."),),
        candidate_snapshot="c" * 64, source_snapshot="s" * 64,
        related_snapshot="r" * 64, policy_snapshot="p" * 64,
    )


def test_frozen_fixture_and_taxonomy():
    cases = load_fixture()
    assert len(cases) == 23
    assert len(FIXTURE_SHA256) == 64
    assert QUESTION_HASH == "51cc78bf261d1f1148c85fed8c72b46505a067d873fcb79fe198bd5da8b2d329"
    assert {case["relation"] for case in cases if case["relation"]} == set(HYPOTHESES["relation"])
    assert {case["support"] for case in cases} == set(HYPOTHESES["evidence_support"])
    assert {case["intent"] for case in cases} == set(HYPOTHESES["intent"])
    assert len([case for case in cases if case["split"] == "holdout"]) == 12


def test_candidate_is_not_in_evidence_premise():
    item = packet()
    assert item.statement not in _premise(item)
    assert item.source_texts[0] in _premise(item)
    assert item.statement in HYPOTHESES["evidence_support"]["supported"].format(
        candidate=item.statement
    )


@pytest.mark.parametrize("relation", tuple(HYPOTHESES["relation"]))
async def test_all_relation_labels_are_typed(monkeypatch, tmp_path, relation):
    provider = PoorJevMemoryProvider(str(tmp_path))
    monkeypatch.setattr(provider, "_read_manifest", lambda: {"model_id": "local", "revision": "rev"})
    item = packet()

    def fake_ask(input_packet):
        assert input_packet == item
        choices = {
            "evidence_support": "supported", "intent": "explicit", "durability": "durable",
            "scope_relation": "same_scope", "conditions_preserved": "yes",
            "exceptions_preserved": "not_applicable", "relation_0": relation,
        }
        return {
            name: SimpleNamespace(
                value=HYPOTHESES["relation" if name.startswith("relation_") else name][choices[name]].format(
                    candidate=item.statement
                ),
                confidence=0.7, abstained=False,
            )
            for name in _question_specs(item)
        }

    monkeypatch.setattr(provider, "_ask", fake_ask)
    signals, provenance = await provider.judge(item)
    assert isinstance(signals, MemorySignals)
    assert signals.relations[0].relation == relation
    assert provenance.question_hash is not None
    assert provenance.calibration_id is None


async def test_invalid_provider_answer_rejected(monkeypatch, tmp_path):
    provider = PoorJevMemoryProvider(str(tmp_path))
    monkeypatch.setattr(provider, "_read_manifest", lambda: {"model_id": "local", "revision": "rev"})
    monkeypatch.setattr(provider, "_ask", lambda _: {"relation_0": object()})
    with pytest.raises(MemoryProviderError, match="MEMORY_INVALID_RESPONSE"):
        await provider.judge(packet())


async def test_missing_model_fails_before_import(tmp_path):
    provider = PoorJevMemoryProvider(str(tmp_path / "absent"))
    with pytest.raises(MemoryProviderError, match="MEMORY_MODEL_UNAVAILABLE"):
        await provider.judge(packet())


def test_missing_poorjev_dependency_is_explicit(monkeypatch, tmp_path):
    provider = PoorJevMemoryProvider(str(tmp_path))
    original = builtins.__import__

    def without_poorjev(name, *args, **kwargs):
        if name == "poorjev":
            raise ImportError("synthetic missing dependency")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_poorjev)
    with pytest.raises(MemoryProviderError, match="MEMORY_DEPENDENCY_ABSENT"):
        provider._ask(packet())


async def test_model_failure_and_timeout_are_explicit(monkeypatch, tmp_path):
    monkeypatch.setattr(
        PoorJevMemoryProvider, "_read_manifest",
        lambda _: {"model_id": "local", "revision": "rev"},
    )
    failing = PoorJevMemoryProvider(str(tmp_path))
    monkeypatch.setattr(failing, "_ask", lambda _: (_ for _ in ()).throw(RuntimeError("load")))
    with pytest.raises(MemoryProviderError, match="MEMORY_PROVIDER_UNAVAILABLE"):
        await failing.judge(packet())

    slow = PoorJevMemoryProvider(str(tmp_path), timeout_seconds=0.1)

    def sleepy(_):
        time.sleep(0.2)
        return {}

    monkeypatch.setattr(slow, "_ask", sleepy)
    with pytest.raises(MemoryProviderError, match="MEMORY_PROVIDER_TIMEOUT"):
        await slow.judge(packet())
