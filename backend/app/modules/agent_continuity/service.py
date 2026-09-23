"""A2 Context Composition Service.

Kanonik kaynaklar (forkOS PostgreSQL, H2, H5, f0rknbrain Vault) açısından
tamamen salt-okunur (read-only) çalışır.
Oturum içi bütçe ve kaynak referanslarını ephemeral destek tablolarına kaydeder.
"""

import hashlib
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
    ContinuityStatusOut,
    OperationalDeadline,
    OperationalProject,
    OperationalState,
)
from app.modules.agent_lifecycle.models import AgentSession
from app.modules.execution.models import ExecutionPlan
from app.modules.project.models import Project
from app.modules.todo.models import Todo

LOGGER = logging.getLogger("forkos.agent_continuity")

MAX_RENDER_CHAR_BUDGET = 4000
DEFAULT_TTL_MINUTES = 60
MAX_DELIVERED_SOURCES = 5


def compute_project_source_version(
    title: str,
    status: str,
    next_action: str | None = None,
    last_activity_at: Any | None = None,
) -> str:
    """A2 tarafından tüketilen bounded project canonical payload deterministik parmak izi."""
    act = (
        last_activity_at.isoformat()
        if hasattr(last_activity_at, "isoformat")
        else str(last_activity_at or "")
    )
    raw = f"{title}|{status}|{next_action or ''}|{act}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def compute_deadline_source_version(
    title: str,
    due_at: Any | None = None,
    entity_type: str | None = None,
    module: str | None = None,
    priority: int | None = None,
) -> str:
    """A2 tarafından tüketilen provider-aware bounded deadline canonical payload parmak izi."""
    due = due_at.isoformat() if hasattr(due_at, "isoformat") else str(due_at or "")
    raw = f"{title}|{due}|{entity_type or ''}|{module or ''}|{priority or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def compute_decision_source_version(
    summary: str,
    status: str,
    revision: int | str = 0,
) -> str:
    """A2 tarafından tüketilen decision canonical payload parmak izi."""
    raw = f"{summary}|{status}|{revision}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def compute_vault_note_source_version(note_bytes: bytes) -> str:
    """Vault notu byte seviyesinde SHA-256 tam parmak izi."""
    return hashlib.sha256(note_bytes).hexdigest()[:32]


async def _collect_identity(
    session: AsyncSession,
    scope_project: str | None = None,
) -> tuple[BootstrapIdentity, list[str], list[Any]]:
    """Kullanıcı ilkelerini ve kalıcı tercihleri f0rknbrain / H2 üzerinden seçer."""
    degraded: list[str] = []
    conventions = [
        "Kullanıcı Türkçe konuşur; kod ve değişkenler İngilizce, açıklamalar Türkçe olmalı. Local-only çalış: harici telemetri veya bulut modeli çağrısı yok.",
        "Kullanıcı onayı olmadan kanonik operasyonel verileri doğrudan mutate etme.",
    ]
    preferences: list[str] = []
    corrections: list[str] = []
    goals: list[str] = []
    semantic_cards: list[Any] = []
    hot_constraints: list[str] = []

    try:
        from app.integrations.agent import hot_memory as h2_svc

        ctx = h2_svc.get_context(
            kinds=["profile", "preference", "constraint", "goal", "correction"]
        )
        for p in ctx.preferences[:3]:
            preferences.append(p.title)
        hot_constraints = [c.title for c in ctx.constraints[:2]]
        for g in ctx.goals[:2]:
            goals.append(g.title)
        for cor in getattr(ctx, "corrections", [])[:3]:
            corrections.append(cor.title)
    except Exception as exc:
        LOGGER.warning("H2 hot memory read degraded in bootstrap: %s", exc)
        degraded.append("HOT_MEMORY_UNAVAILABLE")

    try:
        from app.integrations.obsidian.semantic_memory import get_semantic_profile, readable_root

        sem_root = readable_root()
        if sem_root is not None:
            profile = get_semantic_profile(sem_root, scope_project=scope_project)
            for c in profile.corrections:
                if c.statement not in corrections and len(corrections) < 3:
                    corrections.append(c.statement)
                if c.statement in corrections and c not in semantic_cards:
                    semantic_cards.append(c)
            for co in profile.constraints:
                if co.statement not in conventions and len(conventions) < 3:
                    conventions.append(co.statement)
                if co.statement in conventions and co not in semantic_cards:
                    semantic_cards.append(co)
            for identity_card in profile.identity:
                wording = f"Kimlik: {identity_card.statement}"
                if wording not in preferences and len(preferences) < 4:
                    preferences.append(wording)
                if wording in preferences and identity_card not in semantic_cards:
                    semantic_cards.append(identity_card)
            for p in profile.preferences:
                if p.statement not in preferences and len(preferences) < 4:
                    preferences.append(p.statement)
                if p.statement in preferences and p not in semantic_cards:
                    semantic_cards.append(p)
            for g in profile.goals:
                if g.statement not in goals and len(goals) < 3:
                    goals.append(g.statement)
                if g.statement in goals and g not in semantic_cards:
                    semantic_cards.append(g)
    except Exception as exc:
        LOGGER.warning("Semantic profile read degraded in bootstrap: %s", exc)

    for constraint in hot_constraints:
        if constraint not in conventions and len(conventions) < 3:
            conventions.append(constraint)

    return (
        BootstrapIdentity(
            interaction_conventions=conventions[:3],
            durable_preferences=preferences[:4],
            explicit_corrections=corrections[:3],
            long_running_goals=goals[:3],
        ),
        degraded,
        semantic_cards,
    )


async def _collect_operational_projects(
    session: AsyncSession, limit: int = 5
) -> list[OperationalProject]:
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
        act_str = proj.last_activity_at.isoformat() if proj.last_activity_at else None
        projects.append(
            OperationalProject(
                id=str(proj.id),
                title=title,
                status=proj.status,
                next_action=proj.next_action,
                last_activity_at=act_str,
            )
        )
    return projects


async def _collect_vault_notes(
    scope_project: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """f0rknbrain kasasından anlamsal ve güvenli kalıcı bilgi seçer.

    Tüm kasayı gezmez (os.walk yapmaz); vault_index üzerinden managed kayıtları sorgular.
    """
    degraded: list[str] = []
    notes: list[dict[str, Any]] = []
    try:
        from app.config import settings
        from app.integrations.agent.knowledge import is_vault_accessible
        from app.integrations.obsidian.hot_memory import is_policy_excluded
        from app.integrations.obsidian.security import (
            is_safe_knowledge_path,
            resolve_safe_vault_path,
        )
        from app.integrations.obsidian.service import vault_index

        if not is_vault_accessible():
            degraded.append("VAULT_UNAVAILABLE")
            return notes, degraded

        v_root = settings.resolved_obsidian_vault_path
        if not v_root:
            return notes, degraded

        if not vault_index.is_scanned:
            # İndeks henüz hazır değilse hot path'te disk taraması yapma; güvenli degrade ol
            return notes, degraded

        # 1. Eğer scope_project varsa, projenin managed bilgi notunu ara
        if scope_project:
            v_item = vault_index.get_item(str(scope_project)) or vault_index.find_by_note_kind(
                "project", project_id=str(scope_project)
            )
            if not v_item:
                for item in vault_index.items.values():
                    if item.forkos_type == "project" and (
                        item.forkos_id == str(scope_project)
                        or item.project_id == str(scope_project)
                    ):
                        v_item = item
                        break
            if v_item:
                try:
                    safe_path = resolve_safe_vault_path(v_root, v_item.relative_path)
                    rel_from_vault = safe_path.relative_to(v_root)
                    if is_safe_knowledge_path(rel_from_vault) and safe_path.is_file():
                        raw_bytes = safe_path.read_bytes()
                        raw_text = raw_bytes.decode("utf-8", errors="ignore")
                        if not is_policy_excluded(rel_from_vault, raw_text):
                            notes.append(
                                {
                                    "relative_path": v_item.relative_path,
                                    "title": str(v_item.title or safe_path.stem)[:128],
                                    "version": compute_vault_note_source_version(raw_bytes),
                                    "snippet": " ".join(raw_text.split())[:250],
                                    "kind": "project_knowledge",
                                    "scope_project": scope_project,
                                }
                            )
                except Exception:
                    pass

        # 2. Kalıcı kural / tercih notu (yalnız açıkça managed olanlar)
        pref_items = [
            item
            for item in vault_index.items.values()
            if item.note_kind == "preference" or item.forkos_type == "memory"
        ]
        for p_item in pref_items[:1]:
            try:
                safe_path = resolve_safe_vault_path(v_root, p_item.relative_path)
                rel_from_vault = safe_path.relative_to(v_root)
                if is_safe_knowledge_path(rel_from_vault) and safe_path.is_file():
                    raw_bytes = safe_path.read_bytes()
                    raw_text = raw_bytes.decode("utf-8", errors="ignore")
                    if not is_policy_excluded(rel_from_vault, raw_text):
                        notes.append(
                            {
                                "relative_path": p_item.relative_path,
                                "title": str(p_item.title or safe_path.stem)[:128],
                                "version": compute_vault_note_source_version(raw_bytes),
                                "snippet": " ".join(raw_text.split())[:250],
                                "kind": "preference",
                                "scope_project": None,
                            }
                        )
            except Exception:
                pass

    except Exception as exc:
        LOGGER.warning("Vault notes collection degraded: %s", type(exc).__name__)
        degraded.append("VAULT_UNAVAILABLE")
    return notes[:2], degraded


async def _collect_operational_deadlines(
    session: AsyncSession, limit: int = 5
) -> list[OperationalDeadline]:
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
                module=d.get("module"),
                priority=d.get("priority"),
            )
        )
    return deadlines


async def _collect_operational_decisions(
    session: AsyncSession, limit: int = 3
) -> tuple[int, list[str]]:
    """Bekleyen H7 kararlarını sayar ve özetler."""
    stmt = (
        select(ExecutionPlan.id, ExecutionPlan.title, ExecutionPlan.state)
        .where(ExecutionPlan.state.in_(["draft", "ready_for_review", "input_required"]))
        .order_by(ExecutionPlan.created_at.desc())
        .limit(limit)
    )
    res = await session.execute(stmt)
    rows = res.all()
    count_stmt = (
        select(func.count())
        .select_from(ExecutionPlan)
        .where(ExecutionPlan.state.in_(["draft", "ready_for_review", "input_required"]))
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
        for correction in getattr(ctx, "corrections", [])[:2]:
            items.append(
                {
                    "kind": "correction",
                    "title": correction.title,
                    "text": correction.text,
                    "memory_id": correction.memory_id,
                    "revision": getattr(correction, "revision", 1),
                }
            )
        for p in ctx.profile[:1]:
            items.append(
                {
                    "kind": "profile",
                    "title": p.title,
                    "text": p.text,
                    "memory_id": p.memory_id,
                    "revision": getattr(p, "revision", 1),
                }
            )
        for c in ctx.constraints[:2]:
            items.append(
                {
                    "kind": "constraint",
                    "title": c.title,
                    "text": c.text,
                    "memory_id": c.memory_id,
                    "revision": getattr(c, "revision", 1),
                }
            )
        for g in ctx.goals[:2]:
            items.append(
                {
                    "kind": "goal",
                    "title": g.title,
                    "text": g.text,
                    "memory_id": g.memory_id,
                    "revision": getattr(g, "revision", 1),
                }
            )
        for d in ctx.decisions[:1]:
            items.append(
                {
                    "kind": "decision",
                    "title": d.title,
                    "text": d.text,
                    "memory_id": d.memory_id,
                    "revision": getattr(d, "revision", 1),
                }
            )
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
    identity, id_deg, sem_cards = await _collect_identity(session, scope_project=scope_project)
    degraded_reasons.extend(id_deg)

    projects = (await _collect_operational_projects(session, limit=5))[:5]
    deadlines = (await _collect_operational_deadlines(session, limit=5))[:5]
    open_todos_count = (
        await session.scalar(select(func.count()).select_from(Todo).where(Todo.status != "done"))
        or 0
    )
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

    vault_notes, v_deg = await _collect_vault_notes(scope_project=scope_project)
    degraded_reasons.extend(v_deg)
    for vn in vault_notes:
        if (
            vn.get("kind") == "preference"
            and vn.get("snippet")
            and len(identity.durable_preferences) < 4
        ):
            identity.durable_preferences.append(f"{vn['title']}: {vn['snippet'][:100]}")

    # 3. Kaynak referansları oluştur (en fazla 5 grup)
    sources: list[BootstrapSourceRef] = []
    for proj in projects[: 1 if sem_cards else 2]:
        p_version = compute_project_source_version(
            proj.title,
            proj.status,
            proj.next_action,
            proj.last_activity_at,
        )
        sources.append(
            BootstrapSourceRef(
                source_id=f"entity:{proj.id}",
                source_type="project",
                source_version=p_version,
                scope_project=proj.id,
                title=proj.title[:128] if proj.title else None,
            )
        )
    for sc in sem_cards[:3]:
        sources.append(
            BootstrapSourceRef(
                source_id=f"semantic_memory:{sc.card_id}",
                source_type="semantic_memory",
                source_version=sc.revision,
                scope_project=sc.scope_project,
                title=sc.title[:128] if sc.title else None,
            )
        )
    for dead in deadlines[: 1 if sem_cards else 2]:
        d_version = compute_deadline_source_version(
            title=dead.title,
            due_at=dead.due_at,
            entity_type=dead.entity_type,
            module=dead.module,
            priority=dead.priority,
        )
        sources.append(
            BootstrapSourceRef(
                source_id=f"entity:{dead.id}",
                source_type="deadline",
                source_version=d_version,
                title=dead.title[:128] if dead.title else None,
            )
        )
    for h in hot_items[:1]:
        mem_id = h.get("memory_id")
        if mem_id:
            raw_title = h.get("title")
            rev = h.get("revision")
            sources.append(
                BootstrapSourceRef(
                    source_id=f"hot_memory:{mem_id}",
                    source_type="hot_memory",
                    source_version=str(rev) if rev is not None else "1",
                    title=raw_title[:128] if raw_title else None,
                )
            )
    for vn in vault_notes[:1]:
        sources.append(
            BootstrapSourceRef(
                source_id=f"vault:{vn['relative_path']}",
                source_type="vault_note",
                source_version=vn["version"],
                scope_project=vn.get("scope_project"),
                title=vn["title"],
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

    rendered = render_bootstrap_context(packet, enforce_hard_ceiling=False)
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
        rendered = render_bootstrap_context(packet, enforce_hard_ceiling=False)

    # Son sert tavan garantisi
    rendered = render_bootstrap_context(packet, enforce_hard_ceiling=True)

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
        item_count=len(packet.operational_state.active_projects)
        + len(packet.operational_state.upcoming_deadlines)
        + len(packet.hot_memory.items),
        char_count=len(rendered),
        truncated=packet.diagnostics.truncated,
        omitted_count=packet.diagnostics.omitted_count,
        degraded_reasons=packet.diagnostics.degraded_reasons,
        scope_project=scope_project,
        created_at=now,
    )
    session.add(ctx_row)

    for s in sources:
        stmt = (
            insert(AgentSessionSource)
            .values(
                session_id=session_row.id,
                turn_id=turn_id,
                source_id=s.source_id,
                source_type=s.source_type,
                source_version=s.source_version,
                scope_project=s.scope_project,
                topic_signature="initial_bootstrap",
                delivered_at=now,
                expires_at=expires_at,
            )
            .on_conflict_do_update(
                constraint="uq_agent_session_source_identity",
                set_={
                    "delivered_at": now,
                    "expires_at": expires_at,
                    "turn_id": turn_id,
                    "source_version": s.source_version,
                },
            )
        )
        await session.execute(stmt)

    # Opportunistic pruning
    await session.execute(
        delete(AgentSessionSource).where(
            AgentSessionSource.session_id == session_row.id,
            AgentSessionSource.expires_at < now,
        )
    )
    old_ctx_ids = (
        await session.scalars(
            select(AgentSessionContext.id)
            .where(AgentSessionContext.session_id == session_row.id)
            .order_by(AgentSessionContext.created_at.desc())
            .offset(50)
        )
    ).all()
    if old_ctx_ids:
        await session.execute(
            delete(AgentSessionContext).where(AgentSessionContext.id.in_(old_ctx_ids))
        )

    await session.commit()
    return packet, sources, rendered


AMBIGUOUS_PATTERNS = [
    "bunu biraz aç",
    "bunu ac",
    "bunu aç",
    "bunu açıkla",
    "bunu acikla",
    "bunu detaylandır",
    "bunu detaylandir",
    "biraz daha aç",
    "biraz daha ac",
    "bunu detaylandırır mısın",
    "bunu detaylandirir misin",
    "daha detaylı",
    "daha detayli",
    "daha fazla detay",
    "onu da karşılaştır",
    "onu da karsilastir",
    "karşılaştır",
    "karsilastir",
    "peki bunun",
    "peki bunun diğerinden farkı",
    "peki bunun digerinden farki",
    "farkı ne",
    "farki ne",
    "önceki kaynağa göre",
    "onceki kaynaga gore",
    "önceki kaynak",
    "onceki kaynak",
    "buna göre",
    "buna gore",
    "ondan bahset",
    "ondan bahset biraz",
    "hangisi daha iyi",
    "peki ya",
    "neden peki",
    "expand on this",
    "tell me more",
    "explain further",
    "compare that",
    "what about that",
    "what did you mean",
    "go on",
    "elaborate",
    "more details",
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
        if any(
            w
            in {
                "bunu",
                "bunun",
                "bunda",
                "bundan",
                "onu",
                "onun",
                "onda",
                "ondan",
                "this",
                "that",
                "these",
                "it",
            }
            for w in words
        ):
            return True
    return False


def _extract_candidate_keywords(prompt: str) -> list[str]:
    words = re.findall(r"\b[\w-]+\b", prompt)
    stop_words = {
        "ile",
        "icin",
        "için",
        "olan",
        "nedir",
        "nelerdir",
        "nasil",
        "nasıl",
        "durum",
        "son",
        "ilgili",
        "hakkında",
        "hakkinda",
        "proje",
        "projesi",
        "gorev",
        "görev",
        "yeni",
        "bir",
        "ve",
        "veya",
        "ama",
        "fakat",
        "the",
        "and",
        "about",
        "what",
        "project",
        "task",
        "show",
        "tell",
        "give",
        "list",
    }
    candidates = [w for w in words if len(w) >= 3 and w.lower() not in stop_words]
    return candidates


async def check_source_freshness(
    session: AsyncSession,
    source_row: AgentSessionSource,
) -> tuple[bool, str | None]:
    """Kaynağın canlı kanonik veriye göre hâlâ güncel olup olmadığını kontrol eder.

    A2 dışında A3 de kullanır (§22): geçmiş bir oturumun devri güncel durum
    gibi sunulmasın diye destek referansları bu fonksiyonla yeniden doğrulanır.
    Bu yüzden genel addır; ikinci bir tazelik kopyası YAZILMAZ.

    Döner: (is_fresh, current_title)
    """
    if source_row.source_id.startswith("entity:"):
        try:
            ent_uuid = uuid.UUID(source_row.source_id.split(":", 1)[1])
        except Exception:
            return False, None

        if source_row.source_type == "project":
            row = (
                await session.execute(
                    select(Project, Entity.title, Entity.archived_at)
                    .join(Entity, Entity.id == Project.id)
                    .where(Project.id == ent_uuid)
                )
            ).first()
            if not row or row.archived_at is not None:
                return False, None
            proj, title, _ = row
            cur_version = compute_project_source_version(
                title,
                proj.status,
                proj.next_action,
                proj.last_activity_at,
            )
            if source_row.source_version and source_row.source_version != cur_version:
                return False, title
            return True, title

        elif source_row.source_type in ("deadline", "todo"):
            from app.core.deadlines import collect_deadlines

            raw_deadlines = await collect_deadlines(session, limit=200)
            target_deadline = next(
                (d for d in raw_deadlines if str(d.get("entity_id")) == str(ent_uuid)),
                None,
            )
            if not target_deadline:
                return False, None

            cur_version = compute_deadline_source_version(
                title=target_deadline.get("title", ""),
                due_at=target_deadline.get("due_at"),
                entity_type=target_deadline.get("type"),
                module=target_deadline.get("module"),
                priority=target_deadline.get("priority"),
            )
            if source_row.source_version and source_row.source_version != cur_version:
                return False, target_deadline.get("title")
            return True, target_deadline.get("title")

    elif source_row.source_type == "vault_note" and source_row.source_id.startswith("vault:"):
        rel_path = source_row.source_id.split(":", 1)[1]
        try:
            from app.config import settings
            from app.integrations.obsidian.hot_memory import is_policy_excluded
            from app.integrations.obsidian.security import (
                is_safe_knowledge_path,
                resolve_safe_vault_path,
            )

            v_root = settings.resolved_obsidian_vault_path
            if not v_root:
                return False, None

            try:
                safe_target = resolve_safe_vault_path(v_root, rel_path)
            except (ValueError, PermissionError):
                return False, None

            rel_from_vault = safe_target.relative_to(v_root)
            if not is_safe_knowledge_path(rel_from_vault):
                return False, None

            if not safe_target.exists() or not safe_target.is_file():
                return False, None

            data = safe_target.read_bytes()
            raw_text = data.decode("utf-8", errors="ignore")
            if is_policy_excluded(rel_from_vault, raw_text):
                return False, None

            cur_version = compute_vault_note_source_version(data)
            if source_row.source_version and source_row.source_version != cur_version:
                return False, safe_target.stem
            return True, safe_target.stem
        except Exception:
            return False, None

    elif source_row.source_type == "hot_memory":
        try:
            from app.integrations.agent import hot_memory as h2_svc

            ctx = h2_svc.get_context()
            mem_id = source_row.source_id.split(":", 1)[1] if ":" in source_row.source_id else ""
            for m in (
                ctx.profile
                + ctx.constraints
                + ctx.goals
                + ctx.decisions
                + ctx.preferences
                + list(getattr(ctx, "corrections", []) or [])
            ):
                if m.memory_id == mem_id:
                    cur_rev = str(getattr(m, "revision", 1))
                    if source_row.source_version and source_row.source_version != cur_rev:
                        return False, m.title
                    return True, m.title
            return False, None
        except Exception:
            return False, None

    elif source_row.source_type == "semantic_memory":
        try:
            from app.integrations.obsidian import semantic_memory as sem_svc

            root = sem_svc.readable_root()
            if not root:
                return False, None
            card_id = (
                source_row.source_id.split(":", 1)[1]
                if ":" in source_row.source_id
                else source_row.source_id
            )
            card = next(
                (c for c in sem_svc.scan_semantic_cards(root) if c.card_id == card_id), None
            )
            if card is None or card.effective_status != "active":
                return False, None
            if source_row.source_version and source_row.source_version != card.revision:
                return False, card.title
            return True, card.title
        except Exception:
            return False, None

    return True, None


def _is_topic_compatible(
    prompt: str,
    active_sources: list[AgentSessionSource],
    active_titles: list[str],
    scope_project: str | None,
) -> bool:
    """Deterministik konu uyumluluğu kontrolü (harici model veya embedding kullanmaz)."""
    if not prompt:
        return False
    prompt_words = {w.lower() for w in _extract_candidate_keywords(prompt)}
    if not prompt_words:
        return False

    # Scope uyumu
    if scope_project and any(s.scope_project == scope_project for s in active_sources):
        return True

    # Başlık/kelime örtüşmesi
    for title in active_titles:
        title_words = {w.lower() for w in _extract_candidate_keywords(title)}
        if prompt_words & title_words:
            return True

    return False


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

    # 1. Kapsam geçiş matrisi kontrolü
    last_ctx = (
        await session.execute(
            select(AgentSessionContext)
            .where(AgentSessionContext.session_id == session_row.id)
            .order_by(AgentSessionContext.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    prev_scope = last_ctx.scope_project if last_ctx else None
    curr_scope = scope_project

    if prev_scope and curr_scope and prev_scope != curr_scope:
        # A -> B: Proje değişimi; önceki oturum içi tüm kaynakları geçersiz kıl
        await session.execute(
            delete(AgentSessionSource).where(AgentSessionSource.session_id == session_row.id)
        )
    elif prev_scope and not curr_scope:
        # A -> None: Proje temizlendi; sadece A'ya ait kaynakları temizle, genel kaynakları koru
        await session.execute(
            delete(AgentSessionSource).where(
                AgentSessionSource.session_id == session_row.id,
                AgentSessionSource.scope_project == prev_scope,
            )
        )
    elif not prev_scope and curr_scope:
        # None -> B: Proje kapsamına giriş; farklı bir proje kapsamı olanları temizle
        await session.execute(
            delete(AgentSessionSource).where(
                AgentSessionSource.session_id == session_row.id,
                AgentSessionSource.scope_project.is_not(None),
                AgentSessionSource.scope_project != curr_scope,
            )
        )

    # 2. Aktif unexpired kaynakları çek
    stmt = (
        select(AgentSessionSource)
        .where(
            AgentSessionSource.session_id == session_row.id,
            AgentSessionSource.expires_at > now,
        )
        .order_by(AgentSessionSource.delivered_at.desc())
        .limit(MAX_DELIVERED_SOURCES * 2)
    )
    res = await session.execute(stmt)
    all_source_rows = res.scalars().all()

    # Scope filtering: curr_scope varsa yalnız scope_project is None veya scope_project == curr_scope
    if curr_scope:
        source_rows = [
            r for r in all_source_rows if r.scope_project is None or r.scope_project == curr_scope
        ][:MAX_DELIVERED_SOURCES]
    else:
        source_rows = all_source_rows[:MAX_DELIVERED_SOURCES]

    # 3. Canlı veriyle tazelik doğrulaması (Stale detection)
    fresh_sources: list[tuple[AgentSessionSource, str | None]] = []
    stale_ids: list[int] = []
    for r in source_rows:
        is_fresh, title = await check_source_freshness(session, r)
        if is_fresh:
            fresh_sources.append((r, title))
        else:
            stale_ids.append(r.id)

    if stale_ids:
        await session.execute(
            delete(AgentSessionSource).where(AgentSessionSource.id.in_(stale_ids))
        )
        degraded_reasons.append("SOURCE_STALE")

    # 4. Ambiguous follow-up veya aynı konu devamlılığı (Topic Compatibility)
    is_ambig = _is_ambiguous_continuation(transient_prompt)
    is_compat = False
    if fresh_sources and not is_ambig:
        active_titles = [t for _, t in fresh_sources if t]
        is_compat = _is_topic_compatible(
            transient_prompt,
            active_sources=[s for s, _ in fresh_sources],
            active_titles=active_titles,
            scope_project=curr_scope,
        )

    if (is_ambig or is_compat) and fresh_sources:
        sources: list[BootstrapSourceRef] = []
        for r, title in fresh_sources:
            if curr_scope and r.scope_project is not None and r.scope_project != curr_scope:
                continue
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
            degraded_reasons=sorted(set(degraded_reasons)),
            scope_project=curr_scope,
            created_at=now,
        )
        session.add(ctx_row)

        # Opportunistic pruning
        await session.execute(
            delete(AgentSessionSource).where(
                AgentSessionSource.session_id == session_row.id,
                AgentSessionSource.expires_at < now,
            )
        )
        old_ctx_ids = (
            await session.scalars(
                select(AgentSessionContext.id)
                .where(AgentSessionContext.session_id == session_row.id)
                .order_by(AgentSessionContext.created_at.desc())
                .offset(50)
            )
        ).all()
        if old_ctx_ids:
            await session.execute(
                delete(AgentSessionContext).where(AgentSessionContext.id.in_(old_ctx_ids))
            )

        await session.commit()
        return None, sources, rendered, sorted(set(degraded_reasons))

    # 5. Açık konu değişimi veya taze kaynak kalmaması (Topic Shift)
    # Eski oturum kaynaklarını sıfırla
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
                ent_version = None
                if ent.type == "project":
                    p_row = (
                        await session.execute(select(Project).where(Project.id == ent.id))
                    ).scalar_one_or_none()
                    if p_row:
                        ent_version = compute_project_source_version(
                            ent.title, p_row.status, p_row.next_action, p_row.last_activity_at
                        )
                elif ent.type in ("deadline", "todo"):
                    from app.core.deadlines import collect_deadlines

                    raw_deadlines = await collect_deadlines(session, limit=200)
                    target_deadline = next(
                        (d for d in raw_deadlines if str(d.get("entity_id")) == str(ent.id)),
                        None,
                    )
                    if target_deadline:
                        ent_version = compute_deadline_source_version(
                            title=target_deadline.get("title", ""),
                            due_at=target_deadline.get("due_at"),
                            entity_type=target_deadline.get("type"),
                            module=target_deadline.get("module"),
                            priority=target_deadline.get("priority"),
                        )

                new_sources.append(
                    BootstrapSourceRef(
                        source_id=f"entity:{ent.id}",
                        source_type=ent.type,
                        source_version=ent_version,
                        scope_project=str(ent.id) if ent.type == "project" else None,
                        title=ent.title[:128] if ent.title else None,
                    )
                )
            if new_sources:
                break
        except Exception as exc:
            LOGGER.debug("search_operational_context failed: %s", type(exc).__name__)

    new_sources = new_sources[:MAX_DELIVERED_SOURCES]
    rendered = None
    if new_sources:
        rendered = render_continuity_context(new_sources)
        expires_at = now + timedelta(minutes=DEFAULT_TTL_MINUTES)
        for s in new_sources:
            stmt = (
                insert(AgentSessionSource)
                .values(
                    session_id=session_row.id,
                    turn_id=turn_id,
                    source_id=s.source_id,
                    source_type=s.source_type,
                    source_version=s.source_version,
                    scope_project=s.scope_project,
                    topic_signature="query_retrieval",
                    delivered_at=now,
                    expires_at=expires_at,
                )
                .on_conflict_do_update(
                    constraint="uq_agent_session_source_identity",
                    set_={
                        "delivered_at": now,
                        "expires_at": expires_at,
                        "turn_id": turn_id,
                        "source_version": s.source_version,
                    },
                )
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
        degraded_reasons=sorted(set(degraded_reasons)),
        scope_project=curr_scope,
        created_at=now,
    )
    session.add(ctx_row)

    # Opportunistic pruning
    await session.execute(
        delete(AgentSessionSource).where(
            AgentSessionSource.session_id == session_row.id,
            AgentSessionSource.expires_at < now,
        )
    )
    old_ctx_ids = (
        await session.scalars(
            select(AgentSessionContext.id)
            .where(AgentSessionContext.session_id == session_row.id)
            .order_by(AgentSessionContext.created_at.desc())
            .offset(50)
        )
    ).all()
    if old_ctx_ids:
        await session.execute(
            delete(AgentSessionContext).where(AgentSessionContext.id.in_(old_ctx_ids))
        )

    await session.commit()
    return None, new_sources, rendered, sorted(set(degraded_reasons))


async def status(session: AsyncSession) -> ContinuityStatusOut:
    """Devamlılık ve bağlam oluşturma tanılamalarını döner."""
    now = datetime.now(UTC)
    last_bootstrap = await session.scalar(
        select(AgentSessionContext.created_at)
        .where(AgentSessionContext.is_first_turn.is_(True))
        .order_by(AgentSessionContext.created_at.desc())
        .limit(1)
    )
    last_context = await session.scalar(
        select(AgentSessionContext.created_at)
        .order_by(AgentSessionContext.created_at.desc())
        .limit(1)
    )
    last_harness_row = (
        await session.execute(
            select(AgentSession.harness)
            .join(AgentSessionContext, AgentSessionContext.session_id == AgentSession.id)
            .order_by(AgentSessionContext.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    latest_session_id = await session.scalar(
        select(AgentSession.id)
        .where(AgentSession.status == "active")
        .order_by(AgentSession.last_seen_at.desc())
        .limit(1)
    )
    if latest_session_id:
        active_sources = (
            await session.scalar(
                select(func.count())
                .select_from(AgentSessionSource)
                .where(
                    AgentSessionSource.session_id == latest_session_id,
                    AgentSessionSource.expires_at > now,
                )
            )
            or 0
        )
    else:
        active_sources = 0

    latest_ctx = (
        await session.execute(
            select(AgentSessionContext).order_by(AgentSessionContext.created_at.desc()).limit(1)
        )
    ).scalar_one_or_none()

    return ContinuityStatusOut(
        available=True,
        last_bootstrap_at=last_bootstrap,
        last_context_at=last_context,
        last_harness=last_harness_row,
        active_source_count=active_sources,
        is_truncated=latest_ctx.truncated if latest_ctx else False,
        degraded_reasons=latest_ctx.degraded_reasons if latest_ctx else [],
        has_active_continuity=active_sources > 0,
    )
