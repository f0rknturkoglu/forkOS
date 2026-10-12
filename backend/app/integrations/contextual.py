"""Product summaries over existing owners. Read-only; never invokes a model."""

import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.core.models import Entity
from app.core.time import local_day_bounds
from app.integrations.contextual_schemas import (
    AssistanceContext,
    AssistanceSummary,
    ContextFact,
    ContextLink,
    ReviewContext,
)
from app.integrations.review_intelligence.models import SourceRef

MAX_CONTEXT_BYTES = 24_000


async def require_entity(db, identity, types):
    entity = await db.get(Entity, identity)
    if not entity or entity.archived_at or entity.type not in types:
        raise HTTPException(404, "Seçilen bağlam kaydı bulunamadı")
    return entity


def add_entity(out, entity, *, schedulable=False):
    from app.integrations.agent.context import resolve_route

    identity = str(entity.id)
    out.sources.append(
        SourceRef(
            ref="entity:" + identity,
            domain="operational",
            kind=entity.type,
            entity_id=identity,
            title=entity.title[:300],
            timestamp=entity.updated_at.isoformat(),
        )
    )
    out.links.append(
        ContextLink(
            id=entity.id,
            type=entity.type,
            title=entity.title[:300],
            route=resolve_route(entity.type, entity.id),
            schedulable=schedulable,
        )
    )


def add_insights(out, items, *, allowed_refs=None):
    for item in items:
        refs = item.support_refs
        if allowed_refs is not None and (not refs or not set(refs).issubset(allowed_refs)):
            continue
        out.facts.append(
            ContextFact(
                text=item.text[:500],
                status=item.status,
                support_refs=refs,
                timestamp=item.temporal_start,
            )
        )


async def review_summary(db, context: ReviewContext, out):
    from app.integrations.review_intelligence.service import review_intelligence
    from app.modules.review import service as reviews
    from app.modules.review.models import Review
    from app.modules.todo.models import Todo

    start, end = reviews.period_bounds(context.period_kind, context.period_start)
    if start != context.period_start:
        raise HTTPException(422, "Dönem başlangıcı seçilen takvim dönemiyle eşleşmeli")
    saved = (
        await db.get(Review, context.review_id)
        if context.review_id
        else await db.scalar(
            select(Review).where(Review.kind == context.period_kind, Review.period_start == start)
        )
    )
    if context.review_id and not saved:
        raise HTTPException(404, "Kaydedilmiş değerlendirme bulunamadı")
    if saved and (saved.kind != context.period_kind or saved.period_start != start):
        raise HTTPException(422, "Değerlendirme bu döneme ait değil")
    if saved:
        # Accepted history remains history. Do not reconstruct it from today's database.
        saved_entity = await require_entity(db, saved.id, {"review"})
        ref = "review:" + str(saved.id)
        out.sources.append(
            SourceRef(
                ref=ref,
                domain="review",
                kind="review",
                title="Kaydedilmiş dönem",
                timestamp=saved_entity.created_at.isoformat(),
            )
        )
        stats = saved.stats
        out.warnings.append(
            "Kaydedilmiş değerlendirme: aşağıdaki ölçümler o günkü kayıttır; canlı durumla yeniden hesaplanmadı."
        )
        from app.integrations.review_intelligence.models import Coverage

        out.coverage = Coverage(
            period_start=local_day_bounds(start)[0].isoformat(),
            period_end=local_day_bounds(end)[0].isoformat(),
            days=(end - start).days,
            partial=local_day_bounds(end)[0] > saved_entity.created_at,
            comparable=False,
        )
        if saved.note:
            out.facts.append(
                ContextFact(text=saved.note[:500], status="candidate", support_refs=[ref])
            )
    else:
        preview = await reviews.preview(db, context.period_kind, start)
        stats = preview.stats.model_dump(mode="json")
        ref = f"aggregate:review_preview:{context.period_kind}:{start}"
        out.sources.append(
            SourceRef(
                ref=ref, domain="aggregate", kind="review_preview", title="Canlı dönem ölçümleri"
            )
        )
    out.title = f"{start} → {end} · Dönem değerlendirmesi"
    # Missing != zero: old snapshots may not contain these fields.
    for group, key, label in (
        ("todos", "completed", "Tamamlanan görev"),
        ("flashcards", "reviewed", "Tekrar edilen kart"),
    ):
        if key in stats.get(group, {}):
            out.facts.append(ContextFact(text=f"{label}: {stats[group][key]}", support_refs=[ref]))
    for objective in (stats.get("strategy_snapshot") or {}).get("objectives", [])[:6]:
        identity = UUID(objective["goal"]["id"])
        target = await db.get(Entity, identity)
        if target and not target.archived_at:
            add_entity(out, target)
        progress = objective.get("strategic_progress_percent")
        text = f"{objective['goal']['title'][:200]}: " + (
            f"ölçülebilen sonuçlarda %{progress}"
            if progress is not None
            else "sonuç ilerlemesi bilinmiyor"
        )
        reasons = [r.get("explanation", "") for r in objective.get("reasons", [])[:3]]
        out.facts.append(ContextFact(text=text + ". " + " ".join(reasons), support_refs=[ref]))
    if not saved:
        for item in preview.unfinished_todos[:10]:
            target = await db.get(Entity, item.id)
            todo = await db.get(Todo, item.id)
            if target and not target.archived_at and todo and todo.status in {"open", "doing"}:
                add_entity(out, target, schedulable=True)
    focus = stats.get("focus", {})
    if "minutes" in focus:
        out.facts.append(
            ContextFact(
                text=f"Kayıtlı odak: {focus['minutes']} dk; sonuç veya öğrenme ustalığı ölçümü değildir.",
                support_refs=[ref],
            )
        )
    if context.period_kind in {"daily", "weekly"} and not saved:
        h5 = await review_intelligence(
            db,
            mode="weekly_review" if context.period_kind == "weekly" else "daily_close",
            reference_date=start.isoformat(),
            include_knowledge=False,
        )
        out.coverage = h5.coverage
        out.warnings += h5.warnings
        out.truncated |= h5.truncated
        out.sources += h5.sources
        payload = h5.payload
        add_insights(out, getattr(payload, "wins", getattr(payload, "completed_outcomes", [])))
        add_insights(out, getattr(payload, "changes", []))
        for loop in payload.open_loops[:5]:
            out.facts.append(
                ContextFact(text=f"Açık kalan: {loop.title}", support_refs=loop.support_refs)
            )
    elif not saved:
        from app.integrations.review_intelligence.models import Coverage

        out.coverage = Coverage(
            period_start=local_day_bounds(start)[0].isoformat(),
            period_end=local_day_bounds(end)[0].isoformat(),
            days=(end - start).days,
            partial=local_day_bounds(end)[0] > datetime.now(UTC),
            comparable=False,
        )
        out.warnings.append("Bu dönem için haftalık karşılaştırma üretilmedi.")
    if out.coverage and out.coverage.partial:
        out.warnings.append(
            "Kayıt dönemin tamamını kapsamıyor; tam dönemlerle sayısal karşılaştırma yapılmaz."
        )


async def project_summary(db, context, out):
    from app.integrations.agent.context import get_project_context
    from app.integrations.review_intelligence.service import review_intelligence
    from app.modules.project import service as projects
    from app.modules.todo.models import Todo

    entity = await require_entity(db, context.entity_id, {"project"})
    packet = await get_project_context(db, str(entity.id))
    h5 = await review_intelligence(
        db, mode="continuity", focus_entity_id=str(entity.id), include_knowledge=False
    )
    out.title = "Proje özeti"
    add_entity(out, entity)
    out.coverage = h5.coverage
    out.truncated |= h5.truncated
    allowed = {"entity:" + str(entity.id)}
    for todo in packet.todos[:10]:
        todo_entity = await require_entity(db, UUID(todo["id"]), {"todo"})
        todo_row = await db.get(Todo, todo_entity.id)
        add_entity(out, todo_entity, schedulable=todo_row.status in {"open", "doing"})
        allowed.add("entity:" + todo["id"])
    for milestone in packet.milestones[:10]:
        item = await require_entity(db, UUID(milestone["id"]), {"milestone"})
        add_entity(out, item)
        allowed.add("entity:" + milestone["id"])
    timeline = await projects.timeline(db, entity.id, limit=10)
    for event in timeline:
        event_ref = "event:" + str(event["id"])
        allowed.add(event_ref)
        out.sources.append(
            SourceRef(
                ref=event_ref,
                domain="operational",
                kind="event",
                title=event["verb"],
                timestamp=str(event["occurred_at"]),
            )
        )
    for field in (
        "recent_completed",
        "state_changes",
        "stalled_projects",
        "time_sensitive_changes",
    ):
        add_insights(out, getattr(h5.payload, field), allowed_refs=allowed)
    out.sources += [s for s in h5.sources if s.ref in allowed]
    # This existing reader includes linked tasks; unlike a GitHub sync stamp it represents counted activity.
    from app.integrations.review_intelligence.sources import project_last_activity

    activity = await project_last_activity(db, project_ids=[entity.id])
    last = activity.get(str(entity.id))
    out.facts.append(
        ContextFact(
            text=f"Son kayıtlı anlamlı hareket: {last.isoformat()}"
            if last
            else "Henüz çalışma kaydı yok.",
            status="fact" if last else "missing",
            support_refs=["entity:" + str(entity.id)] if last else [],
            timestamp=last.isoformat() if last else None,
        )
    )
    if packet.project.get("next_action"):
        out.facts.append(
            ContextFact(
                text="Kayıtlı sonraki adım: " + packet.project["next_action"][:400],
                support_refs=["entity:" + str(entity.id)],
            )
        )
    if packet.knowledge.available:
        out.facts.append(
            ContextFact(
                text="Bağlı Obsidian notu: " + str(packet.knowledge.relative_path),
                support_refs=["entity:" + str(entity.id)],
            )
        )
    else:
        out.warnings.append(
            "Bağlı Obsidian notu bulunamadı veya Vault erişilemiyor; günlük gövdesi okunmadı."
        )
    for event in timeline:
        if event["verb"] == "github.commit":
            ref = "event:" + str(event["id"])
            out.sources.append(
                SourceRef(
                    ref=ref,
                    domain="operational",
                    kind="event",
                    title="Depo hareketi",
                    timestamp=str(event["occurred_at"]),
                )
            )
            out.facts.append(
                ContextFact(
                    text="Depoda kayıtlı commit hareketi var; kişisel çalışma veya proje sonucu olduğu varsayılmaz.",
                    support_refs=[ref],
                    timestamp=str(event["occurred_at"]),
                )
            )
            break


async def build_summary(db, context: AssistanceContext) -> AssistanceSummary:
    from app.integrations.agent.context import get_entity_context
    from app.modules.semantic_memory import service as memory
    from app.modules.todo.models import Todo

    out = AssistanceSummary(title="Mevcut bağlam", generated_at=datetime.now(UTC))
    if context.kind == "review":
        await review_summary(db, context, out)
    elif context.kind == "project":
        await project_summary(db, context, out)
    elif context.kind == "planning":
        for identity in context.todo_ids:
            entity = await require_entity(db, identity, {"todo"})
            todo = await db.get(Todo, identity)
            add_entity(out, entity, schedulable=todo.status != "done")
        out.title = f"Seçili görevler · {context.day}"
    else:
        types = {
            "goal": {"goal"},
            "career": {"opportunity"},
            "learning": {"study_topic", "bookmark"},
        }[context.kind]
        entity = await require_entity(db, context.entity_id, types)
        add_entity(out, entity)
        out.title = entity.title[:300]
        packet = await get_entity_context(db, str(entity.id))
        for related in packet.related_entities[:12]:
            target = await db.get(Entity, UUID(related["id"]))
            if target and not target.archived_at:
                todo = await db.get(Todo, target.id) if target.type == "todo" else None
                add_entity(out, target, schedulable=bool(todo and todo.status != "done"))
        if context.kind == "goal":
            from app.modules.goal import service as goals
            from app.modules.goal import strategy

            goal = await goals.get_goal(db, entity.id)
            overview = await strategy.overview(db)
            objective = next((o for o in overview.objectives if o.goal.id == entity.id), None)
            if objective:
                progress = objective.strategic_progress_percent
                out.facts.append(
                    ContextFact(
                        text="Ölçülen sonuç ilerlemesi: "
                        + (f"%{progress}" if progress is not None else "bilinmiyor")
                        + f"; {objective.measurable_count}/{objective.active_kr_count} sonuç ölçülebiliyor.",
                        support_refs=["entity:" + str(entity.id)],
                    )
                )
                out.warnings += [r.explanation for r in objective.reasons[:5]]
                for kr in objective.key_results[:6]:
                    item = await db.get(Entity, kr.id)
                    if item and not item.archived_at:
                        add_entity(out, item)
                    out.facts.append(
                        ContextFact(
                            text=f"{kr.title[:200]}: "
                            + (
                                f"%{kr.measurement.progress_percent}"
                                if kr.measurement.progress_percent is not None
                                else "ölçüm bilinmiyor"
                            ),
                            support_refs=["entity:" + str(kr.id)],
                        )
                    )
                    out.warnings += [r.explanation for r in kr.measurement.reasons[:2]]
            out.facts.append(
                ContextFact(
                    text=f"Hedef durumu: { {'active': 'etkin', 'paused': 'beklemede', 'completed': 'tamamlandı', 'retired': 'kapatıldı'}[goal.status] }. Emek süresi tek başına sonuç ilerlemesi değildir.",
                    support_refs=["entity:" + str(entity.id)],
                )
            )
        if context.kind == "career":
            from app.modules.opportunity.models import Application, Opportunity

            opportunity = await db.get(Opportunity, entity.id)
            application = await db.scalar(
                select(Application).where(Application.opportunity_id == entity.id)
            )
            out.facts.append(
                ContextFact(
                    text=f"Keşif durumu: {opportunity.status}; başvuru durumu: {application.status if application else 'başvuru kaydı yok'}.",
                    support_refs=["entity:" + str(entity.id)],
                )
            )
        if not out.facts:
            out.facts.append(
                ContextFact(
                    text="Mevcut kayıt ve bağlı kaynaklar; öğrenme ustalığı veya başarı çıkarımı yapılmadı.",
                    support_refs=["entity:" + str(entity.id)],
                )
            )
    out.memory_candidates = await memory.contextual_candidates(
        db,
        entity_id=str(getattr(context, "entity_id", "")),
        refs={s.ref for s in out.sources},
        allow_global=context.kind in {"review", "goal", "planning"},
    )
    if len(out.facts) > 16 or len(out.links) > 20 or len(out.sources) > 30:
        out.truncated = True
    out.facts = out.facts[:16]
    out.links = list({str(link.id): link for link in out.links}.values())[:20]
    out.sources = list({s.ref: s for s in out.sources}.values())[:30]
    out.warnings = list(dict.fromkeys(out.warnings))[:12]
    # Never silently chop JSON. Remove complete trailing records, report bounded context.
    while len(out.model_dump_json().encode()) > MAX_CONTEXT_BYTES - 400:
        out.truncated = True
        if out.memory_candidates:
            out.memory_candidates.pop()
        elif out.sources:
            out.sources.pop()
        elif out.links:
            out.links.pop()
        elif out.facts:
            out.facts.pop()
        else:
            raise HTTPException(422, "Bağlam sınırı aşıldı")
    if out.truncated:
        out.warnings.append(
            "Kaynaklar sınırlı bir pencereyle gösteriliyor; bu özet tam geçmiş değildir."
        )
    return out


def inference_context(summary):
    # Memory review metadata is not inference consent. It stays in the UI, never sent implicitly.
    data = summary.model_dump(mode="json", exclude={"memory_candidates", "strategy_snapshot"})
    return json.loads(json.dumps(data, ensure_ascii=False))
