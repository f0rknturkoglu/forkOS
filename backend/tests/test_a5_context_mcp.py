"""The sole A5.1 MCP tool: H3-first, read-only, bounded and default-off."""

import uuid

import pytest

from app.config import settings
from app.core.models import Entity
from app.db import SessionLocal
from app.integrations.agent.mcp import mcp_server
from tests.agent_test_utils import capture_db_content_fingerprint, mcp_session, tool_payload


@pytest.mark.no_database
async def test_context_judge_tool_contract():
    tools = {tool.name: tool for tool in await mcp_server.list_tools()}
    assert len(tools) == 36
    tool = tools["forkos_context_judge"]
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.destructive_hint is False
    properties = tool.input_schema["properties"]
    assert set(properties) == {"query", "entity_id", "scope", "since", "until", "max_depth", "limit"}
    assert properties["query"]["minLength"] == 2
    assert properties["query"]["maxLength"] == 200
    assert properties["limit"]["maximum"] == 15
    assert "provider" not in properties and "mode" not in properties
    assert tools["forkos_evidence"].annotations.read_only_hint is True


async def test_transport_off_preserves_original_h3_bundle(monkeypatch):
    monkeypatch.setattr(settings, "a5_context_mode", "off")
    entity_id = uuid.uuid4()
    async with SessionLocal() as session:
        session.add(Entity(id=entity_id, type="todo", title="Synthetic Atlas", search_text="Rust"))
        await session.commit()
        before = await capture_db_content_fingerprint(session)

    args = {"query": "Synthetic Atlas Rust", "entity_id": str(entity_id), "scope": "operational"}
    async with mcp_session() as client:
        h3 = await client.call_tool("forkos_evidence", args)
        a5 = await client.call_tool("forkos_context_judge", args)
    assert not h3.is_error and not a5.is_error
    h3_data = tool_payload(h3)["data"]
    a5_data = tool_payload(a5)["data"]
    assert a5_data["bundle"] == h3_data
    assert a5_data["mode"] == "off"
    assert a5_data["baseline_order"] == a5_data["advisory_order"] == a5_data["effective_order"]
    assert len(a5_data["verdicts"]) == len(h3_data["evidence"])

    async with SessionLocal() as session:
        assert await capture_db_content_fingerprint(session) == before
