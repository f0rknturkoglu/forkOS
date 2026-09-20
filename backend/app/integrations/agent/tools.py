from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

from app.db import SessionLocal
from app.integrations.agent import context as ctx_svc
from app.integrations.agent import knowledge as kn_svc
from app.integrations.agent.models import (
    ActivityEventData,
    AgentEnvelope,
    BrainReadData,
    BrainScope,
    BrainSearchResult,
    BrainStatusData,
    BriefingData,
    EntityContextData,
    EntitySearchResult,
    ProjectContextData,
)

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
)


def register_agent_tools(server: MCPServer) -> None:
    """Register all 8 read-only H0 Brain Interface tools."""

    @server.tool(
        name="forkos_briefing",
        description=(
            "Factual, bounded operational day briefing (agenda, open todos, deadlines, "
            "active projects, learning due, notifications, vault status). "
            "Read-only. Does not modify forkOS or the Vault."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def forkos_briefing(day: str | None = None) -> AgentEnvelope[BriefingData]:
        try:
            async with SessionLocal() as session:
                data = await ctx_svc.get_briefing_context(session, day=day)
                truncated = any([
                    len(data.open_todos) >= 20,
                    len(data.deadlines) >= 15,
                    len(data.active_projects) >= 10,
                    len(data.learning_due) >= 10,
                    len(data.opportunity_attention) >= 10,
                    len(data.notifications) >= 10,
                ])
                return AgentEnvelope(source="forkos", data=data, truncated=truncated)
        except Exception as exc:
            raise ToolError(f"BRIEFING_ERROR: {exc}") from exc

    @server.tool(
        name="forkos_search",
        description=(
            "Search active operational entities across forkOS (excluding legacy note entities). "
            "Read-only. Does not modify forkOS or the Vault."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def forkos_search(
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 10,
    ) -> AgentEnvelope[list[EntitySearchResult]]:
        try:
            async with SessionLocal() as session:
                results = await ctx_svc.search_operational_context(
                    session, query=query, entity_types=entity_types, limit=limit
                )
                truncated = len(results) >= limit
                return AgentEnvelope(source="forkos", data=results, truncated=truncated)
        except Exception as exc:
            raise ToolError(f"SEARCH_ERROR: {exc}") from exc

    @server.tool(
        name="forkos_entity_context",
        description=(
            "Inspect identity, deep links, related entities, and recent activity for an operational entity UUID. "
            "Read-only. Does not modify forkOS or the Vault."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def forkos_entity_context(entity_id: str) -> AgentEnvelope[EntityContextData]:
        try:
            async with SessionLocal() as session:
                data = await ctx_svc.get_entity_context(session, entity_id=entity_id)
                return AgentEnvelope(source="forkos", data=data, truncated=False)
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="forkos_project_context",
        description=(
            "Inspect compact project operational packet (status, milestones, open todos, recent activity, Vault note pointer). "
            "Read-only. Does not modify forkOS or the Vault."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def forkos_project_context(project_id: str) -> AgentEnvelope[ProjectContextData]:
        try:
            async with SessionLocal() as session:
                data = await ctx_svc.get_project_context(session, project_id=project_id)
                return AgentEnvelope(source="forkos", data=data, truncated=False)
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="forkos_recent_activity",
        description=(
            "Inspect sanitized append-only operational events. "
            "Read-only. Does not modify forkOS or the Vault."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def forkos_recent_activity(
        since: str | None = None,
        entity_type: str | None = None,
        verb: str | None = None,
        limit: int = 30,
    ) -> AgentEnvelope[list[ActivityEventData]]:
        try:
            async with SessionLocal() as session:
                data = await ctx_svc.get_recent_activity_context(
                    session, since=since, entity_type=entity_type, verb=verb, limit=limit
                )
                truncated = len(data) >= limit
                return AgentEnvelope(source="forkos", data=data, truncated=truncated)
        except Exception as exc:
            raise ToolError(f"ACTIVITY_ERROR: {exc}") from exc

    @server.tool(
        name="brain_status",
        description=(
            "Health, connectivity, and statistics of f0rknbrain Vault knowledge interface. "
            "Read-only. Does not modify forkOS or the Vault."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def brain_status() -> AgentEnvelope[BrainStatusData]:
        try:
            data = kn_svc.get_brain_status()
            return AgentEnvelope(source="f0rknbrain", data=data, truncated=False)
        except Exception as exc:
            raise ToolError(f"STATUS_ERROR: {exc}") from exc

    @server.tool(
        name="brain_search",
        description=(
            "Deterministic lexical search across all safe Markdown knowledge in the Vault (managed + unmanaged). "
            "Read-only. Does not modify forkOS or the Vault."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def brain_search(
        query: str,
        scope: BrainScope = "all",
        limit: int = 8,
    ) -> AgentEnvelope[list[BrainSearchResult]]:
        try:
            data = kn_svc.search_vault(query=query, scope=scope, limit=limit)
            truncated = len(data) >= limit
            return AgentEnvelope(source="f0rknbrain", data=data, truncated=truncated)
        except Exception as exc:
            raise ToolError(f"VAULT_SEARCH_ERROR: {exc}") from exc

    @server.tool(
        name="brain_read",
        description=(
            "Safe, bounded Markdown reader for a specific knowledge file by forkos_id or relative_path. "
            "Read-only. Does not modify forkOS or the Vault."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def brain_read(
        forkos_id: str | None = None,
        relative_path: str | None = None,
        heading: str | None = None,
    ) -> AgentEnvelope[BrainReadData]:
        try:
            data = kn_svc.read_vault_note(
                forkos_id=forkos_id, relative_path=relative_path, heading=heading
            )
            return AgentEnvelope(source="f0rknbrain", data=data, truncated=data.truncated)
        except Exception as exc:
            raise ToolError(str(exc)) from exc
