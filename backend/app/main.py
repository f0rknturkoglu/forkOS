import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app.config import settings
from app.core.models import SourceRun
from app.core.router import router as core_router
from app.db import SessionLocal
from app.integrations.agent.mcp import get_streamable_http_app, mcp_server
from app.modules import MODULES

log = logging.getLogger("api")


async def _startup_critical_catch_up() -> None:
    """Kritik kaynaklari (YLSY/OSYM/YOK, hizli ATS) tazele -- bounded ve sessiz.

    Worker acikken bu is worker'in; kapaliyken uygulama acilisi telafi eder ki
    kritik kaynaklar gunlerce bayat kalmasin. Yalnizca suresi gecmis kritik
    kaynaklar kuyruga girer ve cekim arka planda yapilir; acilis bekletilmez.
    """
    if settings.worker_enabled:
        return
    from app.core import source_sync
    from app.modules.opportunity.worker import critical_source_ids
    from app.modules.system import automation
    from app.worker.jobs import CRITICAL_CATCH_UP_LIMIT, CRITICAL_CATCH_UP_MIN_AGE

    # SINIRLIDIR: acilis tum kritik katalogu degil, en fazla
    # CRITICAL_CATCH_UP_LIMIT kaynagi kuyruga alir (resmi duyurular once).
    ids = critical_source_ids()[:CRITICAL_CATCH_UP_LIMIT]
    if not ids:
        return
    async with SessionLocal() as session:
        if not await automation.is_enabled(session, "opportunity"):
            return
        latest = dict(
            (
                await session.execute(
                    select(SourceRun.source, func.max(SourceRun.started_at))
                    .where(SourceRun.source.in_(ids))
                    .group_by(SourceRun.source)
                )
            ).all()
        )
        cutoff = datetime.now(UTC) - CRITICAL_CATCH_UP_MIN_AGE
        stale = [
            source_id
            for source_id in ids
            if latest.get(source_id) is None or latest[source_id] <= cutoff
        ]
        if not stale:
            return
        batch, queued = await source_sync.create_or_extend_batch(session, stale)
        await session.commit()
    log.info("kritik catch-up: %d kaynak kuyruga alindi (batch %s)", len(queued), batch.id)
    # Cekimi API sureci yurutur; worker sonradan acilsa da ayni kuyrugu paylasir.
    # Gorev referansi tutulur: aksi halde CPython onu toplayabilir.
    from app.worker.jobs import drain_source_sync_batches

    task = asyncio.create_task(drain_source_sync_batches())
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


#: Acilista baslatilan arka plan gorevlerinin referanslari.
_BACKGROUND_TASKS: set[asyncio.Task] = set()


async def _startup_maintenance() -> None:
    """Gunluk hafif bakimi arka planda dene (acilisi BLOKLAMAZ).

    Worker kapaliyken operasyonel budama hic kosmuyordu. Bu gorev gunde en
    fazla bir kez, sinirli ve agsiz calisir; `run_maintenance` gun kapisini
    atomik olarak aldigi icin worker da acikken cift kosmaz.
    """
    from app.modules.system.maintenance import run_maintenance

    async with SessionLocal() as session:
        summary = await run_maintenance(session)
    if summary is None:
        log.info("bakim: bugun zaten kosulmus")
    else:
        log.info("bakim tamamlandi: %s", summary.get("results"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await _startup_critical_catch_up()
    except Exception:  # noqa: BLE001 - acilis, kaynak tazeleme yuzunden dusmemeli
        log.exception("kritik catch-up baslatilamadi")
    # Acilisi bekletmemek icin arka planda; tek seferlik ve gun kapili.
    task = asyncio.create_task(_startup_maintenance())
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)

    # MCP Streamable HTTP session manager lifecycle (tied to FastAPI lifespan)
    if getattr(mcp_server.session_manager, "_has_started", False):
        new_mcp_app = get_streamable_http_app(force_new=True)
        for route in app.routes:
            if getattr(route, "path", None) == "/mcp":
                route.app = new_mcp_app
    else:
        _ = get_streamable_http_app()

    async with mcp_server.session_manager.run():
        yield


app = FastAPI(title="Life OS", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(core_router, prefix="/api")

# Her modul kendi router'ini registry uzerinden verir -- main.py'yi duzenlemene gerek yok
for module in MODULES:
    app.include_router(module.router, prefix="/api")

# H0: Streamable HTTP MCP (loopback / local-only agent interface)
app.mount("/mcp", get_streamable_http_app())


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "modules": [m.id for m in MODULES]}
