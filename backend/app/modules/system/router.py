from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.system import backup, export
from app.modules.system.models import Setting

router = APIRouter(tags=["system"])

DEFAULTS: dict[str, Any] = {
    "modules.disabled": [],
    "today.widget_order": [],
    "pomodoro.defaults": {"focus": 25, "short": 5, "long": 15},
    "notifications.thresholds": {},
    "sources.intervals": {},
    "rss.retention_days": 90,
    "media.links": [],
    "theme": "dark",
}


class SettingIn(BaseModel):
    value: Any


@router.get("/settings")
async def settings(session: AsyncSession = Depends(get_session)):
    result = dict(DEFAULTS)
    rows = list((await session.execute(select(Setting))).scalars())
    result.update({item.key: item.value for item in rows})
    return result


@router.put("/settings/{key:path}")
async def put_setting(key: str, body: SettingIn, session: AsyncSession = Depends(get_session)):
    item = await session.get(Setting, key)
    if item is None:
        item = Setting(key=key, value=body.value)
        session.add(item)
    else:
        item.value = body.value
    await session.commit()
    return {"key": key, "value": body.value}


@router.get("/export/json")
async def export_json(session: AsyncSession = Depends(get_session)):
    payload = await export.full_json(session)
    return Response(
        json.dumps(payload, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=forkos-export.json"},
    )


@router.get("/export/csv")
async def export_csv(module: str, session: AsyncSession = Depends(get_session)):
    try:
        body = await export.csv_export(session, module)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return PlainTextResponse(
        body,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={module}.csv"},
    )


@router.get("/export/markdown")
async def export_markdown(session: AsyncSession = Depends(get_session)):
    return PlainTextResponse(await export.markdown_export(session), media_type="text/markdown")


@router.get("/export/bookmarks")
async def export_bookmarks(session: AsyncSession = Depends(get_session)):
    return Response(await export.bookmarks_html(session), media_type="text/html")


@router.get("/export/opml")
async def export_opml(session: AsyncSession = Depends(get_session)):
    return Response(await export.opml(session), media_type="text/xml")


@router.get("/export/ics")
async def export_ics(session: AsyncSession = Depends(get_session)):
    return Response(await export.ics(session), media_type="text/calendar")


@router.post("/backup")
async def run_backup(session: AsyncSession = Depends(get_session)):
    path = await backup.create_backup(session)
    return {"path": str(path), "size": path.stat().st_size}
