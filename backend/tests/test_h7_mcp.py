"""H7 MCP yüzeyi: kapalı işlem kümesi, yetki sınırı, gerçek taşıma."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.db import SessionLocal
from app.integrations.agent.mcp import mcp_server
from app.modules.todo.models import Todo
from tests.agent_test_utils import mcp_session, tool_payload

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def _tools() -> dict:
    return {tool.name: tool for tool in await mcp_server.list_tools()}


async def test_h7_tool_contract() -> None:
    tool = (await _tools())["forkos_execution"]
    schema = tool.input_schema
    assert schema["required"] == ["operation"]
    assert set(schema["properties"]["operation"]["enum"]) == {
        "prepare",
        "get",
        "list",
        "approve",
        "reject",
        "respond",
        "cancel",
        "execute",
        "recover",
        "status",
    }
    wire = tool.annotations.model_dump(by_alias=True, exclude_none=True)
    assert wire["readOnlyHint"] is False
    assert wire["destructiveHint"] is False
    assert wire["idempotentHint"] is True
    # Serbest araç/komut alanı YOK.
    for forbidden in ("tool_name", "command", "shell", "sql", "approved"):
        assert forbidden not in schema["properties"]


def _steps(title: str = "ALES başvurusunu tamamla") -> list[dict]:
    return [{"step_id": "s1", "action": "todo_create", "arguments": {"title": title}}]


async def test_prepare_get_approve_execute_over_transport(db_session: AsyncSession) -> None:
    """§76: gerçek `/mcp` üzerinden uçtan uca karar döngüsü."""
    async with mcp_session() as session:
        prepared = await session.call_tool(
            "forkos_execution",
            {"operation": "prepare", "title": "ALES planı", "steps": _steps(), "reason": "T-3"},
        )
        assert prepared.is_error is False, prepared.content
        plan = tool_payload(prepared)
        assert plan["state"] == "awaiting_approval"
        assert plan["decision_required"] is True
        plan_row_id = plan["plan_row_id"]
        revision = plan["revision"]

        # Onaysız yürütme REDDEDİLİR (model "onayladım" dese bile).
        blocked = await session.call_tool(
            "forkos_execution", {"operation": "execute", "plan_row_id": plan_row_id}
        )
        assert blocked.is_error is True
        assert "APPROVAL_REQUIRED" in blocked.content[0].text

        approved = await session.call_tool(
            "forkos_execution",
            {"operation": "approve", "plan_row_id": plan_row_id, "revision": revision},
        )
        assert approved.is_error is False, approved.content
        assert tool_payload(approved)["state"] == "approved"

        executed = await session.call_tool(
            "forkos_execution", {"operation": "execute", "plan_row_id": plan_row_id}
        )
        assert executed.is_error is False, executed.content
        result = tool_payload(executed)
        assert result["final_status"] == "completed"
        assert [item["status"] for item in result["receipts"]] == ["completed"]

    # Canonical mutasyon GERÇEKTEN oldu (H1 üzerinden).
    todos = list((await db_session.execute(select(Todo))).scalars())
    assert len(todos) == 1


async def test_wrong_revision_approval_is_rejected_over_transport(
    db_session: AsyncSession,
) -> None:
    async with mcp_session() as session:
        prepared = await session.call_tool(
            "forkos_execution", {"operation": "prepare", "title": "P", "steps": _steps()}
        )
        plan_row_id = tool_payload(prepared)["plan_row_id"]
        stale = await session.call_tool(
            "forkos_execution",
            {"operation": "approve", "plan_row_id": plan_row_id, "revision": "plan-v1:" + "0" * 64},
        )
    assert stale.is_error is True
    assert "APPROVAL_STALE" in stale.content[0].text


async def test_unknown_operation_and_action_are_rejected() -> None:
    async with mcp_session() as session:
        bad_op = await session.call_tool("forkos_execution", {"operation": "run_shell"})
        bad_action = await session.call_tool(
            "forkos_execution",
            {
                "operation": "prepare",
                "title": "Kötü",
                "steps": [{"action": "delete_everything", "arguments": {}}],
            },
        )
        missing_target = await session.call_tool(
            "forkos_execution",
            {
                "operation": "prepare",
                "title": "Hedefsiz",
                "steps": [
                    {
                        "action": "project_update",
                        "arguments": {"project_id": "00000000-0000-4000-8000-000000000000"},
                    }
                ],
            },
        )
    assert bad_op.is_error is True
    assert bad_action.is_error is True and "UNKNOWN_ACTION" in bad_action.content[0].text
    assert missing_target.is_error is True
    assert "STEP_TARGET_MISSING" in missing_target.content[0].text


async def test_status_lists_pending_decisions(db_session: AsyncSession) -> None:
    async with mcp_session() as session:
        await session.call_tool(
            "forkos_execution", {"operation": "prepare", "title": "Karar bekleyen", "steps": _steps()}
        )
        status = await session.call_tool("forkos_execution", {"operation": "status"})
    payload = tool_payload(status)
    assert payload["pending_decisions"]
    assert payload["pending_decisions"][0]["state"] == "awaiting_approval"


async def test_reject_and_respond_over_transport(db_session: AsyncSession) -> None:
    async with mcp_session() as session:
        prepared = await session.call_tool(
            "forkos_execution",
            {"operation": "prepare", "title": "Soru", "steps": _steps(), "input_questions": ["Hangi CV?"]},
        )
        plan = tool_payload(prepared)
        assert plan["state"] == "input_required"

        answered = await session.call_tool(
            "forkos_execution",
            {"operation": "respond", "plan_row_id": plan["plan_row_id"], "answers": {"cv": "Backend"}},
        )
        assert tool_payload(answered)["state"] == "draft"

        # Cevap sonrası plan `draft`tır: karar için YENİDEN hazırlanması gerekir.
        # Draft bir KARAR durumu değildir; kapatma yolu `cancel`dır.
        cancelled = await session.call_tool(
            "forkos_execution", {"operation": "cancel", "plan_row_id": plan["plan_row_id"]}
        )
        assert tool_payload(cancelled)["state"] == "cancelled"

    # Ayrı bir plan reddedilebilir (awaiting_approval → rejected).
    async with mcp_session() as session:
        other = await session.call_tool(
            "forkos_execution", {"operation": "prepare", "title": "Reddedilecek", "steps": _steps()}
        )
        rejected = await session.call_tool(
            "forkos_execution",
            {"operation": "reject", "plan_row_id": tool_payload(other)["plan_row_id"]},
        )
        assert tool_payload(rejected)["state"] == "rejected"


async def test_plan_operations_do_not_mutate_canonical_state(db_session: AsyncSession) -> None:
    """§68: prepare/approve/reject/respond/cancel canonical durumu DEĞİŞTİRMEZ."""
    async with SessionLocal() as seed:
        entity = Entity(type="todo", title="Dokunulmaz", search_text="")
        seed.add(entity)
        await seed.commit()
        target_id = entity.id

    async with mcp_session() as session:
        prepared = await session.call_tool(
            "forkos_execution", {"operation": "prepare", "title": "Karar", "steps": _steps()}
        )
        plan_row_id = tool_payload(prepared)["plan_row_id"]
        await session.call_tool("forkos_execution", {"operation": "list"})
        await session.call_tool("forkos_execution", {"operation": "get", "plan_row_id": plan_row_id})
        await session.call_tool("forkos_execution", {"operation": "approve", "plan_row_id": plan_row_id})
        await session.call_tool("forkos_execution", {"operation": "cancel", "plan_row_id": plan_row_id})

    async with SessionLocal() as check:
        rows = list((await check.execute(select(Todo))).scalars())
        entity_after = await check.get(Entity, target_id)
    assert rows == [], "karar operasyonları canonical mutasyon ÜRETMEMELİ"
    assert entity_after is not None and entity_after.title == "Dokunulmaz"
