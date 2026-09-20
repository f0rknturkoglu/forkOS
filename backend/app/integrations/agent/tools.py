from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import Field, ValidationError

from app.db import SessionLocal
from app.integrations.agent import actions as actions_svc
from app.integrations.agent import context as ctx_svc
from app.integrations.agent import evidence as ev_svc
from app.integrations.agent import evidence_models as ev_models
from app.integrations.agent import hot_memory as hm_svc
from app.integrations.agent import knowledge as kn_svc
from app.integrations.agent.hot_memory_models import (
    MAX_QUERY_LENGTH,
    MAX_RELATED,
    MAX_REVISION_LENGTH,
    MAX_TAGS,
    MAX_TEXT,
    MAX_TITLE,
    EffectiveStatusFilter,
    HotMemoryContextData,
    HotMemoryListData,
    HotMemoryRetireIn,
    HotMemoryStoreIn,
    HotMemoryUpdateIn,
    MemoryKindValue,
    SourceModeValue,
)
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
from app.integrations.agent.write_models import (
    COLLECTION_VALUES,
    READ_STATUS_VALUES,
    ActionReceipt,
    ApplicationTransitionIn,
    BookmarkCaptureIn,
    BookmarkUpdateIn,
    BrainCaptureIn,
    BrainSaveToEntityIn,
    OpportunityTransitionIn,
    ProjectUpdateIn,
    TodoCreateIn,
    TodoPlanIn,
    TodoUpdateIn,
)
from app.integrations.local_cognition import models as lc_models
from app.integrations.local_cognition import service as lc_svc
from app.integrations.review_intelligence import models as ri_models
from app.integrations.review_intelligence import service as ri_svc

#: H1 girdi sınırları (§66). Şemada GÖRÜNÜR olmalı ki Hermes onaydan önce
#: limitleri bilebilsin; yürütmedeki otorite yine `write_models` doğrulamasıdır.
Title = Annotated[str, Field(min_length=1, max_length=300)]
OptionalTitle = Annotated[str | None, Field(max_length=300)]
Tags = Annotated[list[str] | None, Field(max_length=20)]
IsoDay = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]


READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
)

#: H6 kontrol araci: YALNIZCA kendi konfigurasyon/override durumunu yazar.
#: Yikici degil ve ayni girdiyle tekrar cagrilabilir (idempotent).
PROACTIVITY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
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

    _register_write_tools(server)
    _register_hot_memory_tools(server)
    _register_evidence_tool(server)
    _register_local_cognition_tool(server)
    _register_review_intelligence_tool(server)
    _register_proactivity_tool(server)


# ---------------------------------------------------------------------------
# H1 yazma araçları (onaylı semantik mutasyonlar)
# ---------------------------------------------------------------------------

#: Her H1 aracının açıklamasında bulunması ZORUNLU cümleler (§70).
_APPROVAL_NOTE = (
    "Write operation; requires user approval when this MCP server is configured "
    "as untrusted. No external network calls."
)


def _write_annotations(*, idempotent: bool) -> ToolAnnotations:
    """H1 mutasyon anotasyonları (§11/§12).

    `readOnlyHint=False` her yazma aracında zorunludur: Hermes'in untrusted
    onay yüzeyi tam olarak bu bayrağa bakar. H1'de yıkıcı araç YOKTUR, bu
    yüzden `destructiveHint` her zaman False'tur -- ama bir silme yeteneği
    eklenirse bayrağı değiştirmek değil, o yeteneği H1'den ÇIKARMAK gerekir.
    """
    return ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=idempotent,
    )


def _request_id(ctx: Context | None) -> str | None:
    """MCP istek kimliği -- yalnızca tanılama korelasyonu (§14).

    Yetkilendirme DEĞİLDİR; kalıcı bir onay/oturum alt sistemi kurulmaz.
    İstek bağlamı yoksa (doğrudan Python çağrısı) sessizce None döner.
    """
    if ctx is None:
        return None
    try:
        return ctx.request_id
    except Exception:  # istek bağlamı dışında: tanılama alanı boş kalır
        return None


def _supplied_arguments(ctx: Context | None) -> set[str] | None:
    """MCP çağrısında kullanıcının GERÇEKTEN gönderdiği alan adları.

    Neden gerekli: MCP handler'ları Python imzasıyla çalışır, dolayısıyla
    `None` varsayılanı olan bir alan modele her zaman geçerse
    `model_fields_set` onu "açıkça verilmiş" sayar ve

        alan hiç gönderilmedi   ≠   alan null gönderildi

    ayrımı yok olur. Bu ayrım olmadan kısmi güncelleme, ilgisiz alanları
    temizler. Çözüm: alan listesini ham istek argümanlarından okumak --
    şema değişmez, ayrım korunur.

    Bağlama sözleşmesi (H1.2) — üç durum vardır:

        ctx yok                     → doğrudan Python/test yolu; None döner ve
                                      çağıran tüm alanları verilmiş sayar.
        ctx var + argümanlar okundu → normal yol; alan adları döner.
        ctx var + argümanlar OKUNAMIYOR → FAIL CLOSED.

    Üçüncü durum kritiktir: MCP SDK iç yerleşimini değiştirirse "her Python
    argümanı verilmiş say" varsayımına düşmek, H1.1'de kapatılan
    omitted-vs-null hatasını sessizce geri getirirdi. Bunun yerine işlem
    reddedilir; sessiz veri kaybı yerine gürültülü hata tercih edilir.
    """
    if ctx is None:
        return None

    try:
        params = ctx.request_context.params
    except Exception as exc:  # istek bağlamı okunamadı
        raise actions_svc.ActionError(
            "MCP_ARGUMENT_BINDING_UNAVAILABLE",
            "MCP istek bağlamı okunamadı; çağrı güvenle yorumlanamıyor",
        ) from exc

    arguments = getattr(params, "arguments", None)
    if arguments is None and isinstance(params, Mapping):
        arguments = params.get("arguments")
    if not isinstance(arguments, Mapping):
        raise actions_svc.ActionError(
            "MCP_ARGUMENT_BINDING_UNAVAILABLE",
            "MCP çağrı argümanları çözülemedi; hangi alanların verildiği bilinemiyor",
        )
    return {str(key) for key in arguments}


def _supplied_only(supplied: set[str] | None, values: dict[str, Any]) -> dict[str, Any]:
    """Yalnızca çağrıda geçen alanları bırakır (omitted ≠ null)."""
    if supplied is None:
        return values
    return {key: value for key, value in values.items() if key in supplied}


def _first_validation_error(exc: ValidationError) -> str:
    """Pydantic hatasını sınırlı, model-okunur tek satıra indirir (§67)."""
    errors = exc.errors()
    if not errors:
        return "geçersiz girdi"
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", ()))
    return f"{location}: {first.get('msg', 'geçersiz')}"


async def _run_write(
    *,
    tool: str,
    source: str,
    factory: Callable[[set[str] | None], Any],
    action: Callable[..., Awaitable[ActionReceipt]],
    ctx: Context | None,
) -> AgentEnvelope[ActionReceipt]:
    """H1 yazmalarının TEK yürütme yolu (§110).

    Sıra: MCP argüman bağlaması → katı girdi doğrulaması → taze oturum →
    canonical adaptör → makbuz. Bağlama çözülemezse fail-closed
    (`MCP_ARGUMENT_BINDING_UNAVAILABLE`); hiçbir yazma denenmez.
    Hata yüzeyi model-okunurdur: yığın izi ve iç dosya yolu SIZMAZ.
    """
    try:
        supplied = _supplied_arguments(ctx)
        data = factory(supplied)
        async with SessionLocal() as session:
            receipt = await action(session, data, request_id=_request_id(ctx))
    except actions_svc.ActionError as exc:
        raise ToolError(str(exc)) from exc
    except ValidationError as exc:
        raise ToolError(f"INVALID_INPUT: {_first_validation_error(exc)}") from exc
    except ValueError as exc:
        raise ToolError(f"INVALID_INPUT: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - sızıntısız hata zarfı
        raise ToolError(f"ACTION_FAILED: {type(exc).__name__}") from exc
    return AgentEnvelope(source=source, data=receipt, truncated=False)  # type: ignore[arg-type]


def _register_write_tools(server: MCPServer) -> None:
    """11 H1 yazma aracını kaydeder.

    Gövdeler İNCE tutulur: iş mantığı `actions.py` ve canonical domain
    servislerindedir; burada yalnızca şema, oturum ve hata zarfı vardır.
    """

    @server.tool(
        name="forkos_todo_create",
        description=(
            "Create one forkOS todo. Optional plan_day writes a planner slot in the same "
            "transaction; project_id links the todo to a project (belongs_to). New todos are "
            "always created as open. " + _APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=False),
    )
    async def forkos_todo_create(
        title: Title,
        description: Annotated[str | None, Field(max_length=5000)] = None,
        priority: Annotated[int, Field(ge=0, le=3)] = 2,
        due_at: str | None = None,
        reminder_at: str | None = None,
        plan_day: str | None = None,
        project_id: str | None = None,
        milestone_id: str | None = None,
        parent_id: str | None = None,
        tags: Tags = None,
        recur: Annotated[str | None, Field(pattern="^(daily|weekdays|weekly|monthly)$")] = None,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="forkos_todo_create",
            source="forkos",
            factory=lambda supplied: TodoCreateIn(**_supplied_only(supplied, dict(
                title=title,
                description=description,
                priority=priority,
                due_at=due_at,
                reminder_at=reminder_at,
                plan_day=plan_day,
                project_id=project_id,
                milestone_id=milestone_id,
                parent_id=parent_id,
                tags=tags or [],
                recur=recur,
            ))),
            action=actions_svc.create_todo,
            ctx=ctx,
        )

    @server.tool(
        name="forkos_todo_update",
        description=(
            "Update metadata of one existing forkOS todo (title, description, priority, dates, "
            "tags, recurrence). Does not complete, delete or restructure relationships - "
            "completion has its own tool. " + _APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=True),
    )
    async def forkos_todo_update(
        todo_id: str,
        title: OptionalTitle = None,
        description: Annotated[str | None, Field(max_length=5000)] = None,
        priority: Annotated[int | None, Field(ge=0, le=3)] = None,
        due_at: str | None = None,
        reminder_at: str | None = None,
        tags: Tags = None,
        recur: Annotated[str | None, Field(pattern="^(daily|weekdays|weekly|monthly)?$")] = None,
        expected_updated_at: str | None = None,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="forkos_todo_update",
            source="forkos",
            factory=lambda supplied: TodoUpdateIn(**_supplied_only(supplied, dict(
                todo_id=todo_id,
                title=title,
                description=description,
                priority=priority,
                due_at=due_at,
                reminder_at=reminder_at,
                tags=tags,
                recur=recur,
                expected_updated_at=expected_updated_at,
            ))),
            action=actions_svc.update_todo,
            ctx=ctx,
        )

    @server.tool(
        name="forkos_todo_complete",
        description=(
            "Complete one forkOS todo using canonical recurrence rules. Completing a recurring "
            "todo may create its next occurrence according to forkOS recurrence rules. "
            "Completing an already-completed todo returns status=noop and creates nothing. "
            + _APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=True),
    )
    async def forkos_todo_complete(
        todo_id: str,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="forkos_todo_complete",
            source="forkos",
            factory=lambda supplied: todo_id,
            action=actions_svc.complete_todo,
            ctx=ctx,
        )

    @server.tool(
        name="forkos_todo_plan",
        description=(
            "Plan or reschedule one forkOS todo using canonical planner slots. Fails with "
            "AMBIGUOUS_PLAN when several future slots exist. Does not change todo content. "
            + _APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=True),
    )
    async def forkos_todo_plan(
        todo_id: str,
        day: IsoDay,
        start_min: Annotated[int | None, Field(ge=0, le=1439)] = None,
        duration_min: Annotated[int | None, Field(ge=5, le=1440)] = None,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="forkos_todo_plan",
            source="forkos",
            factory=lambda supplied: TodoPlanIn(**_supplied_only(supplied, dict(
                todo_id=todo_id, day=day, start_min=start_min, duration_min=duration_min
            ))),
            action=actions_svc.plan_todo,
            ctx=ctx,
        )

    @server.tool(
        name="forkos_project_update",
        description=(
            "Update the operational next_action of one forkOS project. Intentionally narrow: "
            "no rename, no repo/url/stack changes, no deletion, and it does NOT rewrite the "
            "project's Vault knowledge note. " + _APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=True),
    )
    async def forkos_project_update(
        project_id: str,
        next_action: Annotated[str | None, Field(max_length=500)] = None,
        expected_updated_at: str | None = None,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="forkos_project_update",
            source="forkos",
            factory=lambda supplied: ProjectUpdateIn(**_supplied_only(supplied, dict(
                project_id=project_id,
                next_action=next_action,
                expected_updated_at=expected_updated_at,
            ))),
            action=actions_svc.update_project,
            ctx=ctx,
        )

    @server.tool(
        name="forkos_opportunity_transition",
        description=(
            "Move one forkOS opportunity/announcement through its discovery lifecycle using "
            "canonical transition rules. This is NOT the application CRM pipeline; application "
            "stages have their own tool. Requires expected_status for stale-state safety. "
            + _APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=False),
    )
    async def forkos_opportunity_transition(
        opportunity_id: str,
        expected_status: str,
        to_status: str,
        note: Annotated[str | None, Field(max_length=1000)] = None,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="forkos_opportunity_transition",
            source="forkos",
            factory=lambda supplied: OpportunityTransitionIn(**_supplied_only(supplied, dict(
                opportunity_id=opportunity_id,
                expected_status=expected_status,
                to_status=to_status,
                note=note,
            ))),
            action=actions_svc.transition_opportunity,
            ctx=ctx,
        )

    @server.tool(
        name="forkos_application_transition",
        description=(
            "Move one forkOS job application through the CRM pipeline (applied, interview, "
            "offer, accepted, rejected, withdrawn, closed) using canonical lifecycle rules. "
            "With no application row, only 'applied' may create it. Requires expected_status "
            "for stale-state safety. Terminal states are operational state, not deletion. "
            + _APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=False),
    )
    async def forkos_application_transition(
        opportunity_id: str,
        to_status: str,
        expected_status: str | None = None,
        note: Annotated[str | None, Field(max_length=1000)] = None,
        rejection_reason: Annotated[str | None, Field(max_length=200)] = None,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="forkos_application_transition",
            source="forkos",
            factory=lambda supplied: ApplicationTransitionIn(**_supplied_only(supplied, dict(
                opportunity_id=opportunity_id,
                expected_status=expected_status,
                to_status=to_status,
                note=note,
                rejection_reason=rejection_reason,
            ))),
            action=actions_svc.transition_application,
            ctx=ctx,
        )

    @server.tool(
        name="forkos_bookmark_capture",
        description=(
            "Save a URL as a forkOS bookmark locally. Performs NO web fetch, NO metadata "
            "scraping and NO enrichment; it does not create a knowledge note. An already "
            "saved URL returns status=noop pointing at the existing bookmark. " + _APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=False),
    )
    async def forkos_bookmark_capture(
        url: Annotated[str, Field(max_length=2048)],
        title: OptionalTitle = None,
        collection: COLLECTION_VALUES = "inbox",
        tags: Tags = None,
        note: Annotated[str | None, Field(max_length=5000)] = None,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="forkos_bookmark_capture",
            source="forkos",
            factory=lambda supplied: BookmarkCaptureIn(**_supplied_only(supplied, dict(
                url=url,
                title=title,
                collection=collection,
                tags=tags or [],
                note=note,
            ))),
            action=actions_svc.capture_bookmark,
            ctx=ctx,
        )

    @server.tool(
        name="forkos_bookmark_update",
        description=(
            "Update low-risk bookmark fields: collection, favorite, read_status, tags. "
            "No deletion, no bulk action, no progress simulation, no enrichment. "
            + _APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=True),
    )
    async def forkos_bookmark_update(
        bookmark_id: str,
        collection: COLLECTION_VALUES | None = None,
        favorite: bool | None = None,
        read_status: READ_STATUS_VALUES | None = None,
        tags: Tags = None,
        expected_updated_at: str | None = None,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="forkos_bookmark_update",
            source="forkos",
            factory=lambda supplied: BookmarkUpdateIn(**_supplied_only(supplied, dict(
                bookmark_id=bookmark_id,
                collection=collection,
                favorite=favorite,
                read_status=read_status,
                tags=tags,
                expected_updated_at=expected_updated_at,
            ))),
            action=actions_svc.update_bookmark,
            ctx=ctx,
        )

    @server.tool(
        name="brain_capture",
        description=(
            "Capture a new knowledge note into the f0rknbrain Obsidian Vault (00 Inbox). Duable "
            "knowledge stays Vault-owned: no forkOS note rows are created. Optional relate_to "
            "stores relation metadata resolved server-side. " + _APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=False),
    )
    async def brain_capture(
        body: Annotated[str, Field(min_length=1, max_length=40000)],
        title: OptionalTitle = None,
        relate_to: str | None = None,
        tags: Tags = None,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="brain_capture",
            source="f0rknbrain",
            factory=lambda supplied: BrainCaptureIn(**_supplied_only(supplied, dict(
                body=body, title=title, relate_to=relate_to, tags=tags
            ))),
            action=actions_svc.capture_brain_note,
            ctx=ctx,
        )

    @server.tool(
        name="brain_save_to_entity",
        description=(
            "Append text to the forkOS-managed knowledge note of an entity, identified by "
            "forkos_id. The note is created if missing. Appends only - it never replaces the "
            "body - and user-owned Markdown and frontmatter are preserved. Unmanaged Obsidian "
            "notes cannot be written (no path input exists). " + _APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=False),
    )
    async def brain_save_to_entity(
        forkos_id: str,
        text: Annotated[str, Field(min_length=1, max_length=20000)],
        heading: Annotated[str | None, Field(max_length=200)] = None,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="brain_save_to_entity",
            source="f0rknbrain",
            factory=lambda supplied: BrainSaveToEntityIn(**_supplied_only(supplied, dict(
                forkos_id=forkos_id, text=text, heading=heading
            ))),
            action=actions_svc.save_to_entity_brain,
            ctx=ctx,
        )


# ---------------------------------------------------------------------------
# H2 sıcak hafıza araçları (90 Agent/Memory)
# ---------------------------------------------------------------------------

#: Sıcak hafıza girdi sınırları (§41) — şemada görünür.
# Sınırlar modele (ve dolayısıyla ayrıştırıcıya) bağlıdır: şemada, dokümanda ve
# çalışma zamanında AYNI sayı görünsün (§20/§25).
MemoryTags = Annotated[list[str] | None, Field(max_length=MAX_TAGS)]
RelatedIds = Annotated[list[str] | None, Field(max_length=MAX_RELATED)]
MemoryQuery = Annotated[str | None, Field(max_length=MAX_QUERY_LENGTH)]

_READ_ONLY_CLAUSE = "Read-only. Does not modify forkOS or the Vault."
_H2_APPROVAL_NOTE = (
    "Write operation; requires user approval when this MCP server is configured "
    "as untrusted. No external network calls."
)


def _hot_memory_read(factory: Callable[[], Any], source: str = "f0rknbrain"):
    """H2 okuma zarflaması: model-okunur hata, mutasyonsuz."""
    try:
        return AgentEnvelope(source=source, data=factory(), truncated=False)
    except actions_svc.ActionError as exc:
        raise ToolError(str(exc)) from exc
    except ValueError as exc:
        raise ToolError(f"HOT_MEMORY_INVALID: {exc}") from exc


def _register_hot_memory_tools(server: MCPServer) -> None:
    """5 H2 aracını kaydeder. Gövdeler incedir: mantık adaptördedir."""

    @server.tool(
        name="hot_memory_context",
        description=(
            "Return the small curated set of ACTIVE hot memories (profile, preferences, "
            "goals, constraints, decisions) useful for personalized reasoning. Bounded by "
            "item and character budget; expired and retired items are excluded. "
            + _READ_ONLY_CLAUSE
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def hot_memory_context(
        kinds: list[MemoryKindValue] | None = None,
    ) -> AgentEnvelope[HotMemoryContextData]:
        return _hot_memory_read(lambda: hm_svc.get_context(kinds))

    @server.tool(
        name="hot_memory_list",
        description=(
            "List or search hot memories for management and discovery (lexical query only). "
            "Includes retired and expired items when requested. " + _READ_ONLY_CLAUSE
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def hot_memory_list(
        kind: MemoryKindValue | None = None,
        effective_status: EffectiveStatusFilter = "active",
        query: MemoryQuery = None,
        limit: int = 20,
    ) -> AgentEnvelope[HotMemoryListData]:
        return _hot_memory_read(
            lambda: hm_svc.list_memories(
                kind=kind, effective_status=effective_status, query=query, limit=limit
            )
        )

    @server.tool(
        name="hot_memory_store",
        description=(
            "Create ONE approved hot memory item under 90 Agent/Memory. Server generates the "
            "UUID; no path is accepted. An exact duplicate (same kind + normalized text) "
            "returns status=noop instead of creating another file. Obvious credential material "
            "is rejected. " + _H2_APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=False),
    )
    async def hot_memory_store(
        kind: MemoryKindValue,
        title: Annotated[str, Field(min_length=1, max_length=MAX_TITLE)],
        text: Annotated[str, Field(min_length=1, max_length=MAX_TEXT)],
        source_mode: SourceModeValue,
        importance: Annotated[int, Field(ge=1, le=3)] = 2,
        expires_at: str | None = None,
        related_forkos_ids: RelatedIds = None,
        tags: MemoryTags = None,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="hot_memory_store",
            source="f0rknbrain",
            factory=lambda supplied: HotMemoryStoreIn(
                **_supplied_only(
                    supplied,
                    dict(
                        kind=kind,
                        title=title,
                        text=text,
                        source_mode=source_mode,
                        importance=importance,
                        expires_at=expires_at,
                        related_forkos_ids=related_forkos_ids or [],
                        tags=tags or [],
                    ),
                )
            ),
            action=hm_svc.store_memory,
            ctx=ctx,
        )

    @server.tool(
        name="hot_memory_update",
        description=(
            "Correct or refine ONE existing hot memory. Requires expected_revision (sha256 of "
            "the current file); a stale revision fails with HOT_MEMORY_STALE and changes "
            "nothing. An omitted field is preserved; an explicit null clears expiry. Status "
            "changes use hot_memory_retire. " + _H2_APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=True),
    )
    async def hot_memory_update(
        memory_id: str,
        expected_revision: Annotated[
            str, Field(min_length=MAX_REVISION_LENGTH, max_length=MAX_REVISION_LENGTH)
        ],
        kind: MemoryKindValue | None = None,
        title: Annotated[str | None, Field(max_length=MAX_TITLE)] = None,
        text: Annotated[str | None, Field(max_length=MAX_TEXT)] = None,
        importance: Annotated[int | None, Field(ge=1, le=3)] = None,
        expires_at: str | None = None,
        related_forkos_ids: RelatedIds = None,
        tags: MemoryTags = None,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="hot_memory_update",
            source="f0rknbrain",
            factory=lambda supplied: HotMemoryUpdateIn(
                **_supplied_only(
                    supplied,
                    dict(
                        memory_id=memory_id,
                        expected_revision=expected_revision,
                        kind=kind,
                        title=title,
                        text=text,
                        importance=importance,
                        expires_at=expires_at,
                        related_forkos_ids=related_forkos_ids,
                        tags=tags,
                    ),
                )
            ),
            action=hm_svc.update_memory,
            ctx=ctx,
        )

    @server.tool(
        name="hot_memory_retire",
        description=(
            "Stop using ONE hot memory while preserving historical evidence: status becomes "
            "retired and the item leaves active context. This is NOT deletion - the Markdown "
            "file and its Git history remain. Requires expected_revision. "
            + _H2_APPROVAL_NOTE
        ),
        annotations=_write_annotations(idempotent=True),
    )
    async def hot_memory_retire(
        memory_id: str,
        expected_revision: Annotated[str, Field(min_length=64, max_length=64)],
        reason: Annotated[str | None, Field(max_length=240)] = None,
        ctx: Context | None = None,
    ) -> AgentEnvelope[ActionReceipt]:
        return await _run_write(
            tool="hot_memory_retire",
            source="f0rknbrain",
            factory=lambda supplied: HotMemoryRetireIn(
                **_supplied_only(
                    supplied,
                    dict(
                        memory_id=memory_id,
                        expected_revision=expected_revision,
                        reason=reason,
                    ),
                )
            ),
            action=hm_svc.retire_memory,
            ctx=ctx,
        )


# ---------------------------------------------------------------------------
# H3 kanıt getirme aracı (salt-okunur)
# ---------------------------------------------------------------------------

#: H3 girdi sınırları (§15/§164) — şemada GÖRÜNÜR, yürütmede bağımsız dayatılır.
EvidenceQuery = Annotated[
    str, Field(min_length=ev_models.MIN_QUERY_LENGTH, max_length=ev_models.MAX_QUERY_LENGTH)
]
EvidenceDepth = Annotated[
    int, Field(ge=ev_models.MIN_EVIDENCE_DEPTH, le=ev_models.MAX_EVIDENCE_DEPTH)
]
EvidenceLimit = Annotated[
    int, Field(ge=ev_models.MIN_EVIDENCE_LIMIT, le=ev_models.MAX_EVIDENCE_LIMIT)
]


def _register_evidence_tool(server: MCPServer) -> None:
    """H3'ün TEK genel aracını kaydeder (§12/§13).

    Neden tek araç: H0 zaten `forkos_search`, `forkos_entity_context`,
    `forkos_project_context`, `forkos_recent_activity`, `brain_search` ve
    `brain_read` sağlıyor. H3 mikro-araçları çoğaltmaz; bu araç bu alanları
    birleştiren SINIRLI orkestrasyon katmanıdır.
    """

    @server.tool(
        name="forkos_evidence",
        description=(
            "Retrieve inspectable evidence for a question or claim from forkOS operational "
            "state (entities, links, append-only events) and the f0rknbrain Vault (managed "
            "notes, one hop of wikilinks/backlinks, deterministic lexical matches). Returns an "
            "EvidenceBundle with per-item provenance locators, relation paths, a factual "
            "retrieval trace and honest truncation flags. Structure first: with an explicit "
            "entity_id the canonical Link graph and Event history are traversed under hard "
            "budgets; without one, only lexical candidates are returned and nothing is "
            "expanded. Read-only: creates no entity, link, event or file and never modifies the "
            "Vault. No model calls and no answer generation - forkOS retrieves evidence, the "
            "caller reasons over it. Curated hot memory is personalization context, not "
            "evidence, and is never returned here. " + _READ_ONLY_CLAUSE
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def forkos_evidence(
        query: EvidenceQuery,
        entity_id: str | None = None,
        scope: ev_models.EvidenceScope = "all",
        since: str | None = None,
        until: str | None = None,
        max_depth: EvidenceDepth = ev_models.DEFAULT_EVIDENCE_DEPTH,
        limit: EvidenceLimit = ev_models.DEFAULT_EVIDENCE_LIMIT,
    ) -> AgentEnvelope[ev_models.EvidenceBundle]:
        try:
            async with SessionLocal() as session:
                bundle = await ev_svc.retrieve_evidence(
                    session,
                    query=query,
                    entity_id=entity_id,
                    scope=scope,
                    since=since,
                    until=until,
                    max_depth=max_depth,
                    limit=limit,
                )
            return AgentEnvelope(source="forkos", data=bundle, truncated=bundle.truncated)
        except ev_svc.EvidenceError as exc:
            raise ToolError(str(exc)) from exc
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - sızıntısız hata zarfı (§127)
            raise ToolError(f"EVIDENCE_UNAVAILABLE: {type(exc).__name__}") from exc


# ---------------------------------------------------------------------------
# H4 yerel bilis aracı (salt-okunur, yalnız loopback model çağrısı)
# ---------------------------------------------------------------------------

#: H4 girdi sınırları (§29) — şemada GÖRÜNÜR, yürütmede bağımsız dayatılır.
LocalCognitionText = Annotated[
    str, Field(min_length=lc_models.MIN_TEXT_CHARS, max_length=lc_models.MAX_TEXT_CHARS)
]
LocalCognitionLabelItem = Annotated[
    str,
    Field(min_length=lc_models.MIN_LABEL_CHARS, max_length=lc_models.MAX_LABEL_CHARS),
]
LocalCognitionLabels = Annotated[
    list[LocalCognitionLabelItem] | None,
    Field(min_length=lc_models.MIN_LABELS, max_length=lc_models.MAX_LABELS),
]
LocalCognitionProtectedItem = Annotated[
    str,
    Field(
        min_length=lc_models.MIN_PROTECTED_TERM_CHARS,
        max_length=lc_models.MAX_PROTECTED_TERM_CHARS,
    ),
]
LocalCognitionProtectedTerms = Annotated[
    list[LocalCognitionProtectedItem] | None, Field(max_length=lc_models.MAX_PROTECTED_TERMS)
]
LocalCognitionGoal = Annotated[
    str | None, Field(max_length=lc_models.MAX_CLASSIFICATION_GOAL_CHARS)
]

#: H4'ün ağ sözleşmesi H0-H3'ten FARKLIDIR: yalnızca loopback model trafiği
#: vardır, dış ağ çağrısı yoktur.
_H4_NETWORK_NOTE = (
    "Model execution happens only through the configured loopback provider "
    "(localhost/127.0.0.1/::1); no external network calls are made and no remote "
    "model is ever contacted by forkOS."
)


def _register_local_cognition_tool(server: MCPServer) -> None:
    """H4'ün TEK aracını kaydeder (§24).

    Taşıma düz argümanlarla yapılır (MCP istemcileri için en güvenilir biçim);
    ayrık lane isteği handler içinde kurulur ve çalışma zamanında doğrulanır
    (§28: taşıma doğruluğu, şema estetiğinden önce gelir).
    """

    @server.tool(
        name="forkos_local_cognition",
        description=(
            "Run ONE explicitly chosen local cognition primitive through the configured "
            "loopback model: classify (pick one supplied label), structured_extract (named "
            "versioned contract: academic_calendar_v1, weekly_schedule_v1, "
            "deadline_candidates_v1) or query_rewrite (bounded retrieval rewrite that keeps "
            "protected terms verbatim). The lane is mandatory: this tool does not decide what "
            "kind of work to do, it executes the primitive you asked for. Model output is a "
            "proposal only - every result passes deterministic validation, and failures are "
            "retried within hard bounds (small 2 attempts, medium 1) before returning "
            "status=needs_escalation. The caller supplies all text; this tool never reads the "
            "Vault, the database, Hot Memory or evidence, and it never writes anything. "
            "deferred/unsupported lanes (rerank, compress, reason, chat, answer, plan) are "
            "rejected. " + _H4_NETWORK_NOTE
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def forkos_local_cognition(
        lane: lc_models.Lane,
        text: LocalCognitionText,
        contract: lc_models.ExtractionContractName | None = None,
        labels: LocalCognitionLabels = None,
        classification_goal: LocalCognitionGoal = None,
        protected_terms: LocalCognitionProtectedTerms = None,
    ) -> lc_models.LocalCognitionResponse:
        try:
            request = lc_models.build_lane_request(
                lane=lane,
                text=text,
                contract=contract,
                labels=labels,
                classification_goal=classification_goal,
                protected_terms=protected_terms,
            )
            return await lc_svc.run_local_cognition(request)
        except lc_models.H4Error as exc:
            raise ToolError(str(exc)) from exc
        except ValidationError as exc:
            raise ToolError(f"INVALID_ARGUMENT: {_first_validation_error(exc)}") from exc
        except Exception as exc:  # noqa: BLE001 - sızıntısız hata zarfı
            raise ToolError(f"LOCAL_COGNITION_FAILED: {type(exc).__name__}") from exc


# ---------------------------------------------------------------------------
# H5 gözden geçirme zekâsı aracı (salt-okunur)
# ---------------------------------------------------------------------------

#: H5 girdi sınırları (§20) — şemada GÖRÜNÜR, yürütmede bağımsız dayatılır.
ReviewReferenceDate = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
ReviewFocusEntity = Annotated[str, Field(max_length=ri_models.MAX_FOCUS_ENTITY_LEN)]


def _register_review_intelligence_tool(server: MCPServer) -> None:
    """H5'in TEK aracını kaydeder (§15).

    Beş mod, tek araç: mikro-araç çoğaltması (`forkos_weekly_summary`,
    `forkos_consolidate`, ...) YOKTUR.
    """

    @server.tool(
        name="forkos_review_intelligence",
        description=(
            "Bounded, read-only reflection over existing forkOS state: where you left off "
            "(continuity), what changed between two moments (period_delta), the daily close, "
            "the weekly delta review, and consolidation candidates. Modes: continuity, "
            "daily_close, weekly_review, period_delta, consolidation_review. Every factual "
            "insight carries source references and a source manifest; promotion, knowledge-health "
            "and resurfacing outputs are CANDIDATES, never truth. This tool writes nothing: no "
            "Review, Todo, Entity, Link, Event, Vault or Hot Memory mutation, and no automatic "
            "summary storage. It reuses the existing Review preview, canonical deadlines and H3 "
            "evidence; local model assistance (H4) is optional and degrades to deterministic "
            "output when unavailable. " + _READ_ONLY_CLAUSE
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def forkos_review_intelligence(
        mode: ri_models.ReviewMode,
        since: str | None = None,
        until: str | None = None,
        reference_date: ReviewReferenceDate | None = None,
        focus_entity_id: ReviewFocusEntity | None = None,
        include_knowledge: bool = True,
    ) -> ri_models.ReviewIntelligenceResponse:
        try:
            async with SessionLocal() as session:
                return await ri_svc.review_intelligence(
                    session,
                    mode=mode,
                    since=since,
                    until=until,
                    reference_date=reference_date,
                    focus_entity_id=focus_entity_id,
                    include_knowledge=include_knowledge,
                )
        except ri_models.ReviewIntelligenceError as exc:
            raise ToolError(str(exc)) from exc
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - sızıntısız hata zarfı
            raise ToolError(f"REVIEW_INTELLIGENCE_FAILED: {type(exc).__name__}") from exc


# ---------------------------------------------------------------------------
# H6 proaktivite kontrol aracı (inceleme + kullanıcı override'i)
# ---------------------------------------------------------------------------

#: H6'nın KAPALI işlem kümesi: genel bir otomasyon yürütücüsü DEĞİL (§103).
ProactivityOperation = Literal[
    "status", "configure", "rule_set", "snooze", "unsnooze", "history", "evaluate_now"
]

#: `configure` icin KAPALI alt anahtar kumesi (serbest anahtar-deger YOK).
PROACTIVITY_CONFIG_KEYS = frozenset(
    {"quiet_hours_start", "quiet_hours_end", "focus_deferral_enabled", "digest_time"}
)

ProactivityKind = Annotated[str, Field(max_length=48)]
ProactivityUntil = Annotated[str, Field(max_length=40)]


def _register_proactivity_tool(server: MCPServer) -> None:
    """H6'nın TEK aracını kaydeder (§101).

    Araç H6'nın kendi konfigurasyon/override durumunu yazabilir; canonical
    domain kayıtlarına (Todo/Project/Opportunity/Vault/Hot Memory/Review)
    ASLA dokunmaz.
    """

    @server.tool(
        name="forkos_proactivity",
        description=(
            "Inspect and control WHEN forkOS proactively comes to you. This is the attention "
            "layer, not an automation engine: operations are status, configure, rule_set, "
            "snooze, unsnooze, history and evaluate_now. Rule kinds are a CLOSED set "
            "(morning_continuity, daily_close, weekly_review, deadline_staircase, "
            "continuity_gap, project_stalled); arbitrary expressions, cron strings, prompts, "
            "SQL or tool names are rejected. Silence is a successful outcome: a trigger only "
            "means 'evaluate now', never 'notify now'. snooze takes an absolute timezone-aware "
            "timestamp and is an explicit user override that automation always respects. "
            "Writes are limited to proactivity configuration and override state - this tool "
            "never mutates Todos, Projects, Opportunities, Reviews, the Vault or Hot Memory, "
            "and the background worker never performs canonical mutations."
        ),
        annotations=PROACTIVITY_ANNOTATIONS,
    )
    async def forkos_proactivity(
        operation: ProactivityOperation,
        kind: ProactivityKind | None = None,
        enabled: bool | None = None,
        config: dict | None = None,
        run_id: int | None = None,
        until: ProactivityUntil | None = None,
        limit: int | None = None,
    ) -> dict:
        from app.modules.proactivity import service as proactivity_service

        try:
            async with SessionLocal() as session:
                if operation == "status":
                    return await proactivity_service.status(session)
                if operation == "configure":
                    supplied = config or {}
                    unknown = set(supplied) - PROACTIVITY_CONFIG_KEYS
                    if unknown:
                        raise proactivity_service.ProactivityError(
                            "UNKNOWN_CONFIG_FIELD",
                            f"bilinmeyen ayar alani: {sorted(unknown)}",
                        )
                    await proactivity_service.configure(
                        session,
                        enabled=enabled,
                        quiet_hours_start=supplied.get("quiet_hours_start"),
                        quiet_hours_end=supplied.get("quiet_hours_end"),
                        focus_deferral_enabled=supplied.get("focus_deferral_enabled"),
                        digest_time=supplied.get("digest_time"),
                    )
                    await session.commit()
                    # Ayni islem TEK sekil dondurur: REST `configure` da durum
                    # semasini doner, boylece iki yuzey ayrisamaz.
                    return await proactivity_service.status(session)
                if operation == "rule_set":
                    if not kind:
                        raise proactivity_service.ProactivityError(
                            "INVALID_ARGUMENT", "rule_set icin 'kind' gerekli"
                        )
                    rule = await proactivity_service.rule_set(
                        session, kind=kind, enabled=enabled, config=config
                    )
                    await session.commit()
                    return {
                        "kind": rule.kind,
                        "enabled": rule.enabled,
                        "config": rule.config,
                        "snoozed_until": rule.snoozed_until.isoformat()
                        if rule.snoozed_until
                        else None,
                    }
                if operation == "snooze":
                    if until is None:
                        raise proactivity_service.ProactivityError(
                            "INVALID_ARGUMENT", "snooze icin 'until' gerekli"
                        )
                    moment = datetime.fromisoformat(until)
                    await proactivity_service.snooze(
                        session, until=moment, run_id=run_id, kind=kind
                    )
                    await session.commit()
                    return {"snoozed": True, "until": moment.isoformat()}
                if operation == "unsnooze":
                    await proactivity_service.unsnooze(session, run_id=run_id, kind=kind)
                    await session.commit()
                    return {"snoozed": False}
                if operation == "history":
                    return {"runs": await proactivity_service.history(session, limit=limit or 20)}
                if operation == "evaluate_now":
                    result = await proactivity_service.tick(session)
                    return {
                        "evaluated": result.evaluated,
                        "candidates": result.candidates,
                        "surfaced": result.surfaced,
                        "digested": result.digested,
                        "deferred": result.deferred,
                        "suppressed": result.suppressed,
                        "cancelled": result.cancelled,
                        "failed": result.failed,
                    }
                raise proactivity_service.ProactivityError(
                    "UNKNOWN_OPERATION", f"bilinmeyen islem: {operation}"
                )
        except proactivity_service.ProactivityError as exc:
            raise ToolError(str(exc)) from exc
        except ValueError as exc:
            raise ToolError(f"INVALID_ARGUMENT: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - sızıntısız hata zarfı
            raise ToolError(f"PROACTIVITY_FAILED: {type(exc).__name__}") from exc
