"""Cekirdek endpoint'ler: search, activity, tag, saved view, link, kaynak sagligi."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import contributions as contribution_svc
from app.core import events as event_svc
from app.core import graph as graph_svc
from app.core import links as link_svc
from app.core import registry as registry_svc
from app.core import runs as run_svc
from app.core import search as search_svc
from app.core import tags as tag_svc
from app.core.events import log_event
from app.core.models import Entity, Notification
from app.core.schemas import (
    EntityOut,
    EventOut,
    LinkIn,
    NotificationOut,
    RelatedOut,
    SourceRunOut,
    TagOut,
)
from app.db import get_session

router = APIRouter(tags=["core"])


@router.get("/registry/entity-types")
async def registry_entity_types():
    """Tip -> etiket/rota/ikon kayit defteri (AGENTS.md kural 13). Frontend
    bu uctan beslenir; tip->rota sabiti YAZMAZ."""
    return [
        {
            "type": spec.type,
            "label": spec.label,
            "label_plural": spec.label_plural,
            "route": spec.route,
            "icon": spec.icon,
            "searchable": spec.searchable,
            "linkable": spec.linkable,
        }
        for spec in registry_svc.all_entity_types()
    ]


@router.get("/registry/event-verbs")
async def registry_event_verbs():
    """Event verb -> etiket kayit defteri."""
    return {"verbs": sorted(registry_svc.all_event_verbs())}


@router.get("/deadlines")
async def deadlines(
    limit: int = Query(200, le=500),
    session: AsyncSession = Depends(get_session),
):
    """Son tarihli kayitlar -- kayitli modul saglayicilarindan (kural 16)."""
    from app.core.deadlines import collect_deadlines

    return await collect_deadlines(session, limit=limit)


@router.get("/notifications", response_model=list[NotificationOut])
async def notifications(session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(Notification, Entity.type)
            .outerjoin(Entity, Entity.id == Notification.entity_id)
            .where(Notification.dismissed_at.is_(None))
            .order_by(Notification.created_at.desc())
            .limit(100)
        )
    ).all()
    return [
        NotificationOut(
            id=item.id,
            kind=item.kind,
            title=item.title,
            body=item.body,
            entity_id=item.entity_id,
            entity_type=entity_type,
            importance=item.importance,
            created_at=item.created_at,
            read_at=item.read_at,
        )
        for item, entity_type in rows
    ]


@router.post("/notifications/{notification_id}/read")
async def read_notification(notification_id: int, session: AsyncSession = Depends(get_session)):
    item = await session.get(Notification, notification_id)
    if item is None:
        raise HTTPException(404)
    item.read_at = datetime.now(UTC)
    await session.commit()
    return {"ok": True}


@router.post("/notifications/read-all")
async def read_all_notifications(session: AsyncSession = Depends(get_session)):
    now = datetime.now(UTC)
    result = await session.execute(
        update(Notification)
        .where(Notification.read_at.is_(None), Notification.dismissed_at.is_(None))
        .values(read_at=now)
    )
    await session.commit()
    return {"read": result.rowcount or 0}


@router.post("/notifications/{notification_id}/dismiss")
async def dismiss_notification(notification_id: int, session: AsyncSession = Depends(get_session)):
    item = await session.get(Notification, notification_id)
    if item is None:
        raise HTTPException(404)
    now = datetime.now(UTC)
    item.dismissed_at = now
    if item.read_at is None:
        item.read_at = now
    await session.commit()
    return {"ok": True}


@router.post("/notifications/dismiss-all")
async def dismiss_all_notifications(session: AsyncSession = Depends(get_session)):
    now = datetime.now(UTC)
    result = await session.execute(
        update(Notification)
        .where(Notification.dismissed_at.is_(None))
        .values(dismissed_at=now, read_at=func.coalesce(Notification.read_at, now))
    )
    await session.commit()
    return {"dismissed": result.rowcount or 0}


@router.get("/search")
async def search(
    q: str = Query(min_length=1),
    types: list[str] | None = Query(None),
    limit: int = 30,
    grouped: bool = False,
    session: AsyncSession = Depends(get_session),
):
    if grouped:
        return await search_svc.grouped_search(session, q, limit=limit)
    return await search_svc.search_entities(session, q, types=types, limit=limit)


@router.get("/activity", response_model=list[EventOut])
async def activity(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    since: datetime | None = None,
    verbs: list[str] | None = Query(None),
    category: str | None = Query(None),
    q: str | None = Query(None, max_length=200),
    session: AsyncSession = Depends(get_session),
):
    """Hareket akisi.

    `category` emek haritasi kategorilerinden biri (read/task/focus/routine/
    study/media) ya da "system" (haritada sayilmayan worker kayitlari).
    `q` baslik/aciklama/verb icinde arar; `offset` ile "daha fazla yukle"
    yapilir. Ayni kayit iki kez gelmesin diye sira (occurred_at, id) sabittir.
    """
    return await event_svc.recent_events(
        session,
        limit=limit,
        offset=offset,
        since=since,
        verbs=verbs,
        category=category,
        q=q,
    )


@router.get("/activity/heatmap")
async def activity_heatmap(
    days: int = Query(365, ge=7, le=730),
    session: AsyncSession = Depends(get_session),
):
    """Gunluk emek haritasi -- sadece insan eliyle yapilan isler sayilir."""
    return await contribution_svc.heatmap(session, days=days)


@router.get("/activity/day")
async def activity_day(
    day: date = Query(..., description="YYYY-MM-DD"),
    session: AsyncSession = Depends(get_session),
):
    """Tek gunun dokumu -- emek haritasi karesinin hedefi."""
    return await contribution_svc.day_detail(session, day)


@router.get("/entities/{entity_id}", response_model=EntityOut)
async def entity_detail(entity_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    entity = await session.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
    return entity


@router.get("/entities/{entity_id}/related", response_model=list[RelatedOut])
async def related(entity_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Bagli kayitlar: iliski + yon (outgoing/incoming) + karsi entity ozeti."""
    return await link_svc.related(session, entity_id)


@router.post("/links", status_code=201)
async def create_link(body: LinkIn, session: AsyncSession = Depends(get_session)):
    await link_svc.link(session, body.from_id, body.to_id, body.relation)
    await log_event(
        session,
        verb="link.created",
        entity_id=body.from_id,
        payload={"to_id": str(body.to_id), "relation": body.relation},
    )
    await session.commit()
    return {"ok": True}


@router.delete("/links", status_code=204)
async def delete_link(body: LinkIn, session: AsyncSession = Depends(get_session)):
    await link_svc.unlink(session, body.from_id, body.to_id, body.relation)
    await session.commit()


@router.get("/graph")
async def knowledge_graph(
    focus: uuid.UUID | None = None,
    depth: int = Query(2, ge=1, le=4),
    limit: int = Query(graph_svc.MAX_NODES, ge=1, le=graph_svc.MAX_NODES),
    session: AsyncSession = Depends(get_session),
):
    """Bilgi grafi: dugum = entity, kenar = link. focus verilirse o kaydin cevresi."""
    return await graph_svc.build(session, focus=focus, depth=depth, limit=limit)


@router.get("/entities/{entity_id}/backlinks")
async def entity_backlinks(entity_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Bu kayda [[...]] ile baglanan kayitlar."""
    return await graph_svc.backlinks(session, entity_id)


@router.get("/tags", response_model=list[TagOut])
async def list_tags(session: AsyncSession = Depends(get_session)):
    return [TagOut(name=name, count=count) for name, count in await tag_svc.list_tags(session)]


@router.get("/sources/health", response_model=list[SourceRunOut])
async def source_health(
    limit: int = Query(500, le=2000),
    session: AsyncSession = Depends(get_session),
):
    """Her kaynagin son kosumu. 'empty' veya 'error' goruyorsan bir sey kirilmis."""
    return await run_svc.health(session, limit=limit)

