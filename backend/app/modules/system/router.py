from __future__ import annotations

import json
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.system import backup, export, news, restore, stats
from app.modules.system.models import Setting

router = APIRouter(tags=["system"])

DEFAULTS: dict[str, Any] = {
    "modules.disabled": [],
    "today.widget_order": [],
    "today.auto_suggestions": True,
    "pomodoro.defaults": {"focus": 50, "short": 10, "long": 20},
    "notifications.thresholds": {},
    "sources.intervals": {},
    "rss.retention_days": 90,
    "media.links": [],
    "media.sync_interval_hours": 24,
    "media.upcoming_days": 30,
    "media.tmdb_key": "",
    "media.google_books_key": "",
    "media.igdb_client_id": "",
    "media.igdb_client_secret": "",
    "news.subreddits": news.DEFAULT_SUBREDDITS,
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


@router.get("/system/stats")
async def system_stats(session: AsyncSession = Depends(get_session)):
    """Panel icin sunucu sagligi: CPU, RAM, disk, uptime.

    Harici bagimliliksiz -- /proc okunur. forkOS'un uzerinde kostugu
    makineyi (Linux VM ya da host) yansitir, tek bir container'i degil.

    CPU yuzdesi /proc/stat farkindan hesaplanir. Onceden `loadavg[0]/cekirdek`
    gosteriliyordu; o bir kuyruk uzunlugu orani, kullanim yuzdesi degil --
    bos bir makinede bile yuksek, tam dolu bir makinede bile dusuk cikabilir.
    """
    import os

    load: list[float] = []
    with suppress(OSError), open("/proc/loadavg") as handle:
        load = [float(x) for x in handle.read().split()[:3]]

    mem: dict[str, int] = {}
    try:
        with open("/proc/meminfo") as handle:
            for line in handle:
                key, _, rest = line.partition(":")
                if key in ("MemTotal", "MemAvailable"):
                    mem[key] = int(rest.strip().split()[0])  # kB
    except OSError:
        pass

    disk: dict = {}
    disk_path = os.getenv("STATS_DISK_PATH", "/app")
    try:
        stat = os.statvfs(disk_path)
        disk = {"total": stat.f_blocks * stat.f_frsize,
                "free": stat.f_bavail * stat.f_frsize,
                "path": disk_path}
    except OSError:
        pass

    uptime_s = 0.0
    with suppress(OSError), open("/proc/uptime") as handle:
        uptime_s = float(handle.read().split()[0])

    heartbeat = await session.get(Setting, "worker.heartbeat")
    heartbeat_at = None
    if heartbeat and isinstance(heartbeat.value, dict):
        heartbeat_at = heartbeat.value.get("at")
    worker_status = "unknown"
    if isinstance(heartbeat_at, str):
        try:
            observed = datetime.fromisoformat(heartbeat_at)
            worker_status = (
                "healthy"
                if observed >= datetime.now(UTC) - timedelta(minutes=3)
                else "stale"
            )
        except ValueError:
            worker_status = "unknown"

    return {
        "cpu_pct": stats.cpu_percent(),
        "load": load,
        "cpu_count": os.cpu_count() or 1,
        "mem_total_kb": mem.get("MemTotal"),
        "mem_available_kb": mem.get("MemAvailable"),
        "disk": disk,
        "uptime_s": uptime_s,
        "worker": {"status": worker_status, "heartbeat_at": heartbeat_at},
    }


@router.get("/backup/status")
async def backup_status(session: AsyncSession = Depends(get_session)):
    """Son yedek, Drive yukleme durumu ve yedek kapsami -- tek bakisla."""
    return await backup.backup_status(session)


@router.post("/backup/restore")
async def restore_backup(
    file: UploadFile = File(...), session: AsyncSession = Depends(get_session),
):
    """JSON yedegini geri yukler.

    Idempotent + cakismasiz: var olan kayitlara dokunulmaz, eksikler eklenir.
    Ayni yedek defalarca yuklenebilir. (Opsiyonel: Yerel dosyayla cagirilir.)
    """
    content = await file.read()
    try:
        payload = restore.parse_backup(content)
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        raise HTTPException(422, f"yedek okunamadi: {exc}") from exc
    try:
        summary = await restore.restore(session, payload)
    except Exception as exc:
        raise HTTPException(500, f"geri yukleme hatasi: {type(exc).__name__}: {exc}") from exc
    restored = sum(entry.get("inserted", 0) for entry in summary.values())
    return {"restored": restored, "tables": summary}


@router.get("/news/reddit")
async def reddit_news(
    limit: int = Query(12, ge=1, le=40),
    session: AsyncSession = Depends(get_session),
):
    """Bugun panelindeki reddit akisi -- tech/CS subredditleri.

    Sunucudan cekilir: reddit tarayiciya 403 doner (bkz. news.py).
    Kaynak listesi "news.subreddits" ayarindan; yoksa varsayilanlar.
    """
    setting = await session.get(Setting, "news.subreddits")
    value = setting.value if setting and isinstance(setting.value, list) else None
    subs = [str(s) for s in (value or news.DEFAULT_SUBREDDITS)]
    try:
        return await news.reddit_posts(subs, limit)
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"reddit okunamadi: {exc}") from exc


@router.get("/news/hacker-news")
async def hacker_news(
    limit: int = Query(15, ge=1, le=40),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await news.hacker_news(session, limit)
    except (httpx.HTTPError, RuntimeError) as exc:
        raise HTTPException(502, f"Hacker News okunamadı: {exc}") from exc


@router.get("/news/github-trending")
async def github_trending(
    limit: int = Query(10, ge=1, le=40),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await news.github_trending(session, limit)
    except (httpx.HTTPError, RuntimeError) as exc:
        raise HTTPException(502, f"GitHub okunamadı: {exc}") from exc
