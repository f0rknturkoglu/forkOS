"""H4 sözleşme modelleri, sınırlar ve lane/argüman uyumu."""

from __future__ import annotations

import inspect

import pytest

from app.integrations.local_cognition import contracts as contract_svc
from app.integrations.local_cognition import models as lc
from app.integrations.local_cognition import policy as policy_svc

TEXT = "29 Kasım ALES sınavı var."


def _names(schema: dict) -> set[str]:
    names: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                names.update(properties.keys())
                for value in properties.values():
                    walk(value)
            for key in ("items", "anyOf", "allOf", "oneOf", "$defs", "additionalProperties"):
                if key in node:
                    walk(node[key])
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)
    return names


# ---------------------------------------------------------------------------
# Lane/argüman uyumu (§30)
# ---------------------------------------------------------------------------


def test_classify_request_requires_labels_and_goal() -> None:
    request = lc.build_lane_request(
        lane="classify", text=TEXT, labels=["deadline", "task"], classification_goal="Ata"
    )
    assert isinstance(request, lc.ClassifyRequest)
    assert request.labels == ["deadline", "task"]


def test_structured_extract_requires_known_contract() -> None:
    request = lc.build_lane_request(
        lane="structured_extract", text=TEXT, contract="academic_calendar_v1"
    )
    assert isinstance(request, lc.StructuredExtractRequest)

    with pytest.raises(lc.H4Error, match="INVALID_ARGUMENT"):
        lc.build_lane_request(lane="structured_extract", text=TEXT, contract="made_up_v9")
    with pytest.raises(lc.H4Error, match="INVALID_ARGUMENT"):
        lc.build_lane_request(lane="structured_extract", text=TEXT)


def test_query_rewrite_accepts_only_text_and_protected_terms() -> None:
    request = lc.build_lane_request(lane="query_rewrite", text=TEXT, protected_terms=["ALES"])
    assert isinstance(request, lc.QueryRewriteRequest)
    assert request.protected_terms == ["ALES"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"lane": "classify", "text": TEXT, "labels": ["a", "b"], "classification_goal": "x", "contract": "weekly_schedule_v1"},
        {"lane": "classify", "text": TEXT, "labels": ["a", "b"], "classification_goal": "x", "protected_terms": ["a"]},
        {"lane": "structured_extract", "text": TEXT, "contract": "weekly_schedule_v1", "labels": ["a", "b"]},
        {"lane": "structured_extract", "text": TEXT, "contract": "weekly_schedule_v1", "protected_terms": ["a"]},
        {"lane": "query_rewrite", "text": TEXT, "contract": "weekly_schedule_v1"},
        {"lane": "query_rewrite", "text": TEXT, "labels": ["a", "b"]},
    ],
)
def test_incompatible_lane_arguments_are_rejected(kwargs: dict) -> None:
    with pytest.raises(lc.H4Error, match="INVALID_ARGUMENT"):
        lc.build_lane_request(**kwargs)


@pytest.mark.parametrize("lane", ["rerank", "compress"])
def test_deferred_lanes_are_rejected(lane: str) -> None:
    with pytest.raises(lc.H4Error, match="INVALID_LANE"):
        lc.build_lane_request(lane=lane, text=TEXT)


@pytest.mark.parametrize("lane", ["reason", "chat", "answer", "plan"])
def test_reasoning_lanes_are_rejected(lane: str) -> None:
    """Muhakeme Hermes'e aittir; H4 genel bir asistan değildir (§116)."""
    with pytest.raises(lc.H4Error, match="INVALID_LANE"):
        lc.build_lane_request(lane=lane, text=TEXT)


def test_unknown_lane_is_rejected() -> None:
    with pytest.raises(lc.H4Error, match="INVALID_LANE"):
        lc.build_lane_request(lane="summarize", text=TEXT)


# ---------------------------------------------------------------------------
# Çalışma zamanı sınırları (§29/§120)
# ---------------------------------------------------------------------------


def _classify(**overrides) -> lc.LaneRequest:
    """ÜRETİM giriş yolu: sınırlar burada uygulanır (modeli elle kurmak testi

    gerçek çağrı yolundan koparırdı).
    """
    payload: dict = {
        "lane": "classify",
        "text": TEXT,
        "labels": ["a", "b"],
        "classification_goal": "x",
    }
    payload.update(overrides)
    return lc.build_lane_request(**payload)


def test_text_bounds_are_enforced() -> None:
    with pytest.raises(lc.H4Error, match="INVALID_ARGUMENT"):
        lc.validate_lane_request(_classify(text="a"))
    with pytest.raises(lc.H4Error, match="INVALID_ARGUMENT"):
        lc.validate_lane_request(_classify(text="x" * (lc.MAX_TEXT_CHARS + 1)))


def test_label_bounds_and_uniqueness_are_enforced() -> None:
    with pytest.raises(lc.H4Error, match="INVALID_ARGUMENT"):
        lc.validate_lane_request(_classify(labels=["tek"]))
    with pytest.raises(lc.H4Error, match="INVALID_ARGUMENT"):
        lc.validate_lane_request(_classify(labels=[f"l{i}" for i in range(lc.MAX_LABELS + 1)]))
    with pytest.raises(lc.H4Error, match="INVALID_ARGUMENT"):
        lc.validate_lane_request(_classify(labels=["a", "a"]))
    with pytest.raises(lc.H4Error, match="INVALID_ARGUMENT"):
        lc.validate_lane_request(_classify(labels=["a", "  "]))
    with pytest.raises(lc.H4Error, match="INVALID_ARGUMENT"):
        lc.validate_lane_request(_classify(labels=["a", "x" * (lc.MAX_LABEL_CHARS + 1)]))


def test_classification_goal_bound_is_enforced() -> None:
    with pytest.raises(lc.H4Error, match="INVALID_ARGUMENT"):
        lc.validate_lane_request(
            _classify(classification_goal="x" * (lc.MAX_CLASSIFICATION_GOAL_CHARS + 1))
        )


def test_protected_term_bounds_are_enforced() -> None:
    too_many = [f"t{i}" for i in range(lc.MAX_PROTECTED_TERMS + 1)]
    # Şema/model katmanı: sayı sınırı kurulumda reddedilir.
    with pytest.raises(lc.H4Error, match="INVALID_ARGUMENT"):
        lc.build_lane_request(lane="query_rewrite", text=TEXT, protected_terms=too_many)
    # Çalışma zamanı katmanı: boş terim semantik olarak geçersizdir.
    blank = lc.build_lane_request(lane="query_rewrite", text=TEXT, protected_terms=["  "])
    with pytest.raises(lc.H4Error, match="INVALID_ARGUMENT"):
        lc.validate_lane_request(blank)


def test_bounds_are_not_silently_clamped() -> None:
    """İhlal KIRPILMAZ: sınır dışı girdi reddedilir."""
    with pytest.raises(lc.H4Error) as excinfo:
        lc.validate_lane_request(_classify(labels=["tek"]))
    assert excinfo.value.code == "INVALID_ARGUMENT"


# ---------------------------------------------------------------------------
# Çıktı sözleşmesi (§39/§66/§150)
# ---------------------------------------------------------------------------


def test_result_models_have_no_confidence_or_reasoning_fields() -> None:
    forbidden = {
        "confidence",
        "probability",
        "certainty",
        "truth_score",
        "reasoning",
        "chain_of_thought",
        "explanation",
    }
    names = (
        _names(lc.ClassificationResult.model_json_schema())
        | _names(lc.QueryRewriteResult.model_json_schema())
        | _names(lc.ExtractionResult.model_json_schema())
        | _names(lc.RouteDecision.model_json_schema())
        | _names(lc.LocalCognitionResponse.model_json_schema())
    )
    assert not (names & forbidden)


def test_attempt_metadata_carries_no_raw_content() -> None:
    names = _names(lc.AttemptRecord.model_json_schema())
    for forbidden in ("prompt", "response", "raw_output", "source_text", "evidence", "memory"):
        assert forbidden not in names


def test_route_decision_exposes_inspectable_fields() -> None:
    names = _names(lc.RouteDecision.model_json_schema())
    assert {
        "lane",
        "selected_slot",
        "selected_model",
        "execution_boundary",
        "input_chars",
        "required_capabilities",
        "reason_codes",
        "attempts",
        "validation_status",
        "escalated",
        "latency_ms",
    } <= names


def test_execution_boundary_is_loopback_only() -> None:
    schema = lc.RouteDecision.model_json_schema()
    boundary = schema["properties"]["execution_boundary"]
    assert boundary.get("const", boundary.get("enum")) in ("local_loopback", ["local_loopback"])


# ---------------------------------------------------------------------------
# Çıkarım sözleşmeleri
# ---------------------------------------------------------------------------


#: Sözleşme başına koleksiyon tavanı — sürümün PARÇASIDIR, belgelenmiştir.
EXPECTED_ITEM_CAPS = {
    "academic_calendar_v1": 80,
    "weekly_schedule_v1": 80,
    "deadline_candidates_v1": 80,
    "consolidation_candidates_v1": 30,
    "episodic_turn_v1": 6,
}


def test_extraction_contracts_are_versioned_and_bounded() -> None:
    assert set(contract_svc.EXTRACTION_SCHEMAS) == set(lc.EXTRACTION_CONTRACTS)
    assert all(name.endswith("_v1") for name in lc.EXTRACTION_CONTRACTS)
    assert set(EXPECTED_ITEM_CAPS) == set(lc.EXTRACTION_CONTRACTS)

    for name, (collection_key, schema) in contract_svc.EXTRACTION_SCHEMAS.items():
        assert collection_key in schema["properties"]
        assert schema["properties"][collection_key]["maxItems"] == EXPECTED_ITEM_CAPS[name], name


def test_contract_items_require_source_excerpt() -> None:
    for _name, (collection_key, schema) in contract_svc.EXTRACTION_SCHEMAS.items():
        item = schema["$defs"][
            schema["properties"][collection_key]["items"]["$ref"].rsplit("/", 1)[-1]
        ]
        assert "source_excerpt" in item["required"]
        assert "source_excerpt" in item["properties"]


def test_contracts_forbid_extra_fields() -> None:
    outcome = contract_svc.validate_academic_calendar(
        {
            "events": [
                {
                    "title": "Kayıt",
                    "category": "registration",
                    "date_text": "1 Eylül",
                    "source_excerpt": "1 Eylül",
                    "confidence": 0.9,
                }
            ]
        },
        "Kayıt 1 Eylül tarihinde.",
    )
    assert outcome.ok is False
    assert outcome.code == "OUTPUT_SCHEMA_MISMATCH"


# ---------------------------------------------------------------------------
# Politika yüzeyi: metin GÖRMEZ (§20/§148)
# ---------------------------------------------------------------------------


def test_route_task_cannot_see_the_text() -> None:
    """Yönlendirme metni hiç görmez: 'zor görünüyor' diye karar veremez."""
    signature = inspect.signature(policy_svc.route_task)
    assert "text" not in signature.parameters
    assert set(signature.parameters) == {"lane", "input_chars", "profiles", "health"}


# ---------------------------------------------------------------------------
# H4 final cila — otomatik kimlik koruma (§4-§9)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("entity 4f1c9a2e-7b3d-4c58-9a11-2d6e8f0b7c34", ("4f1c9a2e-7b3d-4c58-9a11-2d6e8f0b7c34",)),
        ("see https://example.invalid/a/b.md.", ("https://example.invalid/a/b.md",)),
        ("repo f0rknturkoglu/forkOS release", ("f0rknturkoglu/forkOS",)),
        ("version v2.4.1 shipped", ("v2.4.1",)),
        ("version 2.4.1 shipped", ("2.4.1",)),
        ("forkjob repo status", ()),
        ("Tarih 12/09/2026 ve saat 10:00", ()),
        ("forkjobda rustu neden seçtik", ()),
        ("", ()),
    ],
)
def test_identifier_detection_is_conservative(text: str, expected: tuple[str, ...]) -> None:
    """Yalnızca apaçık kimlikler; tarih ve serbest metin korunmaz (§6)."""
    assert contract_svc.detect_identifiers(text) == expected


def test_identifier_detection_is_order_stable_and_deduplicated() -> None:
    text = "b/x then a/y then b/x again"
    assert contract_svc.detect_identifiers(text) == ("b/x", "a/y")


def test_identifier_detection_is_bounded() -> None:
    text = " ".join(f"owner{i}/repo{i}" for i in range(20))
    assert len(contract_svc.detect_identifiers(text)) == contract_svc.MAX_AUTO_PROTECTED_TERMS


def test_effective_terms_prefer_explicit_terms_and_stay_stable() -> None:
    terms = contract_svc.effective_protected_terms("v2.4.1 shipped", ["forkjob", "forkjob"])
    assert terms == ("forkjob", "v2.4.1")


@pytest.mark.parametrize(
    "identifier",
    [
        "4f1c9a2e-7b3d-4c58-9a11-2d6e8f0b7c34",
        "https://example.invalid/a/b.md",
        "f0rknturkoglu/forkOS",
        "v2.4.1",
    ],
)
def test_rewrite_must_preserve_auto_detected_identifiers(identifier: str) -> None:
    """§8/§160: açık terim verilmese bile kimlik düşürülemez."""
    source = f"Show evidence for {identifier} now"
    dropped = contract_svc.validate_query_rewrite(
        {"rewritten_query": "evidence request summary"}, source, []
    )
    assert dropped.ok is False
    assert dropped.code == "PROTECTED_TERM_LOST"

    kept = contract_svc.validate_query_rewrite(
        {"rewritten_query": f"evidence {identifier}"}, source, []
    )
    assert kept.ok is True


def test_explicit_terms_still_enforced_alongside_auto_detection() -> None:
    source = "forkjobda rustu neden seçtik 4f1c9a2e-7b3d-4c58-9a11-2d6e8f0b7c34"
    outcome = contract_svc.validate_query_rewrite(
        {"rewritten_query": "forkjob Rust gerekçesi"}, source, ["forkjob", "Rust"]
    )
    assert outcome.ok is False
    assert outcome.code == "PROTECTED_TERM_LOST"


def test_prompt_and_validator_share_the_same_term_list() -> None:
    """§9: prompt ile doğrulayıcı AYNI yardımcıyı kullanır (sürüklenme yok)."""
    from app.integrations.local_cognition import prompts as prompt_svc

    request = lc.build_lane_request(
        lane="query_rewrite",
        text="entity 4f1c9a2e-7b3d-4c58-9a11-2d6e8f0b7c34 repo",
        protected_terms=["forkjob"],
    )
    prompt = prompt_svc.build_user_prompt(request)
    for term in contract_svc.effective_protected_terms(request.text, request.protected_terms):
        assert term in prompt
