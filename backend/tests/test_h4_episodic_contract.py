"""`episodic_turn_v1` — A3 oturum episodu çıkarım sözleşmesi (DB'siz).

H4'ün ortak kapısı korunur: şema → birebir kaynak kanıtı (`source_excerpt`)
→ tutarlılık. Bu dosya yeni sözleşmenin KENDİ sınırlarını kilitler: madde
tavanı (≤ 6), `text` tavanı (≤ 300), kapalı `kind` kümesi ve boş listenin
geçerli bir çıktı olması.
"""

from __future__ import annotations

import pytest

from app.integrations.local_cognition import contracts as contract_svc
from app.integrations.local_cognition import models as lc
from app.integrations.local_cognition import prompts as prompts_svc

pytestmark = pytest.mark.no_database

TURN_TEXT = (
    "episodic handoff modülünü A3 için ekleyelim\n"
    "H4 tarafına episodic_turn_v1 sözleşmesini ekledim; DB kısmı yarın\n"
)

VALID_ITEM = {
    "kind": "session_decision",
    "text": "Oturumda A3 için kaynak bağlı oturum devri yapılmasına karar verildi.",
    "source_excerpt": "episodic handoff modülünü A3 için ekleyelim",
}


def _validate(items: list[dict], text: str = TURN_TEXT):
    return contract_svc.validate_episodic_turn({"items": items}, text)


def test_grounded_turn_items_are_accepted() -> None:
    outcome = _validate([VALID_ITEM])

    assert outcome.ok is True
    assert outcome.payload is not None
    assert outcome.payload["items"][0]["kind"] == "session_decision"


def test_source_excerpt_must_be_verbatim_from_the_turn() -> None:
    outcome = _validate([{**VALID_ITEM, "source_excerpt": "turda hiç geçmeyen bir cümle"}])

    assert outcome.ok is False
    assert outcome.code == "SOURCE_EXCERPT_NOT_FOUND"


def test_turn_item_cap_is_enforced() -> None:
    outcome = _validate([VALID_ITEM] * 7)

    assert outcome.ok is False
    assert outcome.code in {"OUTPUT_TOO_LARGE", "OUTPUT_SCHEMA_MISMATCH"}


def test_item_text_cap_is_enforced() -> None:
    outcome = _validate([{**VALID_ITEM, "text": "x" * 301}])

    assert outcome.ok is False
    assert outcome.code in {"OUTPUT_TOO_LARGE", "OUTPUT_SCHEMA_MISMATCH"}


def test_kind_must_come_from_the_fixed_set() -> None:
    outcome = _validate([{**VALID_ITEM, "kind": "preference"}])

    assert outcome.ok is False
    assert outcome.code == "OUTPUT_SCHEMA_MISMATCH"


def test_blank_item_text_is_rejected() -> None:
    """Şemadan geçen ama hiçbir şey söylemeyen madde kabul edilmez."""
    outcome = _validate([{**VALID_ITEM, "text": "   "}])

    assert outcome.ok is False
    assert outcome.code == "OUTPUT_SCHEMA_MISMATCH"


def test_empty_turn_yields_an_empty_list() -> None:
    outcome = _validate([])

    assert outcome.ok is True
    assert outcome.payload == {"items": []}


def test_contract_is_wired_into_the_structured_extract_path() -> None:
    """Kayıt eksik olsaydı istek/prompt yolu `KeyError` verirdi."""
    request = lc.build_lane_request(
        lane="structured_extract", text=TURN_TEXT, contract="episodic_turn_v1"
    )
    prompt = prompts_svc.build_user_prompt(request)

    assert "episodic_turn_v1" in prompt
    assert "open_thread" in prompt
