"""H2 sıcak hafıza araç sözleşmesi (yüzey, anotasyon, şema, yasaklar).

H2'nin dış sözleşmesini kilitler: tam olarak 5 araç, doğru okuma/yazma
anotasyonları, şemada görünür sınırlar, yol girdisinin YOKLUĞU ve yıkıcı ya da
genel amaçlı yetenek bulunmaması.
"""

from __future__ import annotations

import re

import pytest

from app.integrations.agent import hot_memory_models as models
from app.integrations.agent.mcp import mcp_server

pytestmark = pytest.mark.no_database

H2_TOOLS = (
    "hot_memory_context",
    "hot_memory_list",
    "hot_memory_store",
    "hot_memory_update",
    "hot_memory_retire",
)

H2_READ_TOOLS = ("hot_memory_context", "hot_memory_list")
H2_WRITE_TOOLS = ("hot_memory_store", "hot_memory_update", "hot_memory_retire")

#: §100 — araç başına beklenen idempotans.
H2_IDEMPOTENT = {
    "hot_memory_context": True,
    "hot_memory_list": True,
    "hot_memory_store": False,
    "hot_memory_update": True,
    "hot_memory_retire": True,
}

#: §41 — şemada görünmesi gereken sınırlar.
SCHEMA_BOUNDS: dict[tuple[str, str], dict[str, int]] = {
    ("hot_memory_store", "title"): {"maxLength": 120, "minLength": 1},
    ("hot_memory_store", "text"): {"maxLength": 1200, "minLength": 1},
    ("hot_memory_store", "tags"): {"maxItems": 8},
    ("hot_memory_store", "related_forkos_ids"): {"maxItems": 5},
    ("hot_memory_store", "importance"): {"minimum": 1, "maximum": 3},
    ("hot_memory_update", "title"): {"maxLength": 120},
    ("hot_memory_update", "text"): {"maxLength": 1200},
    ("hot_memory_update", "tags"): {"maxItems": 8},
    ("hot_memory_retire", "reason"): {"maxLength": 240},
}

#: H2'de ASLA bulunmaması gereken yetenek adları (§66-§68, §144).
FORBIDDEN_H2_PATTERN = re.compile(
    r"delete|purge|forget|drop|candidate|conversation|session|remember_all|bulk",
    re.IGNORECASE,
)


def _bound(spec: dict, key: str) -> int | None:
    if key in spec:
        return spec[key]
    for branch in spec.get("anyOf", []) or []:
        if key in branch:
            return branch[key]
    return None


async def _tools() -> dict:
    tools = await mcp_server.list_tools()
    return {tool.name: tool for tool in tools}


async def test_exactly_five_h2_tools() -> None:
    """§48/§40: H2 tam olarak 5 araç ekler; H5 sonrası yüzey 27'dir."""
    tool_map = await _tools()
    assert len(tool_map) == 37
    assert set(H2_TOOLS) <= set(tool_map)


async def test_h2_annotations_are_exact() -> None:
    """§100: okuma/yazma ve idempotans iddiaları araç başına doğrudur."""
    tool_map = await _tools()
    for name, expected_idempotent in H2_IDEMPOTENT.items():
        annotations = tool_map[name].annotations
        assert annotations.read_only_hint is (name in H2_READ_TOOLS), name
        assert annotations.destructive_hint is False, name
        assert annotations.idempotent_hint is expected_idempotent, name


async def test_no_delete_or_candidate_tool_exists() -> None:
    """§66/§67: silme ve aday araçları YÜZEYDE YOKTUR."""
    tool_map = await _tools()
    offenders = [
        name for name in tool_map
        if FORBIDDEN_H2_PATTERN.search(name) and not name.startswith("semantic_memory_")
    ]
    assert offenders == []


async def test_h2_write_descriptions_state_approval_and_locality() -> None:
    tool_map = await _tools()
    for name in H2_WRITE_TOOLS:
        description = tool_map[name].description or ""
        assert "requires user approval" in description, name
        assert "No external network calls" in description, name


async def test_h2_read_descriptions_are_marked_read_only() -> None:
    tool_map = await _tools()
    for name in H2_READ_TOOLS:
        assert "Read-only. Does not modify forkOS or the Vault." in (
            tool_map[name].description or ""
        ), name


async def test_h2_schema_bounds_are_visible() -> None:
    """§41/§46: sınırlar şemada görünür kalır (opak sözlüğe dönüşmez)."""
    tool_map = await _tools()
    for (tool_name, field), expected in SCHEMA_BOUNDS.items():
        properties = tool_map[tool_name].input_schema.get("properties", {})
        assert field in properties, f"{tool_name}.{field} şemada yok"
        for key, value in expected.items():
            assert _bound(properties[field], key) == value, f"{tool_name}.{field}.{key}"


async def test_h2_kind_enum_is_visible() -> None:
    tool_map = await _tools()
    store = tool_map["hot_memory_store"].input_schema["properties"]
    assert store["kind"]["enum"] == list(models.MemoryKindValue.__args__)
    assert "explicit_user" in store["source_mode"]["enum"]


async def test_h2_schemas_accept_no_paths() -> None:
    """§49/§72: H2 girdilerinde yol alanı YOKTUR."""
    tool_map = await _tools()
    for name in H2_TOOLS:
        properties = set(tool_map[name].input_schema.get("properties", {}))
        assert properties.isdisjoint({"path", "relative_path", "file", "filename"}), name


async def test_h2_write_schemas_require_revision_where_applicable() -> None:
    """§60/§64: güncelleme ve emeklilik revizyon önkoşulu ister."""
    tool_map = await _tools()
    for name in ("hot_memory_update", "hot_memory_retire"):
        required = set(tool_map[name].input_schema.get("required", []))
        assert {"memory_id", "expected_revision"} <= required, name

    store_required = set(tool_map["hot_memory_store"].input_schema.get("required", []))
    assert {"kind", "title", "text", "source_mode"} <= store_required
    # §56: sunucu kimlik üretir; çağıran memory_id veremez.
    assert "memory_id" not in tool_map["hot_memory_store"].input_schema["properties"]


def test_memory_models_reject_unknown_fields_and_bad_kinds() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        models.HotMemoryStoreIn(
            kind="preference", title="x", text="y", source_mode="explicit_user", memory_id="z"
        )
    with pytest.raises(ValidationError):
        models.HotMemoryStoreIn(kind="gecersiz", title="x", text="y", source_mode="explicit_user")
    with pytest.raises(ValidationError):
        models.HotMemoryStoreIn(
            kind="preference", title="x" * 121, text="y", source_mode="explicit_user"
        )
    with pytest.raises(ValidationError):
        models.HotMemoryStoreIn(
            kind="preference", title="x", text="y", source_mode="explicit_user", tags=[f"t{i}" for i in range(9)]
        )
    with pytest.raises(ValidationError):
        models.HotMemoryStoreIn(
            kind="preference",
            title="x",
            text="y",
            source_mode="explicit_user",
            related_forkos_ids=[str(__import__("uuid").uuid4())] * 6,
        )
    with pytest.raises(ValidationError):
        models.HotMemoryRetireIn(memory_id="11111111-1111-1111-1111-111111111111", expected_revision="kisa")
