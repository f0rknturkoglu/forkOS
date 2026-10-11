"""H5 gözden geçirme modları: gün kapanışı, haftalık, dönem deltası (§113).

Mevcut Review altyapısı YENİDEN KULLANILIR (§12/§41):

```text
review.service.preview(kind="daily"|"weekly")  → deterministik metrikler
Review.stats / Review.decisions                → kabul edilmiş tarihsel kayıt
Review.decisions["_receipts"]                  → öncelik → Todo kimliği
```

İkinci bir Review alt sistemi KURULMAZ; H5 yalnızca okur ve yorumlar.
"""

from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Link
from app.integrations.review_intelligence import consolidation as consolidation_svc
from app.integrations.review_intelligence import policy as policy_svc
from app.integrations.review_intelligence import sources as source_svc
from app.integrations.review_intelligence.models import (
    MAX_H5_BODY_OF_WORK,
    MAX_H5_COMPLETED_RECENT,
    MAX_H5_DEADLINES,
    MAX_H5_INSIGHTS,
    MAX_H5_OPEN_LOOPS,
    MAX_H5_PRIORITIES,
    MAX_INSIGHT_TEXT,
    STALLED_PROJECT_DAYS,
    UPCOMING_DEADLINE_DAYS,
    CanonicalOpenLoop,
    Collector,
    ConsolidationBundle,
    Coverage,
    DailyCloseBundle,
    PeriodDeltaBundle,
    ReviewInsight,
    SourceRef,
    WeeklyReviewBundle,
)
from app.modules.opportunity.models import ApplicationHistory
from app.modules.pomodoro.models import PomodoroSession


def _insight(
    *,
    insight_type: str,
    text: str,
    support_refs: list[str],
    status: str = "fact",
    temporal_start: str | None = None,
    temporal_end: str | None = None,
) -> ReviewInsight:
    refs = [ref for ref in support_refs if ref]
    return ReviewInsight(
        type=insight_type,  # type: ignore[arg-type]
        text=text[:MAX_INSIGHT_TEXT],
        support_refs=refs,
        status=status,  # type: ignore[arg-type]
        temporal_start=temporal_start,
        temporal_end=temporal_end,
    )


def _loop(
    *, kind: str, title: str, entity_id: str | None, detail: str | None, due_at: str | None,
    support_refs: list[str],
) -> CanonicalOpenLoop:
    return CanonicalOpenLoop(
        kind=kind,  # type: ignore[arg-type]
        title=title,
        entity_id=entity_id,
        detail=detail,
        due_at=due_at,
        support_refs=[ref for ref in support_refs if ref],
    )


async def _preview(session: AsyncSession, kind: str, period_start) -> dict[str, Any]:
    from app.modules.review import service as review_svc

    preview = await review_svc.preview(session, kind, period_start)
    return preview.model_dump(mode="json")


async def _completed_rows(session: AsyncSession, kind: str, period_start: Any) -> list[dict[str, Any]]:
    """Tamamlanma satırları — kanonik review servisinden (§H5.1).

    Satırlar `event_id` taşır: tamamlanma olgusunun kanıtı append-only
    Event'tır, güncel Entity DEĞİLDİR.
    """
    from app.modules.review import service as review_svc

    return await review_svc.completed_todo_rows(session, kind, period_start)


def _completion_refs(collector: Collector, row: dict[str, Any]) -> list[str]:
    """Tamamlanma için kanonik destek referansları (§H5.1).

    `event:<id>` TEK BAŞINA yeterlidir: Todo/Entity silinse bile Event kalır.
    Entity hâlâ duruyorsa bağlam olarak `entity:<id>` de eklenir. Kaynaksız
    olgu üretilmez; bu yüzden bu fonksiyon ASLA boş liste döndürmez.
    """
    refs = [
        collector.add_source(
            SourceRef(
                ref=f"event:{row['event_id']}",
                domain="operational",
                kind="event",
                title=f"Tamamlandı: {row['title']}",
                timestamp=row.get("completed_at"),
                entity_id=row.get("id"),
            )
        )
    ]
    if row.get("id"):
        refs.append(f"entity:{row['id']}")
    return refs


async def _open_loops_and_projects(
    session: AsyncSession, collector: Collector, *, now: datetime
) -> tuple[list[CanonicalOpenLoop], list[ReviewInsight], list[dict[str, Any]], list[uuid.UUID]]:
    """Kanonik açık döngüler + durağan proje sinyalleri (paylaşılan)."""
    open_todos = await source_svc.open_todos(session, limit=MAX_H5_OPEN_LOOPS)
    loops = [
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
            loops.append(
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
        if last_at is None:
            continue
        days_since = max((now - last_at).days, 0)
        if days_since >= STALLED_PROJECT_DAYS:
            stalled.append(
                _insight(
                    insight_type="stalled",
                    text=f"'{project['title']}' projesinde {days_since} gündür kayıtlı anlamlı hareket yok.",
                    support_refs=[f"entity:{project['id']}"],
                )
            )
    return loops[:MAX_H5_OPEN_LOOPS], stalled, projects, project_ids


async def _promotion_bundle(
    session: AsyncSession,
    collector: Collector,
    *,
    period_start: datetime,
    period_end: datetime,
    start_day: date,
    end_day: date,
    focus_entity_id: uuid.UUID | None,
    project_ids: list[uuid.UUID],
    include_daily_notes: bool,
    include_knowledge: bool,
    now: datetime,
) -> tuple[list, list, list, list, list[dict[str, Any]]]:
    """Konsolidasyon adaylarını (terfi, açık döngü, bilgi sağlığı, yeniden yüzey) üretir."""
    fragments: list[dict[str, Any]] = []
    daily_notes: list[dict[str, Any]] = []

    if include_daily_notes:
        days = source_svc.daily_note_days(start_day, end_day)
        collector.manifest.daily_notes_expected = len(days)
        for day in days:
            note = source_svc.read_daily_note(day)
            if note is None:
                continue
            collector.manifest.daily_notes_found += 1
            collector.manifest.vault_sources.append(note["ref"])
            daily_notes.append(note)
            fragments.append({"ref": note["ref"], "text": note["excerpt"], "entity_id": None})
        missing = collector.manifest.daily_notes_expected - collector.manifest.daily_notes_found
        collector.manifest.daily_notes_missing = missing
        if missing > 0:
            collector.warn("MISSING_DAILY_NOTES", f"{missing} günlük not yok")
        collector.step(
            "daily_notes_loaded",
            considered=collector.manifest.daily_notes_expected,
            accepted=collector.manifest.daily_notes_found,
        )

    events, truncated = await source_svc.meaningful_events(
        session, start=period_start, end=period_end, limit=MAX_H5_BODY_OF_WORK
    )
    collector.manifest.events_considered += len(events)
    if truncated:
        collector.warn("EVENT_SCAN_TRUNCATED")
        collector.truncated = True
    for event in events[:MAX_H5_BODY_OF_WORK]:
        payload = event.get("payload") or {}
        summary = " ".join(
            str(value) for value in [event.get("title"), payload.get("title"), payload.get("topic")]
            if value
        ).strip()
        if not summary:
            continue
        fragments.append(
            {
                "ref": f"event:{event['id']}",
                "text": f"{event['verb']}: {summary}",
                "entity_id": event.get("entity_id"),
            }
        )

    episode_items = await source_svc.sealed_episode_items(
        session, start=period_start, end=period_end, limit=20
    )
    for ep_item in episode_items:
        fragments.append(
            {
                "ref": ep_item["ref"],
                "text": f"{ep_item['kind']}: {ep_item['text']}",
                "entity_id": None,
            }
        )

    promotions = await consolidation_svc.extract_promotion_candidates(
        session, collector, fragments=fragments, focus_entity_id=focus_entity_id
    )
    loops = await consolidation_svc.possible_open_loops(session, collector, candidates=promotions)

    health: list = []
    resurface: list = []
    if include_knowledge and consolidation_svc.knowledge_scope(collector):
        knowledge_ids = [focus_entity_id] if focus_entity_id else project_ids
        knowledge_ids = [item for item in knowledge_ids if item is not None]
        health = await consolidation_svc.stale_managed_notes(
            session, collector, entity_ids=knowledge_ids, now=now
        )
        health += await consolidation_svc.supersession_candidates(
            session, collector, candidates=promotions, focus_entity_id=focus_entity_id
        )
        resurface = await consolidation_svc.resurface_candidates(
            session, collector, entity_ids=knowledge_ids, now=now
        )
        consolidation_svc.report_index_conflicts(collector)
    else:
        collector.step("knowledge_health_checked", considered=0, accepted=0)
    return promotions, loops, health, resurface, daily_notes


async def build_daily_close(
    session: AsyncSession,
    collector: Collector,
    *,
    reference_date: Any,
    include_knowledge: bool,
    now: datetime | None = None,
) -> tuple[DailyCloseBundle, Coverage]:
    """Gün kapanışı (§49): küçük, salt-okunur ritüel."""
    moment = now or datetime.now(UTC)
    period = source_svc.resolve_period(
        mode="daily_close", since=None, until=None, reference_date=reference_date, now=moment
    )
    day = period.start_day
    collector.step("period_resolved", considered=1, accepted=1)

    preview = await _preview(session, "daily", day)
    collector.manifest.reviews_considered += 1
    collector.add_source(
        SourceRef(
            ref=f"aggregate:review_preview:daily:{day.isoformat()}",
            domain="aggregate",
            kind="review_preview",
            title=f"gün özeti {day.isoformat()}",
            timestamp=period.start.isoformat(),
        )
    )
    collector.step("review_preview_loaded", considered=1, accepted=1)

    completed_rows = await _completed_rows(session, "daily", day)
    completed_outcomes = [
        _insight(
            insight_type="win",
            text=f"Tamamlandı: {row['title']}",
            support_refs=_completion_refs(collector, row),
            temporal_start=row.get("completed_at"),
        )
        for row in completed_rows[:MAX_H5_COMPLETED_RECENT]
    ]

    loops, stalled, projects, project_ids = await _open_loops_and_projects(
        session, collector, now=moment
    )
    overdue_rows = await source_svc.newly_overdue_todos(
        session, start=period.start, end=moment, limit=MAX_H5_OPEN_LOOPS
    )
    newly_overdue = [
        _loop(
            kind="todo",
            title=row["title"],
            entity_id=row["id"],
            detail="bugün son tarihi geçti",
            due_at=row["due_at"],
            support_refs=[f"entity:{row['id']}"],
        )
        for row in overdue_rows
    ]
    deadlines, truncated = await source_svc.upcoming_deadlines(
        session, now=moment, days=UPCOMING_DEADLINE_DAYS, limit=MAX_H5_DEADLINES
    )
    collector.manifest.deadlines_considered = len(deadlines)
    if truncated:
        collector.warn("DEADLINE_SCAN_TRUNCATED")
    collector.step("deadlines_loaded", considered=len(deadlines), accepted=len(deadlines))

    promotions: list = []
    daily_notes: list[dict[str, Any]] = []
    if include_knowledge:
        promotions, _loops, _health, _resurface, daily_notes = await _promotion_bundle(
            session,
            collector,
            period_start=period.start,
            period_end=period.end,
            start_day=period.start_day,
            end_day=period.end_day,
            focus_entity_id=None,
            project_ids=project_ids,
            include_daily_notes=True,
            include_knowledge=True,
            now=moment,
        )
    else:
        collector.step("h4_candidates_extracted", considered=0, accepted=0)

    stats = preview.get("stats") or {}
    bundle = DailyCloseBundle(
        day=day.isoformat(),
        review_preview=preview,
        completed_outcomes=completed_outcomes,
        focus_summary={
            "focus": stats.get("focus") or {},
            "topics": (stats.get("topics") or [])[:5],
            "study": stats.get("study") or {},
        },
        open_todos=[loop for loop in loops if loop.kind == "todo"],
        newly_overdue=newly_overdue,
        upcoming=deadlines,
        open_loops=loops,
        promotion_candidates=promotions,
        carry_forward_candidates=[loop for loop in loops if loop.kind == "todo"][:MAX_H5_OPEN_LOOPS],
        daily_note=daily_notes[0] if daily_notes else None,
    )
    return bundle, Coverage(
        period_start=period.start.isoformat(),
        period_end=period.end.isoformat(),
        days=1,
        partial=period.partial,
        comparable=period.comparable,
        reference_date=day.isoformat(),
    )


async def build_weekly_review(
    session: AsyncSession,
    collector: Collector,
    *,
    reference_date: Any,
    include_knowledge: bool,
    now: datetime | None = None,
) -> tuple[WeeklyReviewBundle, Coverage]:
    """Haftalık delta gözden geçirmesi (§41/§42)."""
    moment = now or datetime.now(UTC)
    period = source_svc.resolve_period(
        mode="weekly_review", since=None, until=None, reference_date=reference_date, now=moment
    )
    week_start = period.start_day
    collector.step("period_resolved", considered=1, accepted=1)

    current = await _preview(session, "weekly", week_start)
    collector.manifest.reviews_considered += 1
    collector.add_source(
        SourceRef(
            ref=f"aggregate:review_preview:weekly:{week_start.isoformat()}",
            domain="aggregate",
            kind="review_preview",
            title=f"hafta özeti {week_start.isoformat()}",
            timestamp=period.start.isoformat(),
        )
    )
    collector.step("review_preview_loaded", considered=1, accepted=1)

    previous = await source_svc.previous_review(session, kind="weekly", before=week_start)
    if previous is None:
        collector.warn("NO_PREVIOUS_REVIEW")
    else:
        collector.manifest.reviews_considered += 1
        collector.add_source(
            SourceRef(
                ref=f"review:{previous['id']}",
                domain="review",
                kind="review",
                title=f"önceki hafta {previous['period_start']}",
                timestamp=previous["period_start"],
                entity_id=previous["id"],
            )
        )
    collector.step("previous_review_loaded", considered=1, accepted=1 if previous else 0)

    declared: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    if previous is not None:
        decisions = previous.get("decisions") or {}
        raw_priorities = decisions.get("priorities") or []
        receipts = (decisions.get("_receipts") or {}).get("priorities") or []
        receipt_by_title = {
            policy_svc.normalize_for_identity(str(item.get("title") or "")): item
            for item in receipts
            if isinstance(item, dict)
        }
        todo_ids: list[uuid.UUID] = []
        for item in raw_priorities[:MAX_H5_PRIORITIES]:
            title = item if isinstance(item, str) else str(item.get("title") or "")
            if not title:
                continue
            receipt = receipt_by_title.get(policy_svc.normalize_for_identity(title))
            declared.append({"title": title, "has_receipt": bool(receipt)})
            if receipt and receipt.get("todo_id"):
                with contextlib.suppress(ValueError, AttributeError):
                    todo_ids.append(uuid.UUID(str(receipt["todo_id"])))
        if declared and not receipts:
            collector.warn(
                "PRIORITY_RECEIPTS_UNAVAILABLE",
                "önceki review makbuz içermiyor; tamamlanma durumu İDDİA EDİLMEZ",
            )
        statuses = await source_svc.todo_statuses(session, todo_ids=todo_ids)
        for entry in declared:
            receipt = receipt_by_title.get(policy_svc.normalize_for_identity(entry["title"]))
            if not receipt or not receipt.get("todo_id"):
                # §45/§151: başlık eşleştirmesi KANONİK KİMLİK SAYILMAZ.
                outcomes.append(
                    {
                        "title": entry["title"],
                        "outcome": "unknown",
                        "reason": "PRIORITY_RECEIPTS_UNAVAILABLE",
                    }
                )
                continue
            status = statuses.get(str(receipt["todo_id"]))
            if status is None:
                # §H5.1: makbuz KİMLİKTİR, güncel varlık değildir. Görev
                # silinmişse mevcut durum YOKTUR; bu "açık" demek DEĞİLDİR.
                outcome, status_name = "unknown", "missing"
            elif status["status"] == "done":
                outcome, status_name = "completed", status["status"]
            else:
                outcome, status_name = "open", status["status"]
            outcomes.append(
                {
                    "title": entry["title"],
                    "todo_id": str(receipt["todo_id"]),
                    "scheduled_day": receipt.get("scheduled_day"),
                    "outcome": outcome,
                    "status": status_name,
                }
            )

    comparison: dict[str, Any] = {}
    if previous is not None:
        previous_stats = previous.get("stats") or {}
        current_stats = current.get("stats") or {}
        if period.partial:
            comparison = {
                "comparable": False,
                "reason": "PARTIAL_PERIOD",
                "previous_completed": (previous_stats.get("todos") or {}).get("completed"),
                "current_completed": (current_stats.get("todos") or {}).get("completed"),
            }
        else:
            comparison = {
                "comparable": True,
                "completed_delta": int((current_stats.get("todos") or {}).get("completed", 0))
                - int((previous_stats.get("todos") or {}).get("completed", 0)),
                "focus_minutes_delta": int((current_stats.get("focus") or {}).get("minutes", 0))
                - int((previous_stats.get("focus") or {}).get("minutes", 0)),
            }
    if period.partial:
        collector.warn("PARTIAL_PERIOD", "dönem tamamlanmadı; sayısal karşılaştırma yapılmadı")

    completed_rows = await _completed_rows(session, "weekly", week_start)
    body_of_work = [
        _insight(
            insight_type="win",
            text=f"Tamamlandı: {row['title']}",
            support_refs=_completion_refs(collector, row),
            temporal_start=row.get("completed_at"),
        )
        for row in completed_rows[:MAX_H5_BODY_OF_WORK]
    ]

    events, events_truncated = await source_svc.meaningful_events(
        session, start=period.start, end=period.end, limit=MAX_H5_BODY_OF_WORK
    )
    collector.manifest.events_considered += len(events)
    if events_truncated:
        collector.warn("EVENT_SCAN_TRUNCATED")
    collector.step("events_loaded", considered=len(events), accepted=len(events))

    changes: list[ReviewInsight] = []
    opportunities = await source_svc.opportunity_changes(
        session, start=period.start, end=period.end, limit=MAX_H5_INSIGHTS
    )
    for opportunity in opportunities:
        changes.append(
            _insight(
                insight_type="change",
                text=f"Yeni kayıt: {opportunity['title']}",
                support_refs=[f"entity:{opportunity['id']}"],
                temporal_start=opportunity.get("found_at"),
            )
        )
        collector.add_source(
            SourceRef(
                ref=f"entity:{opportunity['id']}",
                domain="operational",
                kind="opportunity",
                title=opportunity["title"],
                timestamp=opportunity.get("found_at"),
                entity_id=opportunity["id"],
            )
        )

    loops, stalled, projects, project_ids = await _open_loops_and_projects(
        session, collector, now=moment
    )
    deadlines, deadlines_truncated = await source_svc.upcoming_deadlines(
        session, now=moment, days=UPCOMING_DEADLINE_DAYS, limit=MAX_H5_DEADLINES
    )
    collector.manifest.deadlines_considered = len(deadlines)
    if deadlines_truncated:
        collector.warn("DEADLINE_SCAN_TRUNCATED")

    time_sensitive: list[ReviewInsight] = []
    for deadline in deadlines:
        remaining = int(deadline.get("remaining_days") or 0)
        if remaining > 3:
            continue
        entity_id = deadline.get("entity_id")
        if not entity_id:
            # Kanonik referansı olmayan son tarih için OLGU ÜRETİLMEZ (§H5.1);
            # uydurma/pseudo kaynak yazmak yerine sessizce değil, iz adımında
            # "kabul edilmedi" olarak görünür.
            continue
        time_sensitive.append(
            _insight(
                insight_type="time_sensitive",
                text=f"{deadline['title']} için son tarih {remaining} gün içinde.",
                support_refs=[f"entity:{entity_id}"],
                temporal_end=deadline.get("due_at"),
            )
        )
    collector.step(
        "deadlines_loaded", considered=len(deadlines), accepted=len(time_sensitive)
    )

    promotions: list = []
    health: list = []
    resurface: list = []
    if include_knowledge:
        promotions, _loops, health, resurface, _notes = await _promotion_bundle(
            session,
            collector,
            period_start=period.start,
            period_end=period.end,
            start_day=period.start_day,
            end_day=period.end_day,
            focus_entity_id=None,
            project_ids=project_ids,
            include_daily_notes=True,
            include_knowledge=True,
            now=moment,
        )
    else:
        collector.step("h4_candidates_extracted", considered=0, accepted=0)

    stats = current.get("stats") or {}
    bundle = WeeklyReviewBundle(
        current_snapshot=current,
        previous_review=previous,
        comparison=comparison,
        declared_priorities=declared,
        priority_outcomes=outcomes,
        body_of_work=body_of_work,
        focus_distribution={
            "focus": stats.get("focus") or {},
            "topics": (stats.get("topics") or [])[:MAX_H5_INSIGHTS],
        },
        changes=changes[:MAX_H5_INSIGHTS],
        wins=body_of_work[:MAX_H5_INSIGHTS],
        open_loops=loops,
        stalled_projects=stalled,
        upcoming=deadlines,
        time_sensitive_changes=time_sensitive[:MAX_H5_INSIGHTS],
        promotion_candidates=promotions,
        knowledge_health=health,
        resurface_candidates=resurface,
        carry_forward_candidates=[loop for loop in loops if loop.kind == "todo"][:MAX_H5_OPEN_LOOPS],
    )
    return bundle, Coverage(
        period_start=period.start.isoformat(),
        period_end=period.end.isoformat(),
        days=7,
        partial=period.partial,
        comparable=period.comparable and previous is not None,
        reference_date=(period.reference_date or week_start).isoformat(),
    )


async def build_period_delta(
    session: AsyncSession,
    collector: Collector,
    *,
    since: datetime,
    until: datetime | None,
    focus_entity_id: uuid.UUID | None,
    now: datetime | None = None,
) -> tuple[PeriodDeltaBundle, Coverage]:
    """İki an arasında ne değişti (§50)."""
    moment = now or datetime.now(UTC)
    period = source_svc.resolve_period(
        mode="period_delta", since=since, until=until, reference_date=None, now=moment
    )
    collector.step("period_resolved", considered=1, accepted=1)

    focus_entity = None
    if focus_entity_id is not None:
        focus_entity = await source_svc.load_entity(session, focus_entity_id)
        if focus_entity is None:
            from app.integrations.review_intelligence.models import ReviewIntelligenceError

            raise ReviewIntelligenceError("INVALID_FOCUS_ENTITY", "focus entity not found")
        collector.manifest.entities_considered += 1

    if focus_entity_id is not None:
        events, truncated = await source_svc.scoped_events(
            session, entity_ids=[focus_entity_id], start=period.start, end=period.end, limit=MAX_H5_BODY_OF_WORK * 3
        )
    else:
        events, truncated = await source_svc.meaningful_events(
            session, start=period.start, end=period.end, limit=MAX_H5_BODY_OF_WORK * 3
        )
    collector.manifest.events_considered = len(events)
    if truncated:
        collector.warn("EVENT_SCAN_TRUNCATED")
        collector.truncated = True
    collector.step("events_loaded", considered=len(events), accepted=len(events))

    def _events_with(verbs: set[str]) -> list[ReviewInsight]:
        results: list[ReviewInsight] = []
        for event in events:
            if event["verb"] not in verbs:
                continue
            ref = collector.add_source(
                SourceRef(
                    ref=f"event:{event['id']}",
                    domain="operational",
                    kind="event",
                    title=event.get("title") or event["verb"],
                    timestamp=event["occurred_at"].isoformat(),
                    entity_id=event.get("entity_id"),
                )
            )
            results.append(
                _insight(
                    insight_type="change",
                    text=f"{event['verb']}: {event.get('title') or ''}".strip(),
                    support_refs=[ref],
                    temporal_start=event["occurred_at"].isoformat(),
                )
            )
            if len(results) >= MAX_H5_INSIGHTS:
                break
        return results

    completed = _events_with({"todo.completed", "study.topic_completed", "review.completed"})
    created = _events_with({"todo.created"})
    closed = _events_with({"todo.dropped"})
    status_changes = _events_with(
        {verb for verb in {event["verb"] for event in events} if verb.endswith((".updated", ".transitioned"))}
    )

    # Action delta stays on Event; current effort uses recorded sessions.
    focus_query = select(PomodoroSession.topic, func.coalesce(func.sum(PomodoroSession.actual_min), 0)).where(
        PomodoroSession.kind == "focus", PomodoroSession.ended_at.is_not(None),
        PomodoroSession.started_at >= period.start, PomodoroSession.started_at < period.end)
    if focus_entity_id is not None:
        linked = select(Link.from_id).where(Link.to_id == focus_entity_id)
        focus_query = focus_query.where(or_(PomodoroSession.context_entity_id == focus_entity_id,
                                            PomodoroSession.context_entity_id.in_(linked)))
    focus_rows = (await session.execute(focus_query.group_by(PomodoroSession.topic))).all()
    focus_minutes = sum(int(minutes) for _, minutes in focus_rows)
    topics: dict[str, int] = {}
    for topic, minutes in focus_rows:
        label = topic or "Genel"
        topics[label] = topics.get(label, 0) + int(minutes)

    applications: list[ReviewInsight] = []
    if focus_entity_id is None:
        rows = (
            await session.execute(
                select(ApplicationHistory.opportunity_id, ApplicationHistory.to_status, ApplicationHistory.at)
                .where(ApplicationHistory.at >= period.start, ApplicationHistory.at < period.end)
                .order_by(ApplicationHistory.at.desc())
                .limit(MAX_H5_INSIGHTS)
            )
        ).all()
        for opportunity_id, to_status, at in rows:
            ref = collector.add_source(
                SourceRef(
                    ref=f"entity:{opportunity_id}",
                    domain="operational",
                    kind="application",
                    title=to_status,
                    timestamp=at.isoformat(),
                    entity_id=str(opportunity_id),
                )
            )
            applications.append(
                _insight(
                    insight_type="change",
                    text=f"Başvuru durumu: {to_status}",
                    support_refs=[ref],
                    temporal_start=at.isoformat(),
                )
            )

    announcements = await source_svc.opportunity_changes(
        session, start=period.start, end=period.end, limit=MAX_H5_INSIGHTS
    )
    new_announcements = [
        _insight(
            insight_type="change",
            text=f"Yeni kayıt: {item['title']}",
            support_refs=[f"entity:{item['id']}"],
            temporal_start=item.get("found_at"),
        )
        for item in announcements
    ]
    deadline_changes = [
        _insight(
            insight_type="time_sensitive",
            text=f"{item['title']} son tarihi bu pencerede: {item['deadline_at']}",
            support_refs=[f"entity:{item['id']}"],
            temporal_end=item.get("deadline_at"),
        )
        for item in announcements
        if item.get("deadline_at")
    ]

    loops, stalled, _projects, _ids = await _open_loops_and_projects(session, collector, now=moment)
    project_changes = _events_with(
        {verb for verb in {event["verb"] for event in events} if verb.startswith("project.")}
    )

    bundle = PeriodDeltaBundle(
        completed=completed,
        created=created,
        closed=closed,
        opened=new_announcements,
        status_changes=status_changes,
        focus={
            "minutes": focus_minutes,
            "topics": sorted(
                ({"topic": topic, "minutes": minutes} for topic, minutes in topics.items()),
                key=lambda item: (-item["minutes"], item["topic"]),
            )[:MAX_H5_INSIGHTS],
        },
        deadline_changes=deadline_changes,
        new_announcements=new_announcements,
        applications=applications,
        project_changes=project_changes,
        open_loops=loops,
        focus_entity=focus_entity,
    )
    return bundle, Coverage(
        period_start=period.start.isoformat(),
        period_end=period.end.isoformat(),
        days=period.days,
        partial=period.partial,
        comparable=period.comparable,
    )


async def build_consolidation(
    session: AsyncSession,
    collector: Collector,
    *,
    since: datetime | None,
    until: datetime | None,
    focus_entity_id: uuid.UUID | None,
    include_knowledge: bool,
    now: datetime | None = None,
) -> tuple[ConsolidationBundle, Coverage]:
    """Konsolidasyon: hangi geçici malzeme kalıcı olmayı hak ediyor (§51)."""
    moment = now or datetime.now(UTC)
    period = source_svc.resolve_period(
        mode="consolidation_review", since=since, until=until, reference_date=None, now=moment
    )
    collector.step("period_resolved", considered=1, accepted=1)

    focus_entity = None
    if focus_entity_id is not None:
        focus_entity = await source_svc.load_entity(session, focus_entity_id)
        if focus_entity is None:
            from app.integrations.review_intelligence.models import ReviewIntelligenceError

            raise ReviewIntelligenceError("INVALID_FOCUS_ENTITY", "focus entity not found")
        collector.manifest.entities_considered += 1

    _loops, _stalled, _projects, project_ids = await _open_loops_and_projects(
        session, collector, now=moment
    )
    promotions, possible_loops, health, resurface, daily_notes = await _promotion_bundle(
        session,
        collector,
        period_start=period.start,
        period_end=period.end,
        start_day=period.start_day,
        end_day=period.end_day,
        focus_entity_id=focus_entity_id,
        project_ids=project_ids,
        include_daily_notes=True,
        include_knowledge=include_knowledge,
        now=moment,
    )

    bundle = ConsolidationBundle(
        promotion_candidates=promotions,
        possible_open_loops=possible_loops,
        knowledge_health=health,
        resurface_candidates=resurface,
        daily_notes=daily_notes,
        source_fragments=len(daily_notes) + len(promotions),
    )
    return bundle, Coverage(
        period_start=period.start.isoformat(),
        period_end=period.end.isoformat(),
        days=period.days,
        partial=period.partial,
        comparable=period.comparable,
    )


__all__ = [
    "build_consolidation",
    "build_daily_close",
    "build_period_delta",
    "build_weekly_review",
]
