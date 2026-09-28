"""Forkjob collection engine bridged into forkOS' SourceAdapter contract.

The upstream persistence/CLI/web layers are intentionally absent. Every ATS
and portal scraper produces RawItem values; PostgreSQL lifecycle, events,
notifications and health tracking stay native to forkOS.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.sources.base import FetchOutcome, RawItem
from app.sources.forkjob_core.config import load_config
from app.sources.forkjob_core.models import Job
from app.sources.forkjob_core.registry import Registry
from app.sources.forkjob_core.scrapers.base import ScrapeBatch
from app.sources.forkjob_core.scrapers.index import get_scraper, unavailable_reason
from app.sources.forkjob_core.scrapers.registry import LayerBSource, load_registry_b
from app.sources.forkjob_core.sources.adapters import build_adapter
from app.sources.forkjob_core.sources.base import HttpClient

#: Kalici veri dizini. Container'da `/app/data` (compose'da host'a baglanir),
#: repo kopyasinda `backend/data`. Ayni desen yerel belgeler ve gorsel
#: onbelleginde de kullanilir.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CONFIG_PATH = DATA_DIR / "config.yaml"
#: Eski konum: CWD'ye gore `config.yaml` (repo koku / container'da /app).
LEGACY_CONFIG_PATH = Path("config.yaml")


def forkjob_core_config_path() -> Path:
    """Uyum profili (scoring/balance) dosyasinin konumu.

    Kalici veri dizini tercih edilir; eski kurulumdaki `./config.yaml` ilk
    kullanimda oraya DEVRALINIR (kopyalanir, silinmez). Aksi halde gunluk
    runtime'da container yeniden olusturulunca kullanicinin kalibre ettigi
    profil kaybolurdu.
    """
    if not CONFIG_PATH.exists() and LEGACY_CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LEGACY_CONFIG_PATH, CONFIG_PATH)
    return CONFIG_PATH


SCORING = load_config(forkjob_core_config_path())


def job_to_raw(job: Job) -> RawItem:
    row = job.to_row()
    return RawItem(
        external_id=job.external_id or job.job_id,
        title=job.title,
        url=job.url,
        summary=job.description,
        published_at=job.posted_at,
        extra={
            "organization": job.company,
            "location": job.location,
            "city": job.city,
            "country": job.country,
            "remote": job.work_mode.value,
            "compensation": job.salary,
            "department": job.department,
            "language": job.language,
            "forkjob": row,
        },
    )


@dataclass
class AtsBoardSource:
    company: Any
    interval_minutes: int = 360

    @property
    def id(self) -> str:
        return f"forkjob_core:{self.company.source}"

    async def fetch(self) -> list[RawItem]:
        adapter = build_adapter(self.company)
        if adapter is None:
            raise RuntimeError(f"ATS adapter missing: {self.company.ats}")
        async with HttpClient() as client:
            return [job_to_raw(job) for job in await adapter.collect(client)]


@dataclass
class PortalSource:
    portal: LayerBSource
    interval_minutes: int = 720

    @property
    def id(self) -> str:
        return f"forkjob_core:{self.portal.key}"

    @property
    def category(self) -> str:
        """Registry category of the portal (remote, regional, startup, ...).

        Mirrors LayerBSource.category so the catalog can group sources the
        same way the registry does.
        """
        return self.portal.category

    async def fetch(self) -> FetchOutcome:
        scraper = get_scraper(self.portal)
        if scraper is None:
            raise RuntimeError(unavailable_reason(self.portal.key))
        result = await scraper.collect()
        if not isinstance(result, ScrapeBatch):
            return FetchOutcome(items=[job_to_raw(job) for job in result])
        if result.succeeded == 0 and result.errors:
            # Hicbir parca basarili degil: guvenilir sonuc yok, kosum hatadir.
            raise RuntimeError("; ".join(result.errors))
        # Yarim basari KORUNUR: bazi sayfalar/profiller alindiysa kayitlar
        # ingest edilir ama kosum `partial` olur ve kapanma taramasi yapilmaz.
        partial = bool(result.errors) or (
            result.attempted > 0 and result.succeeded < result.attempted
        )
        return FetchOutcome(
            items=[job_to_raw(job) for job in result.jobs],
            partial=partial,
            detail="; ".join(result.errors[:5]) if partial else "",
        )


def forkjob_sources(*, include_opt_in: bool = False) -> list[AtsBoardSource | PortalSource]:
    ats = [AtsBoardSource(company) for company in Registry.load().enabled()]
    portals = load_registry_b().sources
    layer_b = [
        PortalSource(source)
        for source in portals
        if source.enabled or (include_opt_in and source.key == "linkedin")
    ]
    return [*ats, *layer_b]
