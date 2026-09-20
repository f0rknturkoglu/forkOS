"""H1 genel sözleşme: araç yüzeyi, anotasyonlar ve girdi sınırları.

Bu dosya H1'in DIŞ sözleşmesini kilitler: tam olarak 19 genel MCP aracı,
doğru okuma/yazma anotasyonları, yıkıcı veya genel amaçlı yetenek YOKLUĞU ve
şemada görünür girdi sınırları.
"""

from __future__ import annotations

import re

import pytest

from app.integrations.agent import write_models
from app.integrations.agent.mcp import mcp_server

pytestmark = pytest.mark.no_database

#: H0 okuma araçları (§2) — semantik olarak DEĞİŞMEZ.
READ_TOOLS = (
    "forkos_briefing",
    "forkos_search",
    "forkos_entity_context",
    "forkos_project_context",
    "forkos_recent_activity",
    "brain_status",
    "brain_search",
    "brain_read",
)

#: H1 yazma araçları (§8) — tam olarak 11 tanedir.
WRITE_TOOLS = (
    "forkos_todo_create",
    "forkos_todo_update",
    "forkos_todo_complete",
    "forkos_todo_plan",
    "forkos_project_update",
    "forkos_opportunity_transition",
    "forkos_application_transition",
    "forkos_bookmark_capture",
    "forkos_bookmark_update",
    "brain_capture",
    "brain_save_to_entity",
)

#: `idempotentHint` ARAÇ BAŞINA doğru olmalıdır (§11).
IDEMPOTENT_TOOLS = frozenset(
    {
        "forkos_todo_update",
        "forkos_todo_complete",
        "forkos_todo_plan",
        "forkos_project_update",
        "forkos_bookmark_update",
    }
)

#: H2 sıcak hafıza araçları (§48) — 8 + 11 + 5 = 24.
H2_TOOLS = (
    "hot_memory_context",
    "hot_memory_list",
    "hot_memory_store",
    "hot_memory_update",
    "hot_memory_retire",
)

#: Şemada görünmesi gereken sınırlar (§66) — (araç, alan) -> beklenen anahtar/değer.
SCHEMA_BOUNDS: dict[tuple[str, str], dict[str, int]] = {
    ("forkos_todo_create", "title"): {"maxLength": 300, "minLength": 1},
    ("forkos_todo_create", "description"): {"maxLength": 5000},
    ("forkos_todo_create", "tags"): {"maxItems": 20},
    ("forkos_todo_create", "priority"): {"minimum": 0, "maximum": 3},
    ("forkos_todo_update", "title"): {"maxLength": 300},
    ("forkos_todo_plan", "start_min"): {"minimum": 0, "maximum": 1439},
    ("forkos_todo_plan", "duration_min"): {"minimum": 5, "maximum": 1440},
    ("forkos_project_update", "next_action"): {"maxLength": 500},
    ("forkos_opportunity_transition", "note"): {"maxLength": 1000},
    ("forkos_application_transition", "note"): {"maxLength": 1000},
    ("forkos_application_transition", "rejection_reason"): {"maxLength": 200},
    ("forkos_bookmark_capture", "url"): {"maxLength": 2048},
    ("forkos_bookmark_capture", "note"): {"maxLength": 5000},
    ("forkos_bookmark_update", "tags"): {"maxItems": 20},
    ("brain_capture", "body"): {"maxLength": 40000, "minLength": 1},
    ("brain_capture", "title"): {"maxLength": 300},
    ("brain_save_to_entity", "text"): {"maxLength": 20000, "minLength": 1},
    ("brain_save_to_entity", "heading"): {"maxLength": 200},
}

#: Araç -> şemayı üreten katı model. Alan adları birebir eşleşmelidir.
TOOL_MODELS: dict[str, type] = {
    "forkos_todo_create": write_models.TodoCreateIn,
    "forkos_todo_update": write_models.TodoUpdateIn,
    "forkos_todo_plan": write_models.TodoPlanIn,
    "forkos_project_update": write_models.ProjectUpdateIn,
    "forkos_opportunity_transition": write_models.OpportunityTransitionIn,
    "forkos_application_transition": write_models.ApplicationTransitionIn,
    "forkos_bookmark_capture": write_models.BookmarkCaptureIn,
    "forkos_bookmark_update": write_models.BookmarkUpdateIn,
    "brain_capture": write_models.BrainCaptureIn,
    "brain_save_to_entity": write_models.BrainSaveToEntityIn,
}

#: H1'de ASLA bulunmaması gereken yetenek adları (§3/§9/§72).
FORBIDDEN_NAME_PATTERN = re.compile(
    r"delete|drop|purge|reset|disconnect|credential|token|oauth|restore|bulk"
    r"|scrape|ingest|refresh|enrich|call_api|execute_sql|write_file|run_command"
    r"|arbitrary|raw_sql|filesystem",
    re.IGNORECASE,
)


def _bound(spec: dict, key: str) -> int | None:
    """Sınırı üst düzeyde ya da `anyOf` dalında arar (Optional alanlar)."""
    if key in spec:
        return spec[key]
    for branch in spec.get("anyOf", []) or []:
        if key in branch:
            return branch[key]
    return None


async def _tools() -> dict:
    tools = await mcp_server.list_tools()
    return {tool.name: tool for tool in tools}


async def test_exact_public_tool_surface() -> None:
    """§8/§48: 8 okuma + 11 yazma + 5 sıcak hafıza + 1 H3 kanıt = 25.

    H1'in kendi sözleşmesi (11 yazma aracı) değişmedi; H3 yüzeye tam olarak
    bir salt-okunur araç ekledi.
    """
    tool_map = await _tools()
    assert len(tool_map) == 25
    assert set(tool_map) == set(READ_TOOLS) | set(WRITE_TOOLS) | set(H2_TOOLS) | {"forkos_evidence"}


async def test_read_tools_keep_readonly_annotations() -> None:
    """§2: H0 okuma kanıtı zayıflatılmaz."""
    tool_map = await _tools()
    for name in READ_TOOLS:
        annotations = tool_map[name].annotations
        assert annotations.read_only_hint is True, name
        assert annotations.destructive_hint is False, name


async def test_write_tools_annotations_are_exact() -> None:
    """§11/§71: yazma araçları write-capable olarak işaretlenir; idempotans doğru."""
    tool_map = await _tools()
    for name in WRITE_TOOLS:
        annotations = tool_map[name].annotations
        assert annotations.read_only_hint is False, name
        assert annotations.destructive_hint is False, name
        assert annotations.idempotent_hint == (name in IDEMPOTENT_TOOLS), name


async def test_no_destructive_or_generic_tool_exists() -> None:
    """§3/§9/§72/§144: yıkıcı ya da genel amaçlı yetenek YÜZEYDE YOKTUR."""
    tool_map = await _tools()
    offenders = [name for name in tool_map if FORBIDDEN_NAME_PATTERN.search(name)]
    assert offenders == []


async def test_no_write_tool_exposes_a_deletion_switch() -> None:
    """§9: yazma araçlarının şemasında silme anahtarı bulunamaz."""
    tool_map = await _tools()
    for name in WRITE_TOOLS:
        properties = set(tool_map[name].input_schema.get("properties", {}))
        assert properties.isdisjoint(
            {"delete", "permanent", "hard_delete", "force", "purge", "drop"}
        ), name


async def test_write_descriptions_state_approval_and_locality() -> None:
    """§70: Hermes onaydan önce onay ve ağ davranışını görebilmeli."""
    tool_map = await _tools()
    for name in WRITE_TOOLS:
        description = tool_map[name].description or ""
        assert "requires user approval" in description, name
        assert "No external network calls" in description, name
        assert "Write operation" in description, name


async def test_todo_complete_description_mentions_recurrence() -> None:
    """§27: onaylanan eylemin yan etkisi açıkça yazılı olmalı."""
    tool_map = await _tools()
    description = tool_map["forkos_todo_complete"].description or ""
    assert "recurrence" in description
    assert "next occurrence" in description


async def test_schema_bounds_are_visible_to_clients() -> None:
    """§66: sınırlar yalnızca çalışma zamanında değil, ŞEMADA da görünür."""
    tool_map = await _tools()
    for (tool_name, field), expected in SCHEMA_BOUNDS.items():
        properties = tool_map[tool_name].input_schema.get("properties", {})
        assert field in properties, f"{tool_name}.{field} şemada yok"
        spec = properties[field]
        for key, value in expected.items():
            assert _bound(spec, key) == value, f"{tool_name}.{field}.{key}"


async def test_tool_input_fields_match_strict_models() -> None:
    """Şema kayması koruması: araç alanları katı modelle BİREBİR aynı olmalı."""
    tool_map = await _tools()
    for tool_name, model in TOOL_MODELS.items():
        properties = set(tool_map[tool_name].input_schema.get("properties", {}))
        assert properties == set(model.model_fields), tool_name


async def test_no_tool_accepts_a_request_id_or_path_input() -> None:
    """§14/§49/§55: istek kimliği girdi DEĞİLDİR; YAZMA araçları yol kabul etmez.

    H0 `brain_read` okuma için `relative_path` alabilir (kullanıcı notu
    okunabilir); H1 yazma yüzeyi ise yalnızca `forkos_id` ile hedeflenir.
    """
    tool_map = await _tools()
    for name, tool in tool_map.items():
        properties = set(tool.input_schema.get("properties", {}))
        assert "request_id" not in properties, name
    for name in WRITE_TOOLS:
        properties = set(tool_map[name].input_schema.get("properties", {}))
        assert properties.isdisjoint({"relative_path", "path", "file", "target_path"}), name


def test_strict_models_reject_injected_terminal_states() -> None:
    """§21/§24: durum alanı dışarıdan enjekte edilemez."""
    from pydantic import ValidationError

    for payload in (
        {"title": "x", "status": "done"},
        {"title": "x", "status": "dropped"},
    ):
        with pytest.raises(ValidationError):
            write_models.TodoCreateIn.model_validate(payload)

    with pytest.raises(ValidationError):
        write_models.TodoUpdateIn.model_validate({"todo_id": "x", "status": "done"})


def test_runtime_bounds_match_documented_limits() -> None:
    """Şemada ilan edilen sınırların ÇALIŞMA ZAMANI karşılığı da vardır (§65)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        write_models.TodoCreateIn(title="x" * 301)
    with pytest.raises(ValidationError):
        write_models.BrainCaptureIn(body="x" * 40001)
    with pytest.raises(ValidationError):
        write_models.BrainCaptureIn(body="   ")
    with pytest.raises(ValidationError):
        write_models.TodoPlanIn(todo_id="11111111-1111-1111-1111-111111111111", day="2026-9-1")
    with pytest.raises(ValidationError):
        write_models.TodoCreateIn(title="ok", tags=[f"t{i}" for i in range(21)])
    with pytest.raises(ValidationError):
        write_models.BrainSaveToEntityIn(forkos_id="x", text="x" * 20001)


def test_bookmark_collection_vocabulary_matches_canonical_source() -> None:
    """§65: şemadaki sözlük canonical domain sözlüğünden sapamaz."""
    from typing import get_args

    from app.modules.bookmark.models import COLLECTIONS, READ_STATUSES

    assert set(get_args(write_models.COLLECTION_VALUES)) == set(COLLECTIONS)
    assert set(get_args(write_models.READ_STATUS_VALUES)) == set(READ_STATUSES)
