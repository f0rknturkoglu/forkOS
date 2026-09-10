from __future__ import annotations

import json
import uuid
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.core.models import SavedView
from app.core.schemas import SavedViewCreate, SavedViewOut, SavedViewPatch
from app.db import get_session
from app.modules.system import backup, export, news, refresh, restore, stats
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
    "opportunity.career_profile": {
        "current_location": "Ankara, Türkiye",
        "authorized_countries": ["Türkiye"],
        "willing_to_relocate": False,
    },
    "news.subreddits": news.DEFAULT_SUBREDDITS,
    "theme": "dark",
}


class SettingIn(BaseModel):
    value: Any


class ManualRefreshOut(BaseModel):
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    results: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


@router.get("/system/refresh", response_model=ManualRefreshOut)
async def manual_refresh_status(session: AsyncSession = Depends(get_session)):
    return await refresh.status(session)


@router.post("/system/refresh", response_model=ManualRefreshOut)
async def manual_refresh(
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    value, started = await refresh.queue(session)
    if started:
        background.add_task(refresh.run)
    return value


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
        disk = {
            "total": stat.f_blocks * stat.f_frsize,
            "free": stat.f_bavail * stat.f_frsize,
            "path": disk_path,
        }
    except OSError:
        pass

    uptime_s = 0.0
    with suppress(OSError), open("/proc/uptime") as handle:
        uptime_s = float(handle.read().split()[0])

    heartbeat = await session.get(Setting, "worker.heartbeat")
    heartbeat_at = None
    if heartbeat and isinstance(heartbeat.value, dict):
        heartbeat_at = heartbeat.value.get("at")
    worker_status = "unknown" if app_settings.worker_enabled else "disabled"
    if app_settings.worker_enabled and isinstance(heartbeat_at, str):
        try:
            observed = datetime.fromisoformat(heartbeat_at)
            fresh = observed >= datetime.now(UTC) - timedelta(minutes=3)
            worker_status = "healthy" if fresh else "stale"
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
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """Birleştirerek içe aktar (merge import) -- tam geri donus DEGILDIR.

    Idempotent + cakismasiz: `ON CONFLICT DO NOTHING`, var olan kayitlara
    dokunulmaz, eksikler eklenir. Ayni yedek defalarca yuklenebilir.
    Gercek felaket kurtarmasi app disindadir: `make disaster-restore`.
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
    skipped = sum(entry.get("skipped", 0) for entry in summary.values())
    return {"restored": restored, "skipped": skipped, "tables": summary}


@router.post("/backup/inspect")
async def inspect_backup(file: UploadFile = File(...)):
    """Import oncesi preflight: yedegi hicbir sey yazmadan inceler.

    Format versiyonu, tablo/satir sayilari, bilinmeyen tablolar, eksik
    bolumler, secret setting satirlari ve manifest butunlugu raporlanir.
    Kullanici raporu gorup onayladiktan sonra `/backup/restore` cagrilir.
    """
    content = await file.read()
    try:
        payload = restore.parse_backup(content)
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        raise HTTPException(422, f"yedek okunamadi: {exc}") from exc
    return restore.inspect_payload(payload)


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


@router.get("/views", response_model=list[SavedViewOut])
async def list_views(
    module: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Kayitli gorunumler. Sira: sabitlenenler once, sonra konum, sonra id."""
    stmt = select(SavedView).order_by(
        SavedView.pinned.desc(), SavedView.position.asc(), SavedView.id.asc()
    )
    if module:
        stmt = stmt.where(SavedView.module == module)
    return list((await session.execute(stmt)).scalars())


@router.post("/views", response_model=SavedViewOut, status_code=201)
async def create_view(body: SavedViewCreate, session: AsyncSession = Depends(get_session)):
    """Yeni gorunum. position = modul icindeki en buyuk + 1."""
    max_pos = (
        await session.execute(
            select(func.max(SavedView.position)).where(SavedView.module == body.module)
        )
    ).scalar()
    view = SavedView(**body.model_dump(), position=(max_pos or 0) + 1)
    session.add(view)
    await session.commit()
    return view


@router.patch("/views/{view_id}", response_model=SavedViewOut)
async def patch_view(
    view_id: uuid.UUID,
    body: SavedViewPatch,
    session: AsyncSession = Depends(get_session),
):
    """Verilen alanlari gunceller; pinned=true ise view en on konuma cekilir."""
    view = await session.get(SavedView, view_id)
    if view is None:
        raise HTTPException(404, "gorunum bulunamadi")
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(view, key, value)
    if updates.get("pinned") is True:
        view.position = 0
    await session.commit()
    await session.refresh(view)
    return view


@router.delete("/views/{view_id}", status_code=204)
async def delete_view(view_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    view = await session.get(SavedView, view_id)
    if view is None:
        raise HTTPException(404, "gorunum bulunamadi")
    await session.delete(view)
    await session.commit()
