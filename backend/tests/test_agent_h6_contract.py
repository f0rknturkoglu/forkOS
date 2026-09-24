"""H6 MCP yüzeyi: 29 araç, tek yeni kontrol aracı, kapalı işlem kümesi."""

from __future__ import annotations

import json

from app.integrations.agent.mcp import mcp_server
from app.modules.proactivity import models as proactivity_models
from app.modules.proactivity import policy as proactivity_policy
from app.modules.proactivity import service as proactivity_service

H6_TOOLS = {"forkos_proactivity"}
H7_TOOLS = {"forkos_execution"}

#: H6'nın genel yüzeye ASLA koymadığı yetenekler (§103/§155).
FORBIDDEN_OPERATIONS = {
    "execute_prompt",
    "run_tool",
    "schedule_prompt",
    "create_arbitrary_rule",
    "shell",
    "sql",
    "exec",
}


async def _tools() -> dict:
    return {tool.name: tool for tool in await mcp_server.list_tools()}


async def test_h6_adds_exactly_one_tool() -> None:
    tools = await _tools()
    assert len(tools) == 32
    assert set(tools) & H6_TOOLS == H6_TOOLS


async def test_h6_tool_annotations_are_conservative() -> None:
    """§104: yazabilir ama yıkıcı değil ve idempotent."""
    tool = (await _tools())["forkos_proactivity"]
    wire = tool.annotations.model_dump(by_alias=True, exclude_none=True)
    assert wire["readOnlyHint"] is False
    assert wire["destructiveHint"] is False
    assert wire["idempotentHint"] is True


async def test_operation_enum_is_closed() -> None:
    schema = (await _tools())["forkos_proactivity"].input_schema
    operations = set(schema["properties"]["operation"]["enum"])
    assert operations == {
        "status",
        "configure",
        "rule_set",
        "snooze",
        "unsnooze",
        "history",
        "evaluate_now",
    }
    assert not (operations & FORBIDDEN_OPERATIONS)
    assert schema["required"] == ["operation"]


async def test_tool_schema_exposes_no_internal_knobs() -> None:
    schema = (await _tools())["forkos_proactivity"].input_schema
    for forbidden in (
        "prompt",
        "cron",
        "expression",
        "query",
        "model",
        "provider",
        "base_url",
        "interval_seconds",
    ):
        assert forbidden not in schema["properties"]


def test_rule_kinds_are_a_closed_set() -> None:
    assert proactivity_models.RULE_KINDS == (
        "morning_continuity",
        "daily_close",
        "weekly_review",
        "deadline_staircase",
        "continuity_gap",
        "project_stalled",
    )


def test_outcomes_and_reason_codes_are_bounded() -> None:
    assert set(proactivity_policy.OUTCOMES) == {
        "silent",
        "defer",
        "digest",
        "surface",
        "prepare",
    }
    assert "MUTATE" not in proactivity_policy.OUTCOMES
    assert len(proactivity_policy.REASON_CODES) <= 30


def test_no_automatic_mutation_outcome_exists() -> None:
    """§12/§111: otomatik Level-4 (canonical mutasyon) YOKTUR."""
    dumped = json.dumps(proactivity_policy.CATEGORY_OUTCOMES).lower()
    assert "mutate" not in dumped
    source = "\n".join(
        item.read_text(encoding="utf-8")
        for item in __import__("pathlib").Path("app/modules/proactivity").glob("*.py")
    )
    for forbidden in ("create_entity(", "log_event(", "todo_service.", "opportunity_service."):
        assert forbidden not in source


def test_config_keys_are_closed() -> None:
    assert set(proactivity_service.CONFIG_DEFAULTS) == {
        "proactivity.enabled",
        "proactivity.quiet_hours_start",
        "proactivity.quiet_hours_end",
        "proactivity.focus_deferral_enabled",
        "proactivity.digest_time",
    }
    assert proactivity_service.CONFIG_DEFAULTS["proactivity.enabled"] is False
