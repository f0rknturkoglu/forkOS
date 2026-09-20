"""H5 testleri için ortak kurulum yardımcıları.

`test_*.py` DEĞİLDİR (pytest toplamaz). Gerçek zaman yerine SABİT bir `now`
kullanılır; böylece süreklilik/delta testleri deterministiktir.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, Event, Link
from app.modules.project.models import Milestone, Project
from app.modules.rss.models import Feed, FeedItem
from app.modules.todo.models import PlanSlot, Todo

#: Sabitlenmiş zaman (kullanıcı senaryosu §39).
NOW = datetime(2026, 9, 20, 18, 0, tzinfo=UTC)
ANCHOR = datetime(2026, 9, 18, 17, 0, tzinfo=UTC)


async def make_project(
    session: AsyncSession,
    *,
    title: str = "forkjob",
    next_action: str = "Mimariyi yaz",
    status: str = "active",
) -> Entity:
    entity = Entity(type="project", title=title, search_text="")
    session.add(entity)
    await session.flush()
    session.add(Project(id=entity.id, status=status, next_action=next_action, stack=["Rust"]))
    await session.flush()
    return entity


async def make_todo(
    session: AsyncSession,
    *,
    title: str,
    status: str = "open",
    priority: int = 2,
    due_at: datetime | None = None,
    project: Entity | None = None,
) -> Entity:
    entity = Entity(type="todo", title=title, search_text="")
    session.add(entity)
    await session.flush()
    session.add(Todo(id=entity.id, status=status, priority=priority, due_at=due_at))
    if project is not None:
        session.add(Link(from_id=entity.id, to_id=project.id, relation="belongs_to"))
    await session.flush()
    return entity


async def make_event(
    session: AsyncSession,
    *,
    verb: str,
    occurred_at: datetime,
    entity: Entity | None = None,
    payload: dict[str, Any] | None = None,
) -> Event:
    event = Event(
        entity_id=entity.id if entity else None,
        entity_type=entity.type if entity else None,
        verb=verb,
        payload=payload or {},
        occurred_at=occurred_at,
    )
    session.add(event)
    await session.flush()
    return event


async def make_plan_slot(
    session: AsyncSession, *, todo: Entity, day, start_min: int | None = 600
) -> PlanSlot:
    slot = PlanSlot(entity_id=todo.id, day=day, start_min=start_min, duration_min=60)
    session.add(slot)
    await session.flush()
    return slot


async def make_feed_items(
    session: AsyncSession, *, count: int, fetched_at: datetime, read: bool = False, title: str = "Kurgusal Kaynak"
) -> None:
    feed_entity = Entity(type="feed", title=title, search_text="")
    session.add(feed_entity)
    await session.flush()
    session.add(Feed(id=feed_entity.id, url=f"https://example.invalid/{uuid.uuid4().hex}", category="tech"))
    await session.flush()
    for index in range(count):
        item_entity = Entity(type="feed_item", title=f"İçerik {index}", search_text="")
        session.add(item_entity)
        await session.flush()
        session.add(
            FeedItem(
                id=item_entity.id,
                feed_id=feed_entity.id,
                guid=f"guid-{uuid.uuid4().hex}",
                fetched_at=fetched_at,
                read_at=fetched_at if read else None,
            )
        )
    await session.flush()


async def make_milestone(
    session: AsyncSession, *, project: Entity, title: str = "Alpha", due_at: datetime | None = None
) -> Milestone:
    entity = Entity(type="milestone", title=title, search_text="")
    session.add(entity)
    await session.flush()
    milestone = Milestone(id=entity.id, project_id=project.id, title=title, due_at=due_at)
    session.add(milestone)
    await session.flush()
    return milestone


def write_daily_note(vault: Path, day: str, body: str) -> None:
    directory = vault / "10 Daily"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{day}.md").write_text(body, encoding="utf-8")


def write_managed_note(
    vault: Path,
    relative_path: str,
    *,
    forkos_id: str,
    forkos_type: str = "project",
    body: str,
) -> Path:
    target = vault / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f"---\nforkos_id: {forkos_id}\nforkos_type: {forkos_type}\n---\n{body}",
        encoding="utf-8",
    )
    return target


async def build_continuity_fixture(session: AsyncSession, vault: Path) -> dict[str, Any]:
    """§39 senaryosu: 2 günlük boşluk, RSS birikimi, yaklaşan son tarih, gecikme, geçen plan."""
    project = await make_project(session, title="forkjob", next_action="")
    study = await make_todo(session, title="ALES denemesi", priority=3)
    overdue = await make_todo(
        session, title="Gecikmis gorev", priority=2, due_at=ANCHOR + timedelta(hours=3), project=project
    )
    await make_plan_slot(session, todo=overdue, day=(NOW - timedelta(days=1)).date(), start_min=600)

    await make_event(
        session,
        verb="pomodoro.completed",
        occurred_at=ANCHOR,
        entity=study,
        payload={"minutes": 85, "topic": "ALES"},
    )
    await make_event(
        session,
        verb="todo.created",
        occurred_at=ANCHOR - timedelta(hours=2),
        entity=overdue,
        payload={"title": "Gecikmis gorev"},
    )
    await make_feed_items(session, count=37, fetched_at=ANCHOR + timedelta(hours=1))

    write_managed_note(
        vault, "20 Projects/forkjob.md", forkos_id=str(project.id), body="# forkjob\n\n## Karar\n\nReact ağırlıklı panel.\n"
    )
    write_daily_note(vault, "2026-09-18", "# 18 Eylül\n\nforkjob UI için minimum kaynak yaklaşımı benimsendi.\n")
    write_daily_note(
        vault,
        "2026-09-19",
        "# 19 Eylül\n\nforkjob UI için minimum kaynak yaklaşımı benimsendi.\nYarın H4 modellerini karşılaştır.\n",
    )
    await session.commit()
    return {"project": project, "study": study, "overdue": overdue}
