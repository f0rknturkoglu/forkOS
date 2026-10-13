"""Deterministic strategic read model and explicit user-controlled writes."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.config import settings
from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity, Link
from app.integrations.obsidian.security import is_safe_knowledge_path, resolve_safe_vault_path
from app.modules.goal import service
from app.modules.goal.metrics import PROVIDERS, MetricContext
from app.modules.goal.models import (
    KeyResult,
    StrategicPillar,
    StrategicPlan,
    StrategicPlanRevision,
)
from app.modules.goal.strategy_schemas import (
    Aggregate,
    Alignment,
    Allocation,
    Finding,
    HistoryItem,
    KeyResultIn,
    KeyResultOut,
    ObjectiveState,
    PillarIn,
    PillarOut,
    PlanIn,
    PlanOut,
    Reason,
    StrategyHistory,
    StrategyOverview,
)


def clock():
    return datetime.now(UTC)


def reason(code, explanation):
    return Reason(code=code, explanation=explanation)


def validate_narrative(path):
    if not path:
        return
    if Path(path).suffix.lower() != ".md" or not is_safe_knowledge_path(path):
        raise ValueError("Güvenli göreli Vault Markdown yolu gerekli")
    # Validate structurally even when Vault is offline; real root also blocks symlink escapes.
    resolve_safe_vault_path(
        settings.resolved_obsidian_vault_path or Path("/tmp/forkos-unconfigured-vault"), path
    )


def plan_out(row, entity):
    return PlanOut(
        id=row.id,
        title=entity.title,
        start_at=row.start_at,
        end_at=row.end_at,
        status=row.status,
        summary=row.summary,
        narrative_path=row.narrative_path,
        revision=row.revision,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


async def plans(session):
    return [
        plan_out(row, entity)
        for row, entity in (
            await session.execute(
                select(StrategicPlan, Entity)
                .join(Entity, Entity.id == StrategicPlan.id)
                .order_by(Entity.created_at.desc(), StrategicPlan.id)
                .limit(100)
            )
        ).all()
    ]


async def pillars(session):
    return [
        PillarOut(
            id=row.id,
            plan_id=row.plan_id,
            title=entity.title,
            weight=row.weight,
            position=row.position,
        )
        for row, entity in (
            await session.execute(
                select(StrategicPillar, Entity)
                .join(Entity, Entity.id == StrategicPillar.id)
                .order_by(StrategicPillar.position, StrategicPillar.id)
                .limit(500)
            )
        ).all()
    ]


async def revision(session, row, entity, change_reason):
    item = await create_entity(
        session,
        type=StrategicPlanRevision.ENTITY_TYPE,
        title=f"{entity.title} · revizyon {row.revision}",
    )
    await session.flush()
    await session.refresh(entity)
    state = plan_out(row, entity).model_dump(mode="json")
    state["pillars"] = [
        p.model_dump(mode="json") for p in await pillars(session) if p.plan_id == row.id
    ]
    session.add(
        StrategicPlanRevision(
            id=item.id, plan_id=row.id, revision=row.revision, state=state, reason=change_reason
        )
    )
    await log_event(
        session,
        verb="strategic_plan.revised",
        entity_id=row.id,
        entity_type=row.ENTITY_TYPE,
        payload={
            "revision": row.revision,
            "revision_entity_id": str(item.id),
            "reason": change_reason,
        },
    )


async def save_plan(session, data: PlanIn, plan_id=None, *, commit=True):
    validate_narrative(data.narrative_path)
    values = data.model_dump(exclude={"title", "change_reason"})
    if plan_id:
        row = await session.scalar(
            select(StrategicPlan).where(StrategicPlan.id == plan_id).with_for_update()
        )
        if not row:
            raise ValueError("Plan bulunamadı")
        await touch_entity(session, row.id, title=data.title, search_text=data.summary or "")
        entity = await session.get(Entity, row.id)
        for key, value in values.items():
            setattr(row, key, value)
        row.revision += 1
        verb = "strategic_plan.updated"
    else:
        entity = await create_entity(
            session,
            type=StrategicPlan.ENTITY_TYPE,
            title=data.title,
            search_text=data.summary or "",
        )
        row = StrategicPlan(id=entity.id, revision=1, **values)
        session.add(row)
        verb = "strategic_plan.created"
    await session.flush()
    await revision(session, row, entity, data.change_reason)
    await log_event(
        session,
        verb=verb,
        entity_id=row.id,
        entity_type=row.ENTITY_TYPE,
        payload={"revision": row.revision},
    )
    if commit:
        await session.commit()
    else:
        await session.flush()
    return plan_out(row, entity)


async def save_pillar(session, plan_id, data: PillarIn, pillar_id=None, *, commit=True):
    plan = await session.scalar(
        select(StrategicPlan).where(StrategicPlan.id == plan_id).with_for_update()
    )
    if not plan:
        raise ValueError("Plan bulunamadı")
    if pillar_id:
        row = await session.get(StrategicPillar, pillar_id)
        if not row or row.plan_id != plan_id:
            raise ValueError("Alan bulunamadı")
        await touch_entity(session, row.id, title=data.title)
        entity = await session.get(Entity, row.id)
        row.position, row.weight = data.position, data.weight
    else:
        entity = await create_entity(session, type=StrategicPillar.ENTITY_TYPE, title=data.title)
        row = StrategicPillar(
            id=entity.id, plan_id=plan_id, weight=data.weight, position=data.position
        )
        session.add(row)
    await session.flush()
    plan.revision += 1
    await touch_entity(session, plan.id)
    parent = await session.get(Entity, plan.id)
    await revision(session, plan, parent, "Stratejik alan güncellendi")
    await log_event(
        session,
        verb="strategic_pillar.updated" if pillar_id else "strategic_pillar.created",
        entity_id=row.id,
        entity_type=row.ENTITY_TYPE,
        payload={"plan_id": str(plan_id)},
    )
    if commit:
        await session.commit()
    else:
        await session.flush()
    return PillarOut(id=row.id, plan_id=plan_id, **data.model_dump())


async def save_kr(
    session, goal_id, data: KeyResultIn, kr_id=None, *, commit=True, preserve_measurement=False
):
    if not await service.get_goal(session, goal_id):
        raise ValueError("Hedef bulunamadı")
    values = data.model_dump(exclude={"title", "source_config"})
    values["source_config"] = data.source_config.model_dump(mode="json", exclude_none=True)
    if data.source_key == "linked_completion":
        linked = await session.get(Entity, data.source_config.linked_entity_id)
        if not linked or linked.archived_at or linked.type not in {"goal_milestone", "study_topic"}:
            raise ValueError("Bağlı kayıt etkin hedef adımı veya öğrenme konusu olmalı")
    if kr_id:
        row = await session.scalar(select(KeyResult).where(KeyResult.id == kr_id).with_for_update())
        if not row or row.goal_id != goal_id:
            raise ValueError("Key Result bulunamadı")
        changed = row.manual_value != data.manual_value
        await touch_entity(session, row.id, title=data.title, search_text=data.description or "")
        entity = await session.get(Entity, row.id)
        for key, value in values.items():
            setattr(row, key, value)
        if (
            data.source_key == "manual"
            and data.manual_value is not None
            and not preserve_measurement
        ):
            row.measured_at = clock()
            changed = True
        verb = "key_result.updated"
    else:
        entity = await create_entity(
            session,
            type=KeyResult.ENTITY_TYPE,
            title=data.title,
            search_text=data.description or "",
        )
        row = KeyResult(
            id=entity.id,
            goal_id=goal_id,
            measured_at=clock() if data.manual_value is not None else None,
            **values,
        )
        session.add(row)
        changed = data.manual_value is not None
        verb = "key_result.created"
    await log_event(
        session,
        verb=verb,
        entity_id=row.id,
        entity_type=row.ENTITY_TYPE,
        payload={"goal_id": str(goal_id), "definition": data.model_dump(mode="json")},
    )
    if changed and data.source_key == "manual":
        await log_event(
            session,
            verb="key_result.manual_value_updated",
            entity_id=row.id,
            entity_type=row.ENTITY_TYPE,
            payload={"value": str(data.manual_value)},
        )
    if commit:
        await session.commit()
    else:
        await session.flush()
    return next(
        kr
        for objective in (await overview(session)).objectives
        for kr in objective.key_results
        if kr.id == row.id
    )


async def alignment(session, goals, milestones, *, days, now):
    from app.integrations.review_intelligence.sources import meaningful_events

    start = now - timedelta(days=days)
    events, truncated = await meaningful_events(session, start=start, end=now, limit=5000)
    # Same H5 whitelist; additionally uphold canonical positive media semantics.
    events = [
        e
        for e in events
        if e["verb"] != "media.consumed"
        or isinstance(e["payload"].get("amount"), (int, float))
        and e["payload"]["amount"] > 0
    ]
    active = {g.id: g for g in goals if g.status == "active"}
    milestone_goals = {m.id: m.goal_id for m in milestones}
    graph_rows = list(
        (
            await session.scalars(
                select(Link)
                .where(
                    Link.relation.in_(["advances_goal", "advances_goal_milestone", "belongs_to"])
                )
                .order_by(Link.id)
                .limit(10001)
            )
        ).all()
    )
    graph = defaultdict(set)
    supports = defaultdict(set)
    for link in graph_rows[:10000]:
        if link.relation == "advances_goal" and link.to_id in active:
            graph[link.from_id].add(link.to_id)
            supports[link.to_id].add(link.from_id)
        elif (
            link.relation == "advances_goal_milestone" and milestone_goals.get(link.to_id) in active
        ):
            graph[link.from_id].add(milestone_goals[link.to_id])
            supports[milestone_goals[link.to_id]].add(link.from_id)
    # Explicit belongs_to chains only; no semantic/title guesses. Five-hop bounded propagation.
    for _ in range(5):
        changed = False
        for link in graph_rows[:10000]:
            if link.relation == "belongs_to":
                before = len(graph[link.from_id])
                graph[link.from_id].update(graph[link.to_id])
                changed |= before != len(graph[link.from_id])
        if not changed:
            break
    counts, pillar_counts, linked, event_refs = (
        defaultdict(Decimal),
        defaultdict(Decimal),
        0,
        defaultdict(list),
    )
    refs = []
    for event in events:
        entity_id = UUID(event["entity_id"]) if event["entity_id"] else None
        matched = set(graph.get(entity_id, set()))
        if entity_id in active:
            matched.add(entity_id)
        if milestone_goals.get(entity_id) in active:
            matched.add(milestone_goals[entity_id])
        ref = f"event:{event['id']}"
        refs.append(ref)
        if matched:
            linked += 1
            share = Decimal(1) / len(matched)
            for goal_id in sorted(matched, key=str):
                counts[goal_id] += share
                event_refs[goal_id].append(ref)
                if active[goal_id].pillar_id:
                    pillar_counts[active[goal_id].pillar_id] += share
    warnings = []
    if truncated or len(graph_rows) > 10000:
        warnings.append(
            reason(
                "ALIGNMENT_TRUNCATED",
                "Hareket/ilişki tarama sınırı aşıldı; dağılım yalnız gözlenen örneklem.",
            )
        )

    def allocations(values):
        return [
            Allocation(
                entity_id=k,
                count=v,
                share_percent=round(float(v * 100 / len(events)), 1) if events else 0,
            )
            for k, v in sorted(values.items(), key=lambda x: str(x[0]))
        ]

    result = Alignment(
        window_days=days,
        start_at=start,
        end_at=now,
        eligible_count=len(events),
        linked_count=linked,
        unaligned_count=len(events) - linked,
        percent=round(linked * 100 / len(events)) if events and not warnings else None,
        objectives=allocations(counts),
        pillars=allocations(pillar_counts),
        warnings=warnings,
        evidence_refs=refs[:100],
    )
    return result, supports, event_refs


def weighted(values):
    measurable = [
        (Decimal(value), Decimal(weight)) for value, weight in values if value is not None
    ]
    return (
        round(sum(v * w for v, w in measurable) / sum(w for _, w in measurable))
        if measurable
        else None
    )


async def overview(session, *, days=30, now=None):
    now = now or clock()
    goals = await service.list_goals(session)
    from app.modules.goal.work import load_work

    work = await load_work(session, goals)
    plan_rows, pillar_rows = await plans(session), await pillars(session)
    goal_ids = [g.id for g in goals]
    rows = list(
        (
            await session.execute(
                select(KeyResult, Entity)
                .join(Entity, Entity.id == KeyResult.id)
                .where(KeyResult.goal_id.in_(goal_ids), Entity.archived_at.is_(None))
                .order_by(KeyResult.position, KeyResult.id)
                .limit(2001)
            )
        ).all()
    )
    warnings = (
        [
            reason(
                "STRATEGY_COLLECTION_LIMIT",
                "Hedef/plan/KR sınırına ulaşıldı; genel özet tam kapsam olarak sunulmaz.",
            )
        ]
        if len(goals) >= 500 or len(plan_rows) >= 100 or len(pillar_rows) >= 500 or len(rows) > 2000
        else []
    )
    rows = rows[:2000]
    context = await MetricContext.load(
        session,
        goal_ids,
        [
            UUID(r.source_config["linked_entity_id"])
            for r, _ in rows
            if r.source_config.get("linked_entity_id")
        ],
    )
    aligned, supports, activity = await alignment(
        session, goals, context.milestones, days=days, now=now
    )
    grouped = defaultdict(list)
    for kr, entity in rows:
        try:
            measurement = context.read(kr, now)
        except (ValueError, ArithmeticError, TypeError):
            from app.modules.goal.strategy_schemas import Measurement

            measurement = Measurement(
                current_value=None,
                progress_percent=None,
                reasons=[reason("PROVIDER_FAILED", "Sağlayıcı geçerli bir ölçüm üretemedi.")],
            )
        grouped[kr.goal_id].append(
            KeyResultOut(
                id=kr.id,
                goal_id=kr.goal_id,
                title=entity.title,
                measured_at=kr.measured_at,
                measurement=measurement,
                **{key: getattr(kr, key) for key in KeyResultIn.model_fields if key != "title"},
            )
        )
    from app.modules.goal.roadmap import read_many

    roadmaps = await read_many(session, goals)
    objectives = []
    for goal in goals:
        krs = grouped[goal.id]
        active = [k for k in krs if k.status in {"active", "completed"}]
        measurable = [k for k in active if k.measurement.progress_percent is not None]
        progress = weighted([(k.measurement.progress_percent, k.weight) for k in active])
        expected = weighted([(k.measurement.expected_percent, k.weight) for k in active])
        reasons = [r for k in active for r in k.measurement.reasons]
        confidence = (
            "high"
            if active and all(k.measurement.confidence == "high" for k in active)
            else "medium"
        )
        if (
            not active
            or len(measurable) < len(active)
            or any(k.measurement.confidence == "low" for k in active)
        ):
            confidence = "low"
        if not active:
            reasons.append(
                reason(
                    "NO_KEY_RESULTS",
                    "Ölçülebilir sonuç tanımlanmadı; milestone yüzdesi yerine kullanılmaz.",
                )
            )
        if len(measurable) < len(active):
            reasons.append(
                reason("PARTIAL_KR_COVERAGE", "Yüzde yalnız ölçülebilen KR ağırlıklarını kapsıyor.")
            )
        pace = "unknown" if progress is None else "not_applicable"
        trajectory_krs = [
            k
            for k in active
            if k.measurement.expected_percent is not None
            and k.measurement.progress_percent is not None
        ]
        if trajectory_krs:
            actual_pace = weighted(
                [(k.measurement.progress_percent, k.weight) for k in trajectory_krs]
            )
            gap = actual_pace - expected
            pace = "ahead" if gap > 10 else "behind" if gap < -10 else "on_track"
        objectives.append(
            ObjectiveState(
                roadmap_progress_percent=roadmaps[goal.id].percent,
                roadmap_present=not roadmaps[goal.id].legacy,
                roadmap_scope_count=roadmaps[goal.id].scope_count,
                roadmap_completed_scope_count=roadmaps[goal.id].completed_scope_count,
                goal=goal,
                work=work[goal.id],
                key_results=krs,
                strategic_progress_percent=progress,
                milestone_progress_percent=goal.progress_percent,
                measurable_count=len(measurable),
                active_kr_count=len(active),
                confidence=confidence,
                reasons=reasons,
                trajectory=pace,
                expected_percent=expected,
                linked_entity_ids=sorted(supports.get(goal.id, set()), key=str),
                evidence_refs=[f"entity:{goal.id}", *activity.get(goal.id, [])[:50]],
            )
        )

    pillar_weights = {p.id: p.weight for p in pillar_rows}

    def aggregate(id_, selected):
        selected = [o for o in selected if o.goal.status == "active"]
        measured = [
            o
            for o in selected
            if o.strategic_progress_percent is not None and o.measurable_count == o.active_kr_count
        ]
        enough = bool(selected) and len(measured) / len(selected) >= 0.8 and not warnings
        return Aggregate(
            id=id_,
            progress_percent=weighted(
                [
                    (
                        o.strategic_progress_percent,
                        o.goal.weight
                        * (
                            pillar_weights.get(o.goal.pillar_id, Decimal(1))
                            if o.goal.strategic_plan_id == id_
                            else Decimal(1)
                        ),
                    )
                    for o in measured
                ]
            )
            if enough
            else None,
            measurable_objectives=len(measured),
            active_objectives=len(selected),
            confidence="low"
            if not enough or any(o.confidence == "low" for o in measured)
            else "high"
            if len(measured) == len(selected) and all(o.confidence == "high" for o in measured)
            else "medium",
        )

    findings = []

    def finding(code, facts, refs, evidence):
        findings.append(
            Finding(
                code=code,
                entity_refs=refs,
                evidence_refs=evidence,
                observed_facts=facts,
                window_start=aligned.start_at,
                window_end=now,
            )
        )

    for objective in objectives:
        g = objective.goal
        if g.status != "active":
            continue
        refs = [f"entity:{g.id}"]
        evidence = objective.evidence_refs
        if objective.strategic_progress_percent is None:
            finding(
                "MISSING_MEASUREMENT",
                "Etkin hedef için ölçülebilir stratejik sonuç yok.",
                refs,
                evidence,
            )
        if g.priority == 3 and not objective.linked_entity_ids and not aligned.warnings:
            finding(
                "OBJECTIVE_WITHOUT_SUPPORT",
                "Yüksek öncelikli hedefe açıkça bağlanmış yürütme kaydı yok.",
                refs,
                evidence,
            )
        if (
            g.priority == 3
            and not activity.get(g.id)
            and g.created_at <= aligned.start_at
            and not aligned.warnings
        ):
            finding(
                "OBJECTIVE_INACTIVE",
                f"Son {days} günde bu yüksek öncelikli hedefe bağlı anlamlı hareket gözlenmedi.",
                refs,
                evidence,
            )
        if g.target_at and g.target_at < now:
            finding(
                "STALE_OBJECTIVE",
                "Etkin hedefin hedef tarihi geçti; kullanıcı incelemesi gerekli.",
                refs,
                evidence,
            )
        if (
            g.target_at
            and now <= g.target_at <= now + timedelta(days=14)
            and (objective.strategic_progress_percent or 0) < 20
        ):
            finding(
                "DEADLINE_WITHOUT_PROGRESS",
                "Hedef tarihi 14 gün içinde; ölçülen sonuç ilerlemesi %20 altında veya kullanılamıyor.",
                refs,
                evidence,
            )
        for kr in objective.key_results:
            if kr.status == "active" and kr.measurement.trajectory == "behind":
                finding(
                    "KR_BEHIND",
                    f"{kr.title}: ölçülen sonuç ilan edilen rotanın gerisinde.",
                    [f"entity:{kr.id}"],
                    kr.measurement.evidence_refs,
                )
        if (
            len(activity.get(g.id, [])) >= 5
            and objective.strategic_progress_percent is not None
            and objective.strategic_progress_percent < 20
        ):
            finding(
                "BUSY_NOT_PROGRESSING",
                f"En az 5 bağlı anlamlı hareket var; güncel sonuç ilerlemesi %{objective.strategic_progress_percent}. Bu gözlem nedensellik veya duraklama iddiası değildir.",
                refs,
                evidence,
            )
    if aligned.eligible_count >= 10 and aligned.percent is not None and aligned.percent < 50:
        finding(
            "EXECUTION_DRIFT",
            f"Son {days} günde anlamlı hareketlerin %{100 - aligned.percent} kadarı etkin hedeflere bağlı değil.",
            [],
            aligned.evidence_refs,
        )
    return StrategyOverview(
        calculated_at=now,
        plans=plan_rows,
        pillars=pillar_rows,
        objectives=objectives,
        plan_progress=[
            aggregate(p.id, [o for o in objectives if o.goal.strategic_plan_id == p.id])
            for p in plan_rows
        ],
        pillar_progress=[
            aggregate(p.id, [o for o in objectives if o.goal.pillar_id == p.id])
            for p in pillar_rows
        ],
        alignment=aligned,
        findings=findings,
        providers=PROVIDERS,
        warnings=warnings,
    )


async def history(session):
    from app.modules.review.models import Review

    revisions = (
        await session.execute(
            select(StrategicPlanRevision, Entity)
            .join(Entity, Entity.id == StrategicPlanRevision.id)
            .order_by(Entity.created_at.desc(), Entity.id)
            .limit(50)
        )
    ).all()
    reviews = (
        await session.execute(
            select(Review, Entity)
            .join(Entity, Entity.id == Review.id)
            .order_by(Entity.created_at.desc(), Entity.id)
            .limit(50)
        )
    ).all()
    items = [
        HistoryItem(
            id=r.id,
            kind="plan_revision",
            occurred_at=e.created_at,
            title=e.title,
            state={**r.state, "change_reason": r.reason},
        )
        for r, e in revisions
    ]
    snapshots = []
    for r, e in reviews:
        snapshot = r.stats.get("strategy_snapshot")
        if snapshot:
            item = HistoryItem(
                id=r.id,
                kind="review_snapshot",
                occurred_at=e.created_at,
                title=e.title,
                state=snapshot,
            )
            items.append(item)
            snapshots.append(item)
    comparable = False
    deltas, alignment_delta = {}, None
    comparison_reason = "İki karşılaştırılabilir strateji review snapshot'ı henüz yok."
    if len(snapshots) >= 2:
        newer, older = snapshots[0].state, snapshots[1].state

        def signature(x):
            return (
                x.get("schema_version"),
                x.get("method"),
                x.get("definitions"),
                x.get("plan_revisions"),
                x.get("alignment", {}).get("window_days"),
            )

        comparable = (
            signature(newer) == signature(older)
            and not newer.get("warnings")
            and not older.get("warnings")
            and all(
                o.get("confidence") != "low"
                and o.get("measurable_count") == o.get("active_kr_count")
                for x in (newer, older)
                for o in x.get("objectives", [])
                if o.get("goal", {}).get("status") == "active"
            )
            and not newer.get("alignment", {}).get("warnings")
            and not older.get("alignment", {}).get("warnings")
        )
        comparison_reason = (
            "Aynı sürüm, tanım, ağırlık, plan revizyonu ve ölçüm penceresi."
            if comparable
            else "Sürüm, metrik tanımı, ağırlık, plan revizyonu veya pencere farklı; delta hesaplanmadı."
        )
        if comparable:
            previous = {o["goal"]["id"]: o for o in older["objectives"]}
            for o in newer["objectives"]:
                a, b = (
                    o["strategic_progress_percent"],
                    previous.get(o["goal"]["id"], {}).get("strategic_progress_percent"),
                )
                if a is not None and b is not None:
                    deltas[o["goal"]["id"]] = a - b
            a, b = newer["alignment"]["percent"], older["alignment"]["percent"]
            alignment_delta = a - b if a is not None and b is not None else None
    return StrategyHistory(
        truncated=len(revisions) >= 50 or len(reviews) >= 50,
        items=sorted(items, key=lambda i: (i.occurred_at, str(i.id)), reverse=True)[:100],
        comparable=comparable,
        comparison_reason=comparison_reason,
        progress_deltas=deltas,
        alignment_delta=alignment_delta,
    )


def snapshot(read):
    data = read.model_dump(mode="json")
    data["plan_revisions"] = {str(p.id): p.revision for p in read.plans}
    data["definitions"] = [
        {
            "goal": str(o.goal.id),
            "status": o.goal.status,
            "weight": str(o.goal.weight),
            "plan": str(o.goal.strategic_plan_id),
            "pillar": str(o.goal.pillar_id),
            "krs": [
                k.model_dump(mode="json", exclude={"measurement", "manual_value", "measured_at"})
                for k in o.key_results
            ],
        }
        for o in read.objectives
    ]
    return data
