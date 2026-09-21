"""MCP Streamable HTTP taşıma testleri.

§116/§117: araçlar yalnızca doğrudan Python çağrısıyla değil, GERÇEK `/mcp`
taşıması üzerinden de doğrulanır -- Hermes tam olarak bu yolu kullanır.

Tüm oturumlar `mcp_session()` ile **hermetik** açılır: FastAPI `lifespan`'ının
başlangıç yan etkileri (RSS kurulumu, günlük bakım, kaynak catch-up) test
ortamında kapatılır; aksi halde arka planda yazıp testin transaction'ıyla kilit
yarışına giriyorlar.
"""

from __future__ import annotations

import json
import uuid

import httpx
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.modules.todo.models import Todo
from tests.agent_test_utils import hermetic_lifespan, mcp_session

READ_TOOL_NAMES = {
    "forkos_briefing",
    "forkos_search",
    "forkos_entity_context",
    "forkos_project_context",
    "forkos_recent_activity",
    "brain_status",
    "brain_search",
    "brain_read",
}

WRITE_TOOL_NAMES = {
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
}


def _payload(result) -> dict:
    """Araç sonucundan JSON gövdesini çıkarır (structured ya da text)."""
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict) and structured:
        return structured
    return json.loads(result.content[0].text)


@pytest.mark.no_database
async def test_mcp_fastapi_mount_and_smoke():
    """`/mcp` FastAPI'ye doğru bağlanmış ve resmi istemciyle konuşuyor mu."""
    async with mcp_session() as session:
        init_result = await session.initialize()
        assert init_result.server_info.name == "forkos-brain"

        # 8 H0 + 11 H1 + 5 H2 + 1 H3 + 1 H4 + 1 H5 = 27
        tools = await session.list_tools()
        tool_names = {t.name for t in tools.tools}
        assert tool_names >= READ_TOOL_NAMES
        assert tool_names >= WRITE_TOOL_NAMES
        assert "forkos_evidence" in tool_names
        assert "forkos_local_cognition" in tool_names
        assert "forkos_review_intelligence" in tool_names
        assert len(tool_names) == 29

        status_res = await session.call_tool("brain_status", {})
        assert status_res.is_error is False
        assert "brain_interface_version" in status_res.content[0].text


@pytest.mark.no_database
async def test_mcp_write_annotations_are_visible_over_the_wire():
    """§117: Hermes'in onay davranışı araç metadata'sına bağlıdır."""
    async with mcp_session() as session:
        tools = {t.name: t for t in (await session.list_tools()).tools}

        for name in READ_TOOL_NAMES:
            assert tools[name].annotations.read_only_hint is True, name

        idempotent = {
            "forkos_todo_update",
            "forkos_todo_complete",
            "forkos_todo_plan",
            "forkos_project_update",
            "forkos_bookmark_update",
        }
        for name in WRITE_TOOL_NAMES:
            annotations = tools[name].annotations
            assert annotations.read_only_hint is False, name
            assert annotations.destructive_hint is False, name
            assert annotations.idempotent_hint == (name in idempotent), name


async def test_mcp_transport_h1_write_roundtrip():
    """§116: yazma yolu gerçek taşıma üzerinden çalışır ve DB'de doğrulanır."""
    async with mcp_session() as session:
        created = await session.call_tool(
            "forkos_todo_create",
            {"title": "H1 smoke over /mcp", "priority": 1},
        )
        assert created.is_error is False, created.content

        receipt = _payload(created)["data"]
        assert receipt["tool"] == "forkos_todo_create"
        assert receipt["status"] == "executed"
        assert receipt["target_type"] == "todo"

        # §14: istek kimliği GİRDİ değildir; yalnızca tanılama alanıdır.
        listed = {t.name: t for t in (await session.list_tools()).tools}
        assert "request_id" not in listed["forkos_todo_create"].input_schema.get(
            "properties", {}
        )

        todo_id = uuid.UUID(receipt["target_id"])
        async with SessionLocal() as db:
            todo = await db.get(Todo, todo_id)
            assert todo is not None
            assert todo.status == "open"

        # Tamamlama turu: canonical semantik taşıma üzerinden de çalışır.
        completed = await session.call_tool(
            "forkos_todo_complete", {"todo_id": str(todo_id)}
        )
        assert completed.is_error is False, completed.content
        completion_receipt = _payload(completed)["data"]
        assert completion_receipt["status"] == "executed"
        assert completion_receipt["after"]["status"] == "done"

        # İkinci tamamlama noop döner ve ek kayıt üretmez (§27).
        again = await session.call_tool("forkos_todo_complete", {"todo_id": str(todo_id)})
        assert again.is_error is False
        assert _payload(again)["data"]["status"] == "noop"
        async with SessionLocal() as db:
            rows = (await db.execute(select(Todo).where(Todo.id == todo_id))).scalars().all()
            assert len(rows) == 1


async def test_mcp_transport_error_envelope_is_model_readable():
    """§67: taşıma üzerinden hata kodu net döner; yığın izi sızmaz."""
    async with mcp_session() as session:
        missing = await session.call_tool(
            "forkos_todo_complete", {"todo_id": str(uuid.uuid4())}
        )
        assert missing.is_error is True
        text = missing.content[0].text
        assert "TARGET_NOT_FOUND" in text
        assert "Traceback" not in text

        invalid = await session.call_tool("forkos_bookmark_capture", {"url": "ftp://example.com"})
        assert invalid.is_error is True
        assert "INVALID_INPUT" in invalid.content[0].text


@pytest.mark.no_database
async def test_mcp_dns_rebinding_rejection():
    """Localhost dışı host/origin başlıkları DNS rebinding korumasınca reddedilir."""
    async with (
        hermetic_lifespan(),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://evil.com",
            headers={"host": "evil.com", "origin": "http://evil.com"},
        ) as http_client,
    ):
        res = await http_client.post(
            "http://evil.com/mcp/",
            json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1},
        )
        assert res.status_code in (400, 403, 421)
