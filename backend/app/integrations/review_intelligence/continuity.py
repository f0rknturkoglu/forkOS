"""H5 süreklilik (continuity) — "nerede kalmıştım?" (§18/§112).

Süreklilik iki şeyi AYIRIR (§30):

```text
KULLANICI HAREKETİ   sayılan fiiller (contributions.COUNTED_VERBS)
ZAMAN / DIŞ DURUM    son tarihler yaklaştı, görev gecikti, RSS birikti,
                     plan geçti, yeni ilan geldi, bildirim birikti
```

Kullanıcı hiçbir şey yapmamış olsa bile ikinci grup değişir ve bu görünür.
Süreklilik **neden** hareketin durduğunu ASLA çıkarsamaz (§29): "yoruldun",
"motivasyonunu kaybettin" gibi bir cümle üretilmez. Yalnızca olgu söylenir.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.review_intelligence import consolidation as consolidation_svc
from app.integrations.review_intelligence import policy as policy_svc
from app.integrations.review_intelligence import sources as source_svc
from app.integrations.review_intelligence.models import (
    MAX_H5_ACTIVE_THREADS,
    MAX_H5_ATTENTION,
    MAX_H5_COMPLETED_RECENT,
    MAX_H5_DEADLINES,
    MAX_H5_INSIGHTS,
    MAX_H5_OPEN_LOOPS,
    MAX_INSIGHT_TEXT,
    STALLED_PROJECT_DAYS,
    UNREAD_ACCUMULATION_THRESHOLD,
    UPCOMING_DEADLINE_DAYS,
    AttentionCandidate,
    CanonicalOpenLoop,
    Collector,
    ContinuityAnchor,
    ContinuityBundle,
    Coverage,
    LearningResume,
    ReviewInsight,
    SourceRef,
    ThreadRef,
    UnreadAccumulation,
)

#: Durum değişikliği için BELGELENMİŞ küçük fiil uzantısı (§25).
#: Yalnızca `state_changes` içinde kullanılır; süreklilik ÇAPASI sayılan
#: fiillerle bulunur, bu uzantıyla değil.
STATE_CHANGE_VERBS: tuple[str, ...] = ("todo.created",)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _insight(
    *,
    insight_type: str,
    text: str,
    support_refs: list[str],
    status: str = "fact",
    temporal_start: str | None = None,
    temporal_end: str | None = None,
) -> ReviewInsight:
    return ReviewInsight(
        type=insight_type,  # type: ignore[arg-type]
        text=text[:MAX_INSIGHT_TEXT],
        support_refs=[ref for ref in support_refs if ref],
        source_count=len([ref for ref in support_refs if ref]),
        status=status,  # type: ignore[arg-type]
        temporal_start=temporal_start,
        temporal_end=temporal_end,
    )


def _loop(
    *,
    kind: str,
    title: str,
    entity_id: str | None,
    detail: str | None,
    due_at: str | None,
    support_refs: list[str],
) -> CanonicalOpenLoop:
    return CanonicalOpenLoop(
        kind=kind,  # type: ignore[arg-type]
        title=title,
        entity_id=entity_id,
        detail=detail,
        due_at=due_at,
        support_refs=support_refs,
    )


async def resolve_anchor(
    session: AsyncSession,
    collector: Collector,
    *,
    since: datetime | None,
    focus_entity_id: uuid.UUID | None,
    period_start: datetime,
    moment: datetime,
) -> ContinuityAnchor:
    """Süreklilik çapasını belirler (§24/§26/§27).

    Açık `since` varsa o kullanılır. Yoksa SON ANLAMLI İNSAN HAREKETİ aranır;
    o da yoksa SON REVIEW'ın bittiği gün çapa olur (`previous_review`) — bu
    uydurma değil, gerçek bir damgadır. Hiçbiri yoksa `fallback` +
    `NO_MEANINGFUL_ACTIVITY` uyarısı.
    """
    if since is not None:
        return ContinuityAnchor(kind="explicit", timestamp=since.isoformat())

    if focus_entity_id is not None:
        event = await source_svc.last_meaningful_event_for_entities(
            session, entity_ids=[focus_entity_id]
        )
    else:
        event = await source_svc.last_meaningful_event(session)

    if event is None:
        # Sayılan insan hareketi yok: uydurma yapılmaz. Varsa SON REVIEW'ın
        # bittiği an gerçek bir çapadır ("son gözden geçirmeden beri sessiz").
        previous = await source_svc.previous_review(
            session, kind=None, before=moment.date()
        )
        if previous is not None:
            # Review dönemi YEREL gündür; damga saat dilimli olmalı (§22).
            # Devam eden bir review geleceğe taşmasın: çapa "şimdi"yi geçemez.
            anchor_day = min(date.fromisoformat(previous["period_end"]), moment.date())
            anchor_dt = source_svc.day_bounds(anchor_day)[0]
            ref = collector.add_source(
                SourceRef(
                    ref=f"review:{previous['id']}",
                    domain="operational",
                    kind="review",
                    title=f"{previous['kind']} review",
                    timestamp=anchor_dt.isoformat(),
                )
            )
            return ContinuityAnchor(
                kind="previous_review",
                timestamp=anchor_dt.isoformat(),
                source_ref=ref,
            )
        collector.warn(
            "NO_MEANINGFUL_ACTIVITY",
            "sınırlı geçmiş taramasında sayılan kullanıcı hareketi bulunamadı",
        )
        return ContinuityAnchor(kind="fallback", timestamp=period_start.isoformat())

    ref = collector.add_source(
        SourceRef(
            ref=f"event:{event['id']}",
            domain="operational",
            kind="event",
            title=event.get("title") or event.get("verb"),
            timestamp=_iso(event.get("occurred_at")),
            entity_id=event.get("entity_id"),
        )
    )
    return ContinuityAnchor(
        kind="last_meaningful_activity",
        timestamp=_iso(event["occurred_at"]) or period_start.isoformat(),
        source_ref=ref,
        entity_id=event.get("entity_id"),
        verb=event.get("verb"),
    )


async def build_continuity(
    session: AsyncSession,
    collector: Collector,
    *,
    since: datetime | None,
    until: datetime | None,
    focus_entity_id: uuid.UUID | None,
    include_knowledge: bool,
    now: datetime | None = None,
) -> tuple[ContinuityBundle, Coverage]:
    """Süreklilik paketini kurar. Global ya da tek entity'ye kapsanmış."""
    moment = now or datetime.now(UTC)
    period = source_svc.resolve_period(
        mode="continuity", since=since, until=until, reference_date=None, now=moment
    )
    collector.step("period_resolved", considered=1, accepted=1)

    focus_entity = None
    if focus_entity_id is not None:
        focus_entity = await source_svc.load_entity(session, focus_entity_id)
        if focus_entity is None:
            from app.integrations.review_intelligence.models import ReviewIntelligenceError

            raise ReviewIntelligenceError("INVALID_FOCUS_ENTITY", "focus entity not found")
        collector.add_source(
            SourceRef(
                ref=f"entity:{focus_entity['id']}",
                domain="operational",
                kind="entity",
                title=focus_entity["title"],
                timestamp=focus_entity.get("updated_at"),
                entity_id=focus_entity["id"],
            )
        )
        collector.manifest.entities_considered += 1

    anchor = await resolve_anchor(
        session,
        collector,
        since=since,
        focus_entity_id=focus_entity_id,
        period_start=period.start,
        moment=moment,
    )
    anchor_dt = datetime.fromisoformat(anchor.timestamp)
    gap_hours = max((moment - anchor_dt).total_seconds() / 3600.0, 0.0)

    # --- anlamlı hareketler -------------------------------------------------
    events, events_truncated = await source_svc.meaningful_events(
        session, start=anchor_dt, end=moment
    )
    collector.manifest.events_considered = len(events)
    if events_truncated:
        collector.warn("EVENT_SCAN_TRUNCATED", "süreklilik penceresi tavanına ulaştı")
        collector.truncated = True
    collector.step(
        "events_loaded", considered=len(events), accepted=len(events), truncated=events_truncated
    )

    recent_completed: list[ReviewInsight] = []
    for event in events[:MAX_H5_COMPLETED_RECENT]:
        if event["verb"] not in {"todo.completed", "study.topic_completed", "review.completed", "habit.checked"}:
            continue
        ref = collector.add_source(
            SourceRef(
                ref=f"event:{event['id']}",
                domain="operational",
                kind="event",
                title=event.get("title") or event.get("verb"),
                timestamp=_iso(event.get("occurred_at")),
                entity_id=event.get("entity_id"),
            )
        )
        recent_completed.append(
            _insight(
                insight_type="win",
                text=f"Tamamlandı: {event.get('title') or event['verb']}",
                support_refs=[ref],
                temporal_start=_iso(event.get("occurred_at")),
            )
        )
        if len(recent_completed) >= MAX_H5_INSIGHTS // 2:
            break

    last_event = events[0] if events else None
    last_meaningful = None
    learning_resume = None
    if last_event is not None:
        last_meaningful = {
            "verb": last_event["verb"],
            "title": last_event.get("title") or "",
            "occurred_at": _iso(last_event.get("occurred_at")),
            "entity_id": last_event.get("entity_id"),
        }
        if last_event["verb"] == "pomodoro.completed":
            payload = last_event.get("payload") or {}
            topic = payload.get("topic") or None
            minutes = payload.get("minutes")
            related_todo_id = None
            if topic:
                index = await source_svc.todo_title_index(session, limit=500)
                related_todo_id = index.get(policy_svc.normalize_for_identity(str(topic)))
            learning_resume = LearningResume(
                topic=str(topic) if topic else None,
                minutes=int(minutes) if isinstance(minutes, (int, float)) else None,
                last_activity_at=_iso(last_event.get("occurred_at")),
                related_todo_id=related_todo_id,
                study_area=None,
                support_refs=[f"event:{last_event['id']}"],
            )

    # --- zaman / dış durum değişiklikleri ----------------------------------
    state_changes: list[ReviewInsight] = []
    time_sensitive_changes: list[ReviewInsight] = []
    unread = await source_svc.rss_accumulation(session, anchor=anchor_dt, now=moment)
    unread_ref = collector.add_source(
        SourceRef(
            ref=f"aggregate:rss_unread_since:{anchor.timestamp}",
            domain="aggregate",
            kind="rss_unread",
            title="okunmamış içerik",
            timestamp=anchor.timestamp,
        )
    )
    if unread["new_unread_since_anchor"] > 0:
        state_changes.append(
            _insight(
                insight_type="change",
                text=(
                    f"Bu arada {unread['new_unread_since_anchor']} yeni okunmamış içerik geldi "
                    f"(toplam okunmamış: {unread['current_unread_total']})."
                ),
                support_refs=[unread_ref],
                temporal_start=anchor.timestamp,
                temporal_end=moment.isoformat(),
            )
        )

    opportunities = await source_svc.opportunity_changes(
        session, start=anchor_dt, end=moment, limit=MAX_H5_INSIGHTS
    )
    for opportunity in opportunities:
        ref = collector.add_source(
            SourceRef(
                ref=f"entity:{opportunity['id']}",
                domain="operational",
                kind="opportunity",
                title=opportunity["title"],
                timestamp=opportunity.get("found_at"),
                entity_id=opportunity["id"],
            )
        )
        state_changes.append(
            _insight(
                insight_type="change",
                text=f"Yeni kayıt: {opportunity['title']} ({opportunity.get('kind') or 'ilan'})",
                support_refs=[ref],
                temporal_start=opportunity.get("found_at"),
            )
        )
        if opportunity.get("deadline_at"):
            remaining = (datetime.fromisoformat(opportunity["deadline_at"]) - moment).days
            if 0 <= remaining <= UPCOMING_DEADLINE_DAYS:
                time_sensitive_changes.append(
                    _insight(
                        insight_type="time_sensitive",
                        text=f"{opportunity['title']} için son tarih {remaining} gün içinde.",
                        support_refs=[ref],
                        temporal_end=opportunity["deadline_at"],
                    )
                )

    notifications = await source_svc.important_notifications(
        session, start=anchor_dt, end=moment, limit=MAX_H5_ATTENTION
    )
    for notification in notifications:
        ref = collector.add_source(
            SourceRef(
                ref=f"notification:{notification['id']}",
                domain="operational",
                kind="notification",
                title=notification["title"],
                timestamp=notification["created_at"],
            )
        )
        state_changes.append(
            _insight(
                insight_type="change",
                text=f"Bildirim: {notification['title']}",
                support_refs=[ref],
                temporal_start=notification["created_at"],
            )
        )

    # --- son tarihler ve gecikmeler ---------------------------------------
    deadlines, deadlines_truncated = await source_svc.upcoming_deadlines(
        session, now=moment, days=UPCOMING_DEADLINE_DAYS, limit=MAX_H5_DEADLINES
    )
    collector.manifest.deadlines_considered = len(deadlines)
    if deadlines_truncated:
        collector.warn("DEADLINE_SCAN_TRUNCATED")
        collector.truncated = True
    collector.step("deadlines_loaded", considered=len(deadlines), accepted=len(deadlines))
    for deadline in deadlines:
        if deadline.get("entity_id"):
            collector.add_source(
                SourceRef(
                    ref=f"entity:{deadline['entity_id']}",
                    domain="operational",
                    kind="deadline",
                    title=deadline["title"],
                    timestamp=deadline.get("due_at"),
                    entity_id=deadline["entity_id"],
                )
            )

    overdue_rows = await source_svc.newly_overdue_todos(
        session, start=anchor_dt, end=moment, limit=MAX_H5_OPEN_LOOPS
    )
    newly_overdue = [
        _loop(
            kind="todo",
            title=row["title"],
            entity_id=row["id"],
            detail="son tarihi bu pencerede geçti",
            due_at=row["due_at"],
            support_refs=[collector.add_source(
                SourceRef(
                    ref=f"entity:{row['id']}",
                    domain="operational",
                    kind="todo",
                    title=row["title"],
                    timestamp=row["due_at"],
                    entity_id=row["id"],
                )
            )],
        )
        for row in overdue_rows
    ]

    passed_rows = await source_svc.passed_plan_open_tasks(session, now=moment, limit=MAX_H5_OPEN_LOOPS)
    passed_plans = [
        _loop(
            kind="todo",
            title=row["title"],
            entity_id=row["todo_id"],
            detail=f"planlanan zaman geçti ({row['day']}) ama görev hâlâ açık",
            due_at=None,
            support_refs=[collector.add_source(
                SourceRef(
                    ref=f"plan_slot:{row['plan_slot_id']}",
                    domain="operational",
                    kind="plan_slot",
                    title=row["title"],
                    entity_id=row["todo_id"],
                    locator=row["day"],
                )
            )],
        )
        for row in passed_rows
    ]

    # --- kanonik açık döngüler --------------------------------------------
    open_todos = await source_svc.open_todos(session, limit=MAX_H5_OPEN_LOOPS)
    open_loops = [
        _loop(
            kind="todo",
            title=row["title"],
            entity_id=row["id"],
            detail=f"durum: {row['status']}",
            due_at=row["due_at"],
            support_refs=[f"entity:{row['id']}"],
        )
        for row in open_todos
    ]

    projects = await source_svc.active_projects(session, limit=MAX_H5_OPEN_LOOPS)
    collector.manifest.projects_considered = len(projects)
    collector.step("projects_checked", considered=len(projects), accepted=len(projects))

    project_ids = [uuid.UUID(project["id"]) for project in projects]
    activity = await source_svc.project_last_activity(session, project_ids=project_ids)

    stalled: list[ReviewInsight] = []
    for project in projects:
        if not project["next_action"]:
            open_loops.append(
                _loop(
                    kind="project_next_action",
                    title=project["title"],
                    entity_id=project["id"],
                    detail="sonraki adım tanımlı değil",
                    due_at=None,
                    support_refs=[f"entity:{project['id']}"],
                )
            )
        last_at = activity.get(project["id"])
        days_since = None
        if last_at is not None:
            days_since = max((moment - last_at).days, 0)
        if days_since is not None and days_since >= STALLED_PROJECT_DAYS:
            stalled.append(
                _insight(
                    insight_type="stalled",
                    text=(
                        f"'{project['title']}' projesinde {days_since} gündür kayıtlı anlamlı hareket yok."
                    ),
                    support_refs=[f"entity:{project['id']}"],
                    status="fact",
                )
            )

    milestones = await source_svc.overdue_milestones(session, now=moment, limit=MAX_H5_OPEN_LOOPS)
    for milestone in milestones:
        open_loops.append(
            _loop(
                kind="milestone",
                title=milestone["title"],
                entity_id=milestone["id"],
                detail="kilometre taşı gecikti",
                due_at=milestone["due_at"],
                support_refs=[f"entity:{milestone['id']}"],
            )
        )

    # --- dikkat adayları ---------------------------------------------------
    attention: list[AttentionCandidate] = []
    for row in overdue_rows:
        attention.append(
            AttentionCandidate(
                reason="overdue",
                text=f"{row['title']} gecikti.",
                support_refs=[f"entity:{row['id']}"],
                entity_id=row["id"],
                due_at=row["due_at"],
            )
        )
    for deadline in deadlines:
        entity_id = deadline.get("entity_id")
        if not entity_id:
            # Kanonik referansı olmayan son tarih ADAY olarak da üretilmez
            # (§H5.1): kaynaksız aday, kaynaksız olgu kadar yanıltıcıdır.
            continue
        reason = policy_svc.deadline_reason(int(deadline.get("remaining_days") or 0))
        attention.append(
            AttentionCandidate(
                reason=reason,
                text=(
                    f"{deadline['title']} için son tarih "
                    f"{deadline.get('remaining_days')} gün içinde."
                ),
                support_refs=[f"entity:{entity_id}"],
                entity_id=entity_id,
                due_at=deadline.get("due_at"),
                remaining_days=deadline.get("remaining_days"),
            )
        )
    for row in passed_rows:
        attention.append(
            AttentionCandidate(
                reason="passed_plan_open",
                text=f"{row['title']} için planlanan zaman geçti, görev hâlâ açık.",
                support_refs=[f"plan_slot:{row['plan_slot_id']}"],
                entity_id=row["todo_id"],
            )
        )
    if unread["new_unread_since_anchor"] >= UNREAD_ACCUMULATION_THRESHOLD:
        attention.append(
            AttentionCandidate(
                reason="unread_accumulation",
                text=f"{unread['new_unread_since_anchor']} yeni okunmamış içerik birikti.",
                support_refs=[unread_ref],
            )
        )
    for project in projects:
        if not project["next_action"]:
            attention.append(
                AttentionCandidate(
                    reason="project_without_next_action",
                    text=f"'{project['title']}' projesinin sonraki adımı tanımlı değil.",
                    support_refs=[f"entity:{project['id']}"],
                    entity_id=project["id"],
                )
            )
    for insight in stalled:
        attention.append(
            AttentionCandidate(
                reason="project_inactive",
                text=insight.text,
                support_refs=list(insight.support_refs),
            )
        )
    attention.sort(
        key=lambda item: (policy_svc.attention_rank(item.reason), item.text)
    )
    attention = attention[:MAX_H5_ATTENTION]

    # --- iş parçaları ------------------------------------------------------
    threads: list[ThreadRef] = []
    if learning_resume is not None and learning_resume.topic:
        threads.append(
            ThreadRef(
                kind="learning",
                title=learning_resume.topic,
                entity_id=learning_resume.related_todo_id,
                detail=(
                    f"son odak: {learning_resume.minutes} dk"
                    if learning_resume.minutes
                    else "son odak kaydı"
                ),
                support_refs=list(learning_resume.support_refs),
            )
        )
    for candidate in attention[:MAX_H5_ACTIVE_THREADS]:
        threads.append(
            ThreadRef(
                kind="deadline" if candidate.reason.startswith("deadline") else "todo",
                title=candidate.text,
                entity_id=candidate.entity_id,
                detail=policy_svc.ATTENTION_LABELS.get(candidate.reason),
                support_refs=list(candidate.support_refs),
            )
        )
    for project in projects[:2]:
        threads.append(
            ThreadRef(
                kind="project",
                title=project["title"],
                entity_id=project["id"],
                detail=project["next_action"] or "sonraki adım yok",
                support_refs=[f"entity:{project['id']}"],
            )
        )
    threads = threads[:MAX_H5_ACTIVE_THREADS]

    # --- bilgi sağlığı (isteğe bağlı) --------------------------------------
    knowledge_changes: list[ReviewInsight] = []
    resurface: list[Any] = []
    if include_knowledge and consolidation_svc.knowledge_scope(collector):
        knowledge_ids = [focus_entity_id] if focus_entity_id else project_ids
        health = await consolidation_svc.stale_managed_notes(
            session, collector, entity_ids=[item for item in knowledge_ids if item], now=moment
        )
        for candidate in health:
            knowledge_changes.append(
                _insight(
                    insight_type="knowledge_health",
                    text=candidate.text,
                    support_refs=list(candidate.support_refs),
                    status="candidate",
                )
            )
        resurface = await consolidation_svc.resurface_candidates(
            session, collector, entity_ids=[item for item in knowledge_ids if item], now=moment
        )
        consolidation_svc.report_index_conflicts(collector)
    else:
        collector.step("knowledge_health_checked", considered=0, accepted=0)

    bundle = ContinuityBundle(
        anchor=anchor,
        activity_gap_hours=round(gap_hours, 2),
        last_meaningful_activity=last_meaningful,
        recent_completed=recent_completed,
        state_changes=state_changes[:MAX_H5_INSIGHTS],
        time_sensitive_changes=time_sensitive_changes[:MAX_H5_INSIGHTS],
        newly_overdue=newly_overdue,
        upcoming_deadlines=deadlines,
        unread_accumulation=UnreadAccumulation(
            new_unread_since_anchor=unread["new_unread_since_anchor"],
            current_unread_total=unread["current_unread_total"],
            top_sources=unread["top_sources"],
            support_refs=[unread_ref],
        ),
        passed_plans_still_open=passed_plans,
        open_loops=open_loops[:MAX_H5_OPEN_LOOPS],
        active_threads=threads,
        learning_resume=learning_resume,
        stalled_projects=stalled,
        attention_candidates=attention,
        knowledge_changes=knowledge_changes,
        resurface_candidates=resurface,
        focus_entity=focus_entity,
    )

    coverage = Coverage(
        period_start=anchor.timestamp,
        period_end=moment.isoformat(),
        days=max((moment - anchor_dt).days, 0),
        partial=True,
        comparable=False,
    )
    return bundle, coverage


__all__ = ["STATE_CHANGE_VERBS", "build_continuity", "resolve_anchor"]
