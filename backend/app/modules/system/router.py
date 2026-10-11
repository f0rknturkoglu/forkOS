from __future__ import annotations

import json
import uuid
from contextlib import suppress
from datetime import datetime
from typing import Any, Literal

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.core.events import log_event
from app.core.heartbeat import WORKER_HEARTBEAT_KEY, heartbeat_is_fresh
from app.core.local_ui import StudioRoute
from app.core.models import SavedView
from app.core.schemas import SavedViewCreate, SavedViewOut, SavedViewPatch
from app.db import get_session
from app.integrations.agent import status as agent_status_svc
from app.modules.system import (
    automation,
    backup,
    experience,
    export,
    news,
    refresh,
    restore,
    stats,
    storage_report,
)
from app.modules.system.models import Setting
from app.modules.system.settings_schema import DEFAULTS, RUNTIME_SETTING_KEYS, validate_setting

router = APIRouter(tags=["system"])


class AutomationProfileIn(BaseModel):
    profile: str = Field(min_length=1, max_length=32)


class SettingIn(BaseModel):
    value: Any


class ManualRefreshIn(BaseModel):
    """Yenileme kapsami. Govde verilmezse `standard`."""

    scope: Literal["critical", "standard", "full"] = "standard"


class ManualRefreshOut(BaseModel):
    status: str
    #: Calisan/son calisan yenilemenin kapsami (bkz. refresh.REFRESH_SCOPES).
    scope: str = "standard"
    #: Calisan yenilemenin kaynak kuyrugu kimligi (ilerleme takibi icin).
    batch_id: str | None = None
    #: Yalnizca POST yanitinda anlamli: bu istek yeni bir yenileme baslatti mi?
    started: bool = False
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
    body: ManualRefreshIn | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Manuel yenileme baslat.

    Kapsam kritik/standart/tam secilebilir. Zaten calisan bir yenileme varsa
    ikincisi baslatilmaz; ayni istek yanitiyla mevcut durum doner.
    """
    value, started = await refresh.queue(session, scope=(body.scope if body else "standard"))
    if started:
        background.add_task(refresh.run)
    return {**value, "started": started}


@router.get("/settings")
async def settings(session: AsyncSession = Depends(get_session)):
    result = dict(DEFAULTS)
    rows = list((await session.execute(select(Setting))).scalars())
    result.update({item.key: item.value for item in rows
                   if not item.key.startswith(("media.", "finance.", "automation.media."))
                   and item.key != "backup.drive_folder_id"})
    return result


@router.put("/settings/{key:path}")
async def put_setting(key: str, body: SettingIn, session: AsyncSession = Depends(get_session)):
    if key == "product.experience.v1":
        raise HTTPException(422, "Bu tercih sürümlü ürün sözleşmesiyle kaydedilmeli")
    problem = validate_setting(key, body.value)
    if problem is not None:
        raise HTTPException(422, f"{key}: {problem}")
    item = await session.get(Setting, key)
    if item is None:
        item = Setting(key=key, value=body.value)
        session.add(item)
    else:
        item.value = body.value
    # Kural 3: anlamli aksiyon -> event. Ayrica yedegin "degisti mi?" sinyali
    # event gecmisinden turedigi icin bu kayit olmadan ayar degisiklikleri
    # yedegi tetiklemezdi.
    await log_event(session, verb="settings.updated", payload={"key": key})
    await session.commit()
    return {"key": key, "value": body.value}


@router.post("/settings/reset")
async def reset_settings(session: AsyncSession = Depends(get_session)):
    """Tum kullanici ayarlarini siler: GET /settings yeniden varsayilan doner.

    OAuth token'lari AYRI tabloda (integrations.oauth_token) -- bu uc onlara
    dokunmaz. Worker kalp atisi ve elle senkron durumu sistem durumudur,
    silinirse panel "bilinmiyor" gosterir; onlar korunur.
    """
    rows = list((await session.execute(select(Setting))).scalars())
    removed = [row for row in rows if row.key not in RUNTIME_SETTING_KEYS]
    for row in removed:
        await session.delete(row)
    await log_event(session, verb="settings.reset", payload={"removed": len(removed)})
    await session.commit()
    return {"removed": len(removed)}


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

    heartbeat = await session.get(Setting, WORKER_HEARTBEAT_KEY)
    heartbeat_at = None
    if heartbeat and isinstance(heartbeat.value, dict):
        heartbeat_at = heartbeat.value.get("at")
    worker_status = "unknown" if app_settings.worker_enabled else "disabled"
    if app_settings.worker_enabled and isinstance(heartbeat_at, str):
        try:
            observed = datetime.fromisoformat(heartbeat_at)
            worker_status = "healthy" if heartbeat_is_fresh(observed) else "stale"
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


@router.get("/system/storage")
async def system_storage(session: AsyncSession = Depends(get_session)):
    """Depolama dokumu + esik uyarilari (diagnostics; polling icin DEGIL)."""
    report = await storage_report.storage_report(session)
    return {**report, "warnings": storage_report.warnings(report)}


@router.get("/system/automation")
async def automation_state(session: AsyncSession = Depends(get_session)):
    """Arka plan otomasyonu durumu (arayuz icin tek okuma).

    `modules.disabled`'tan AYRI: gorunurluk ve ag trafigi farkli sorulardir.
    """
    return await automation.snapshot(session)


@router.post("/system/automation/profile")
async def set_automation_profile(
    body: AutomationProfileIn, session: AsyncSession = Depends(get_session)
):
    """Profili uygula (manual/balanced/active): ilgili ayarlar birlikte yazilir."""
    try:
        applied = await automation.set_profile(session, body.profile)
    except ValueError as exc:
        raise HTTPException(422, "geçersiz profil") from exc
    await log_event(
        session,
        verb="system.automation_profile",
        payload={"profile": body.profile, "applied": applied},
    )
    await session.commit()
    return await automation.snapshot(session)


@router.get("/backup/status")
async def backup_status(session: AsyncSession = Depends(get_session)):
    """Son yerel yedek ve yedek kapsami -- tek bakisla."""
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
    Yalnız kaydedilmiş opt-in kaynak listesi kullanılır.
    """
    if not await experience.enabled(session, "reddit"):
        return []
    prefs = await experience.read(session)
    subs = prefs.feed.subreddits
    try:
        return await news.fetch_news_source(session, news.RedditNewsSource(subs), limit)
    except (httpx.HTTPError, RuntimeError) as exc:
        raise HTTPException(502, f"reddit okunamadi: {exc}") from exc


@router.get("/news/hacker-news")
async def hacker_news(
    limit: int = Query(15, ge=1, le=40),
    session: AsyncSession = Depends(get_session),
):
    try:
        if not await experience.enabled(session, "hn"):
            return []
        return await news.hacker_news(session, limit)
    except (httpx.HTTPError, RuntimeError) as exc:
        raise HTTPException(502, f"Hacker News okunamadı: {exc}") from exc


@router.get("/news/github-trending")
async def github_trending(
    limit: int = Query(10, ge=1, le=40),
    session: AsyncSession = Depends(get_session),
):
    try:
        if not await experience.enabled(session, "gh"):
            return []
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


# ── Hava durumu proxy'si ────────────────────────────────────────────────
# Tarayici open-meteo'ya DOGRUDAN gitmez: istek backend'den cikar. Boylece
# arayuz local-only kalir (dis DNS/IP sizintisi yok) ve zaman asimi/UA
# politikasi tek yerde durur. Veri DB'ye yazilmaz -- canli gecis.

WEATHER_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
WEATHER_HEADERS = {"User-Agent": "forkOS/0.1 (+local-only personal workspace)"}
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class GeocodeOut(BaseModel):
    name: str
    latitude: float
    longitude: float
    country: str | None = None
    admin1: str | None = None


@router.get("/weather/geocode", response_model=GeocodeOut)
async def weather_geocode(
    query: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
):
    """Sehir adi -> koordinat; lat/lon verilirse ters yon (koordinat -> ad).

    Ters mod, tarayici konum izniyle bulunan noktayi Ayarlar'da ada cevirmek
    icin. Ikisi de ayni dis servisi kullanir, tek ucta toplanir.
    """
    if lat is not None and lon is not None:
        params: dict[str, Any] = {"latitude": lat, "longitude": lon, "count": 1, "language": "tr"}
    elif query and query.strip():
        params = {"name": query.strip(), "count": 1, "language": "tr"}
    else:
        raise HTTPException(422, "query ya da lat/lon gerekli")

    try:
        async with httpx.AsyncClient(timeout=WEATHER_TIMEOUT, headers=WEATHER_HEADERS) as client:
            response = await client.get(GEOCODE_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, f"Konum servisine ulasilamadi: {exc}") from exc

    results = payload.get("results") or []
    if not results:
        raise HTTPException(404, "Konum bulunamadi")
    hit = results[0]
    return GeocodeOut(
        name=hit.get("name") or (query or "").strip() or "Konumum",
        latitude=float(hit["latitude"]),
        longitude=float(hit["longitude"]),
        country=hit.get("country"),
        admin1=hit.get("admin1"),
    )


@router.get("/weather/forecast")
async def weather_forecast(lat: float, lon: float):
    """Open-Meteo tahmini -- arayuzun bekledigi alanlar aynen gecirilir."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,relative_humidity_2m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "timezone": "auto",
        "forecast_days": 4,
    }
    try:
        async with httpx.AsyncClient(timeout=WEATHER_TIMEOUT, headers=WEATHER_HEADERS) as client:
            response = await client.get(FORECAST_URL, params=params)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, f"Hava durumu alinamadi: {exc}") from exc


# ── Ajan (MCP) durumu ───────────────────────────────────────────────────
# Ayarlar ekraninin H0–H7 yetenek haritasini ve yerel bilis sagligini tek
# okumada gormesi icin SALT OKUNUR teshis ucu. Hicbir sey yazilmaz, DB'ye
# dokunulmaz; aga yalnizca H4 acikken sinirli loopback Ollama probu cikar.
# Is mantigi `app.integrations.agent.status` icindedir -- burada yalnizca
# sekil (typed response model) ve gercek baglanma portu tasinir.


class FamilyOut(BaseModel):
    """Bir Hermes fazinin (H0–H7) disa vurulan ozeti."""

    id: str
    label: str
    summary: str
    tool_count: int


class BrainStatusOut(BaseModel):
    """MCP Brain Interface kimligi ve yetenek haritasi."""

    server_name: str
    endpoint: str
    transport: str
    loopback_only: bool
    tool_count: int
    families: list[FamilyOut]


class SlotOut(BaseModel):
    """Tek yerel model slotunun yapilandirma/kurulum durumu."""

    configured: bool
    available: bool


class LocalCognitionOut(BaseModel):
    """H4 yerel bilis durumu. `reachable` yalnizca prob atildiysa doludur."""

    enabled: bool
    provider: str
    #: Yapilandirilmis adresin sinifi: `invalid` ise loopback kurali ihlal
    #: edilmis demektir -- bu, arayuzde gorunmesi gereken bir guvenlik olayidir.
    endpoint_class: Literal["loopback", "invalid"]
    configured: bool
    reachable: bool | None
    state: Literal[
        "disabled",
        "not_configured",
        "provider_unreachable",
        "model_missing",
        "ready",
    ]
    small: SlotOut
    medium: SlotOut
    detail: str | None


class AgentStatusOut(BaseModel):
    """`GET /api/agent/status` govdesi."""

    brain: BrainStatusOut
    local_cognition: LocalCognitionOut


@router.get("/agent/status", response_model=AgentStatusOut)
async def agent_status(request: Request) -> AgentStatusOut:
    """Ajan yetenek haritasi + yerel bilis durumu (salt okunur teshis).

    Adres gercek baglanma portundan kurulur (`scope["server"]`), Host
    basligindan DEGIL: arayuz hangi adresten baglanacagini boylece dogru
    ogrenir. H4 kapaliyken hicbir ag cagrisi yapilmaz.
    """
    payload = await agent_status_svc.agent_status_payload(server=request.scope.get("server"))
    return AgentStatusOut.model_validate(payload)


@router.get("/system/career-ops/doctor")
async def career_ops_doctor():
    """career-ops yetenek motoru tanı ve durum raporu (salt okunur)."""
    from app.integrations.career_ops.adapter import CareerOpsAdapter

    adapter = CareerOpsAdapter()
    res = await adapter.doctor()
    return res.model_dump()



experience_router = APIRouter(route_class=StudioRoute)


@experience_router.get("/system/experience", response_model=experience.ExperienceOut)
async def get_experience(session: AsyncSession = Depends(get_session)):
    return await experience.read(session)


@experience_router.put("/system/experience", response_model=experience.ExperienceOut)
async def put_experience(body: experience.ExperienceUpdate, session: AsyncSession = Depends(get_session)):
    return await experience.update(session, body)


@experience_router.post("/system/experience/repair", response_model=experience.ExperienceOut)
async def repair_experience(body: experience.ExperienceRepairIn, session: AsyncSession = Depends(get_session)):
    return await experience.repair_feed_memberships(session, expected_revision=body.revision)


@router.get("/news/huggingface-papers")
async def huggingface_papers(date: str | None = None, limit: int = Query(20, ge=1, le=30), session: AsyncSession = Depends(get_session)):
    if not await experience.enabled(session, "hf"):
        return []
    from app.sources.news import HuggingFacePapersSource
    try:
        source = HuggingFacePapersSource(date=date)
        return await news.fetch_news_source(session, source, limit)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "Hugging Face Papers alınamadı") from exc


router.include_router(experience_router)
