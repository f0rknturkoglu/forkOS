"""Cekirdek endpoint'ler: search, activity, tag, saved view, link, kaynak sagligi."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events as event_svc
from app.core import links as link_svc
from app.core import runs as run_svc
from app.core import search as search_svc
from app.core import tags as tag_svc
from app.core.models import SavedView
from app.core.schemas import (
    EntityOut,
    EventOut,
    LinkIn,
    SavedViewIn,
    SavedViewOut,
    SourceRunOut,
    TagOut,
)
from app.db import get_session

router = APIRouter(tags=["core"])


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
    limit: int = Query(50, le=500),
    since: datetime | None = None,
    verbs: list[str] | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    return await event_svc.recent_events(session, limit=limit, since=since, verbs=verbs)


@router.get("/entities/{entity_id}/related", response_model=list[EntityOut])
async def related(entity_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await link_svc.related(session, entity_id)


@router.post("/links", status_code=201)
async def create_link(body: LinkIn, session: AsyncSession = Depends(get_session)):
    await link_svc.link(session, body.from_id, body.to_id, body.relation)
    await session.commit()
    return {"ok": True}


@router.delete("/links", status_code=204)
async def delete_link(body: LinkIn, session: AsyncSession = Depends(get_session)):
    await link_svc.unlink(session, body.from_id, body.to_id, body.relation)
    await session.commit()


@router.get("/tags", response_model=list[TagOut])
async def list_tags(session: AsyncSession = Depends(get_session)):
    return [TagOut(name=name, count=count) for name, count in await tag_svc.list_tags(session)]


@router.get("/sources/health", response_model=list[SourceRunOut])
async def source_health(session: AsyncSession = Depends(get_session)):
    """Her kaynagin son kosumu. 'empty' veya 'error' goruyorsan bir sey kirilmis."""
    return await run_svc.health(session)


@router.get("/views", response_model=list[SavedViewOut])
async def list_views(
    module: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(SavedView).order_by(SavedView.position, SavedView.name)
    if module:
        stmt = stmt.where(SavedView.module == module)
    return list((await session.execute(stmt)).scalars())


@router.post("/views", response_model=SavedViewOut, status_code=201)
async def create_view(body: SavedViewIn, session: AsyncSession = Depends(get_session)):
    view = SavedView(**body.model_dump())
    session.add(view)
    await session.commit()
    return view


@router.delete("/views/{view_id}", status_code=204)
async def delete_view(view_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    view = await session.get(SavedView, view_id)
    if view is not None:
        await session.delete(view)
        await session.commit()
