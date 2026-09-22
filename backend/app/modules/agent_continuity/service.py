"""A2 Context Composition Service.

Kanonik kaynaklar (forkOS PostgreSQL, H2, H5, f0rknbrain Vault) açısından
tamamen salt-okunur (read-only) çalışır.
Oturum içi bütçe ve kaynak referanslarını ephemeral destek tablolarına kaydeder.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.modules.agent_continuity.models import AgentSessionContext, AgentSessionSource
from app.modules.agent_continuity.renderer import (
    render_bootstrap_context,
    render_continuity_context,
)
from app.modules.agent_continuity.schemas import (
    BootstrapContinuity,
    BootstrapDiagnostics,
    BootstrapHotMemory,
    BootstrapIdentity,
    BootstrapPacketV1,
    BootstrapSourceRef,
    OperationalDeadline,
    OperationalProject,
    OperationalState,
    ContinuityStatusOut,
)
from app.modules.agent_lifecycle.models import AgentSession
from app.modules.execution.models import ExecutionPlan
from app.modules.project.models import Project
from app.modules.todo.models import Todo

LOGGER = logging.getLogger("forkos.agent_continuity")

MAX_RENDER_CHAR_BUDGET = 4000
DEFAULT_TTL_MINUTES = 60
MAX_DELIVERED_SOURCES = 5


async def _collect_identity(session: AsyncSession) -> tuple[BootstrapIdentity, list[str]]:
    """Kullanıcı ilkelerini ve kalıcı tercihleri f0rknbrain / H2 üzerinden seçer."""
    degraded: list[str] = []
    conventions = [
        "Kullanıcı Türkçe konuşur; kod ve değişkenler İngilizce, açıklamalar Türkçe olmalı.",
        "Local-only çalış: harici telemetri veya bulut modeli çağrısı yok.",
        "Kullanıcı onayı olmadan kanonik operasyonel verileri doğrudan mutate etme.",
    ]
    preferences: list[str] = []
    corrections: list[str] = []
    goals: list[str] = []

    try:
        from app.integrations.agent import hot_memory as h2_svc
        ctx = h2_svc.get_context(kinds=["profile", "preference", "constraint", "goal"])
        for p in ctx.preferences[:3]:
            preferences.append(p.title)
        for c in ctx.constraints[:2]:
            conventions.append(c.title)
        for g in ctx.goals[:2]:
            goals.append(g.title)
    except Exception as exc:
        LOGGER.warning("H2 hot memory read degraded in bootstrap: %s", exc)
        degraded.append("HOT_MEMORY_UNAVAILABLE")

    return BootstrapIdentity(
        interaction_conventions=conventions[:3],
        durable_preferences=preferences[:4],
        explicit_corrections=corrections[:3],
        long_running_goals=goals[:3],
    ), degraded


async def _collect_operational_projects(session: AsyncSession, limit: int = 5) -> list[OperationalProject]:
    """Aktif projeleri çeker."""
    stmt = (
        select(Project, Entity.title)
        .join(Entity, Entity.id == Project.id)
        .where(Project.status != "completed", Entity.archived_at.is_(None))
        .order_by(Project.position.asc(), Project.last_activity_at.desc().nulls_last())
        .limit(limit)
    )
    res = await session.execute(stmt)
    projects: list[OperationalProject] = []
    for proj, title in res.all():
        projects.append(
            OperationalProject(
                id=str(proj.id),
                title=title,
                status=proj.status,
                next_action=proj.next_action,
            )
        )
    return projects


async def _collect_operational_deadlines(session: AsyncSession, limit: int = 5) -> list[OperationalDeadline]:
    """Yaklaşan son tarihleri çeker."""
    from app.core.deadlines import collect_deadlines

    raw = await collect_deadlines(session, limit=limit)
    deadlines: list[OperationalDeadline] = []
    for d in raw:
        due = d.get("due_at")
        due_str = due.isoformat() if hasattr(due, "isoformat") else str(due) if due else None
        deadlines.append(
            OperationalDeadline(
                id=str(d.get("entity_id") or ""),
                title=d.get("title", ""),
                due_at=due_str,
                remaining_days=d.get("remaining_days"),
                entity_type=d.get("type", "todo"),
            )
        )
    return deadlines


async def _collect_operational_decisions(session: AsyncSession, limit: int = 3) -> tuple[int, list[str]]:
    """Bekleyen H7 kararlarını sayar ve özetler."""
    stmt = (
        select(ExecutionPlan.id, ExecutionPlan.title, ExecutionPlan.state)
        .where(ExecutionPlan.state.in_(["draft", "ready_for_review", "input_required"]))
        .order_by(ExecutionPlan.created_at.desc())
        .limit(limit)
    )
    res = await session.execute(stmt)
    rows = res.all()
    count_stmt = select(func.count()).select_from(ExecutionPlan).where(
        ExecutionPlan.state.in_(["draft", "ready_for_review", "input_required"])
    )
    total = await session.scalar(count_stmt) or 0
    summaries = [f"{title} ({state})" for _, title, state in rows]
    return total, summaries


async def _collect_continuity(session: AsyncSession) -> tuple[BootstrapContinuity, list[str]]:
    """H5 süreklilik analizini çalıştırır."""
    degraded: list[str] = []
    try:
        from app.integrations.review_intelligence.continuity import build_continuity
        from app.integrations.review_intelligence.models import Collector

        collector = Collector()
        bundle, _ = await build_continuity(
            session,
            collector,
            since=None,
            until=None,
            focus_entity_id=None,
            include_knowledge=False,
        )

        last_act = None
        if bundle.last_meaningful_activity:
            verb = bundle.last_meaningful_activity.get("verb", "")
            title = bundle.last_meaningful_activity.get("title", "")
            last_act = f"{verb}: {title}" if title else verb

        recent = [c.text for c in bundle.recent_completed[:3]]
        threads = [t.title for t in bundle.active_threads[:3]]
        stalled = [p.text for p in bundle.stalled_projects[:2]]

        return BootstrapContinuity(
            anchor_timestamp=bundle.anchor.timestamp,
            anchor_kind=bundle.anchor.kind,
            activity_gap_hours=bundle.activity_gap_hours,
            last_meaningful_activity=last_act,
            recent_completed=recent,
            active_threads=threads,
            stalled_projects=stalled,
        ), degraded
    except Exception as exc:
        LOGGER.warning("H5 continuity read degraded in bootstrap: %s", exc)
        degraded.append("CONTINUITY_UNAVAILABLE")
        return BootstrapContinuity(), degraded


async def _collect_hot_memory(session: AsyncSession) -> tuple[list[dict[str, Any]], list[str]]:
    """H2 sıcak hafızadan bütçeli öğeleri seçer."""
    degraded: list[str] = []
    items: list[dict[str, Any]] = []
    try:
        from app.integrations.agent import hot_memory as h2_svc
        ctx = h2_svc.get_context()
        for p in ctx.profile[:1]:
            items.append({"kind": "profile", "title": p.title, "text": p.text, "memory_id": p.memory_id})
        for c in ctx.constraints[:2]:
            items.append({"kind": "constraint", "title": c.title, "text": c.text, "memory_id": c.memory_id})
        for g in ctx.goals[:2]:
            items.append({"kind": "goal", "title": g.title, "text": g.text, "memory_id": g.memory_id})
        for d in ctx.decisions[:1]:
            items.append({"kind": "decision", "title": d.title, "text": d.text, "memory_id": d.memory_id})
    except Exception as exc:
        LOGGER.warning("H2 hot memory items degraded: %s", exc)
        degraded.append("HOT_MEMORY_UNAVAILABLE")
    return items[:6], degraded


async def compose_first_turn_bootstrap(
    session: AsyncSession,
    session_row: AgentSession,
    turn_id: int | None = None,
    scope_project: str | None = None,
) -> tuple[BootstrapPacketV1, list[BootstrapSourceRef], str]:
    """İlk tur için bounded, kaynak kökenli BootstrapPacketV1 bağlamı üretir."""
    start_time = time.monotonic()
    degraded_reasons: list[str] = []

    # 1. Bilgi ve kasa sağlığı kontrolü (hızlı O(1) erişim kontrolü, os.walk taraması yapmaz)
    try:
        from app.integrations.agent.knowledge import is_vault_accessible
        if not is_vault_accessible():
            degraded_reasons.append("VAULT_UNAVAILABLE")
    except Exception:
        degraded_reasons.append("VAULT_UNAVAILABLE")

    # 2. Kaynak ailelerini topla (read-only)
    identity, id_deg = await _collect_identity(session)
    degraded_reasons.extend(id_deg)

    projects = (await _collect_operational_projects(session, limit=5))[:5]
    deadlines = (await _collect_operational_deadlines(session, limit=5))[:5]
    open_todos_count = await session.scalar(
        select(func.count()).select_from(Todo).where(Todo.status != "done")
    ) or 0
    pending_dec_count, pending_dec_summary = await _collect_operational_decisions(session, limit=3)

    op_state = OperationalState(
        active_projects=projects,
        upcoming_deadlines=deadlines,
        open_todos_count=open_todos_count,
        pending_decisions_count=pending_dec_count,
        pending_decisions_summary=pending_dec_summary[:3],
    )

    continuity, cont_deg = await _collect_continuity(session)
    degraded_reasons.extend(cont_deg)

    hot_items, hot_deg = await _collect_hot_memory(session)
    degraded_reasons.extend(hot_deg)

    # 3. Kaynak referansları oluştur (en fazla 5 grup)
    sources: list[BootstrapSourceRef] = []
    for proj in projects[:2]:
        sources.append(
            BootstrapSourceRef(
                source_id=f"entity:{proj.id}",
                source_type="project",
                scope_project=proj.id,
                title=proj.title[:128] if proj.title else None,
            )
        )
    for dead in deadlines[:2]:
        sources.append(
            BootstrapSourceRef(
                source_id=f"entity:{dead.id}",
                source_type="deadline",
                title=dead.title[:128] if dead.title else None,
            )
        )
    for h in hot_items[:1]:
        mem_id = h.get("memory_id")
        if mem_id:
            raw_title = h.get("title")
            sources.append(
                BootstrapSourceRef(
                    source_id=f"hot_memory:{mem_id}",
                    source_type="hot_memory",
                    title=raw_title[:128] if raw_title else None,
                )
            )

    sources = sources[:MAX_DELIVERED_SOURCES]

    # 4. İlk render ve katı bütçe kırpması
    packet = BootstrapPacketV1(
        schema_version=1,
        session_key=session_row.session_key,
        generated_at=datetime.now(UTC).isoformat(),
        is_first_turn=True,
        identity=identity,
        operational_state=op_state,
        continuity=continuity,
        hot_memory=BootstrapHotMemory(items=hot_items),
        sources=sources,
        diagnostics=BootstrapDiagnostics(
            available=True,
            truncated=False,
            omitted_count=0,
            degraded_reasons=sorted(set(degraded_reasons)),
            generation_ms=round((time.monotonic() - start_time) * 1000, 2),
        ),
    )

    rendered = render_bootstrap_context(packet)
    omitted = 0

    # Bütçe aşıldıysa öncelik sırasına göre kırp (identity korunur!)
    while len(rendered) > MAX_RENDER_CHAR_BUDGET:
        if packet.hot_memory.items:
            packet.hot_memory.items.pop()
            omitted += 1
        elif len(packet.operational_state.active_projects) > 1:
            packet.operational_state.active_projects.pop()
            omitted += 1
        elif packet.continuity.recent_completed:
            packet.continuity.recent_completed.pop()
            omitted += 1
        elif packet.continuity.active_threads:
            packet.continuity.active_threads.pop()
            omitted += 1
        else:
            break
        rendered = render_bootstrap_context(packet)

    if omitted > 0:
        packet.diagnostics.truncated = True
        packet.diagnostics.omitted_count = omitted

    # 5. Ephemeral destek tablolarına kaydet (bağımsız transaction)
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=DEFAULT_TTL_MINUTES)

    ctx_row = AgentSessionContext(
        session_id=session_row.id,
        turn_id=turn_id,
        schema_version=1,
        is_first_turn=True,
        item_count=len(packet.operational_state.active_projects) + len(packet.operational_state.upcoming_deadlines) + len(packet.hot_memory.items),
        char_count=len(rendered),
        truncated=packet.diagnostics.truncated,
        omitted_count=packet.diagnostics.omitted_count,
        degraded_reasons=packet.diagnostics.degraded_reasons,
        created_at=now,
    )
    session.add(ctx_row)

    for s in sources:
        stmt = insert(AgentSessionSource).values(
            session_id=session_row.id,
            turn_id=turn_id,
            source_id=s.source_id,
            source_type=s.source_type,
            source_version=s.source_version,
            scope_project=s.scope_project,
            topic_signature="initial_bootstrap",
            delivered_at=now,
            expires_at=expires_at,
        ).on_conflict_do_update(
            constraint="uq_agent_session_source_identity",
            set_={
                "delivered_at": now,
                "expires_at": expires_at,
                "turn_id": turn_id,
            }
        )
        await session.execute(stmt)

    await session.commit()
    return packet, sources, rendered


AMBIGUOUS_PATTERNS = [
    "bunu biraz aç", "bunu ac", "bunu aç", "bunu açıkla", "bunu acikla",
    "bunu detaylandır", "bunu detaylandir", "biraz daha aç", "biraz daha ac",
    "bunu detaylandırır mısın", "bunu detaylandirir misin",
    "daha detaylı", "daha detayli", "daha fazla detay",
    "onu da karşılaştır", "onu da karsilastir", "karşılaştır", "karsilastir",
    "peki bunun", "peki bunun diğerinden farkı", "peki bunun digerinden farki",
    "farkı ne", "farki ne",
    "önceki kaynağa göre", "onceki kaynaga gore", "önceki kaynak", "onceki kaynak",
    "buna göre", "buna gore", "ondan bahset", "ondan bahset biraz",
    "hangisi daha iyi", "peki ya", "neden peki",
    "expand on this", "tell me more", "explain further", "compare that",
    "what about that", "what did you mean", "go on", "elaborate", "more details",
]


def _is_ambiguous_continuation(prompt: str) -> bool:
    if not prompt:
        return False
    p = prompt.strip().lower()
    for pat in AMBIGUOUS_PATTERNS:
        if pat in p:
            return True
    if len(p) < 60:
        words = p.split()
        if any(w in {"bunu", "bunun", "bunda", "bundan", "onu", "onun", "onda", "ondan", "this", "that", "these", "it"} for w in words):
            return True
    return False


def _extract_candidate_keywords(prompt: str) -> list[str]:
    words = re.findall(r"\b[\w-]+\b", prompt)
    stop_words = {
        "ile", "icin", "için", "olan", "nedir", "nelerdir", "nasil", "nasıl",
        "durum", "son", "ilgili", "hakkında", "hakkinda", "proje", "projesi",
        "gorev", "görev", "yeni", "bir", "ve", "veya", "ama", "fakat", "the",
        "and", "about", "what", "project", "task", "show", "tell", "give", "list"
    }
    candidates = [w for w in words if len(w) >= 3 and w.lower() not in stop_words]
    return candidates


async def compose_later_turn_context(
    session: AsyncSession,
    session_row: AgentSession,
    transient_prompt: str,
    turn_id: int | None = None,
    scope_project: str | None = None,
) -> tuple[BootstrapPacketV1 | None, list[BootstrapSourceRef], str | None, list[str]]:
    """Sonraki turlar için kaynak devamlılığı veya sınırlandırılmış sorgu bağlamı üretir.

    Transient prompt asla veritabanına, loglara veya kasaya kaydedilmez.
    """
    now = datetime.now(UTC)
    degraded_reasons: list[str] = []

    # 1. Ambiguous follow-up kontrolü
    if _is_ambiguous_continuation(transient_prompt):
        stmt = (
            select(AgentSessionSource)
            .where(
                AgentSessionSource.session_id == session_row.id,
                AgentSessionSource.expires_at > now,
            )
            .order_by(AgentSessionSource.delivered_at.desc())
            .limit(MAX_DELIVERED_SOURCES)
        )
        res = await session.execute(stmt)
        source_rows = res.scalars().all()

        if source_rows:
            sources: list[BootstrapSourceRef] = []
            for r in source_rows:
                title = None
                if r.source_id.startswith("entity:"):
                    try:
                        ent_id_str = r.source_id.split(":", 1)[1]
                        ent_uuid = uuid.UUID(ent_id_str)
                        title = await session.scalar(select(Entity.title).where(Entity.id == ent_uuid))
                    except Exception:
                        pass
                sources.append(
                    BootstrapSourceRef(
                        source_id=r.source_id,
                        source_type=r.source_type,
                        source_version=r.source_version,
                        scope_project=r.scope_project,
                        title=title[:128] if title else None,
                    )
                )

            rendered = render_continuity_context(sources)

            ctx_row = AgentSessionContext(
                session_id=session_row.id,
                turn_id=turn_id,
                schema_version=1,
                is_first_turn=False,
                item_count=len(sources),
                char_count=len(rendered),
                truncated=False,
                omitted_count=0,
                degraded_reasons=[],
                created_at=now,
            )
            session.add(ctx_row)
            await session.commit()
            return None, sources, rendered, degraded_reasons

        # Süresi dolmuş veya önceki kaynak yok
        return None, [], None, ["EXPIRED_OR_NO_CONTINUITY_SOURCES"]

    # 2. Açık konu değişimi veya yeni sorgu (Topic Shift)
    # Eski kaynakları geçersiz kıl (invalidate/reset)
    await session.execute(
        delete(AgentSessionSource).where(AgentSessionSource.session_id == session_row.id)
    )

    # Yeni sorgu için sınırlandırılmış yerel arama yap
    from app.integrations.agent.context import search_operational_context

    candidates = _extract_candidate_keywords(transient_prompt)
    new_sources: list[BootstrapSourceRef] = []

    for candidate in candidates[:3]:
        try:
            results = await search_operational_context(session, query=candidate, limit=3)
            for ent in results:
                new_sources.append(
                    BootstrapSourceRef(
                        source_id=f"entity:{ent.id}",
                        source_type=ent.type,
                        title=ent.title[:128] if ent.title else None,
                    )
                )
            if new_sources:
                break
        except Exception as exc:
            LOGGER.debug("search_operational_context failed for '%s': %s", candidate, exc)

    new_sources = new_sources[:MAX_DELIVERED_SOURCES]
    rendered = None
    if new_sources:
        rendered = render_continuity_context(new_sources)
        expires_at = now + timedelta(minutes=DEFAULT_TTL_MINUTES)
        for s in new_sources:
            stmt = insert(AgentSessionSource).values(
                session_id=session_row.id,
                turn_id=turn_id,
                source_id=s.source_id,
                source_type=s.source_type,
                source_version=s.source_version,
                scope_project=s.scope_project,
                topic_signature="query_retrieval",
                delivered_at=now,
                expires_at=expires_at,
            ).on_conflict_do_update(
                constraint="uq_agent_session_source_identity",
                set_={
                    "delivered_at": now,
                    "expires_at": expires_at,
                    "turn_id": turn_id,
                }
            )
            await session.execute(stmt)

    ctx_row = AgentSessionContext(
        session_id=session_row.id,
        turn_id=turn_id,
        schema_version=1,
        is_first_turn=False,
        item_count=len(new_sources),
        char_count=len(rendered) if rendered else 0,
        truncated=False,
        omitted_count=0,
        degraded_reasons=degraded_reasons,
        created_at=now,
    )
    session.add(ctx_row)
    await session.commit()

    return None, new_sources, rendered, degraded_reasons


async def status(session: AsyncSession) -> ContinuityStatusOut:
    """Devamlılık ve bağlam oluşturma tanılamalarını döner."""
    now = datetime.now(UTC)
    last_bootstrap = await session.scalar(
        select(AgentSessionContext.created_at)
        .where(AgentSessionContext.is_first_turn.is_(True))
        .order_by(AgentSessionContext.created_at.desc())
        .limit(1)
    )
    last_harness_row = (await session.execute(
        select(AgentSession.harness)
        .join(AgentSessionContext, AgentSessionContext.session_id == AgentSession.id)
        .order_by(AgentSessionContext.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    active_sources = await session.scalar(
        select(func.count())
        .select_from(AgentSessionSource)
        .where(AgentSessionSource.expires_at > now)
    ) or 0

    latest_ctx = (await session.execute(
        select(AgentSessionContext)
        .order_by(AgentSessionContext.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    return ContinuityStatusOut(
        available=True,
        last_bootstrap_at=last_bootstrap,
        last_harness=last_harness_row,
        active_source_count=active_sources,
        is_truncated=latest_ctx.truncated if latest_ctx else False,
        degraded_reasons=latest_ctx.degraded_reasons if latest_ctx else [],
        has_active_continuity=active_sources > 0,
    )


