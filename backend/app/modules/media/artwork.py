"""Medya gorsel onbellegi: indirme, cozumleme, disk istatistigi ve temizlik."""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.modules.media.models import MediaItem, MediaUnit
from app.modules.media.progress import MediaCommandError
from app.modules.media.schemas import MediaArtworkPruneOut, MediaArtworkStatsOut

logger = logging.getLogger(__name__)

MAX_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_AGE_DAYS = 7
SECONDS_PER_DAY = 24 * 60 * 60

# Provider registry'sinin kullandigi gorsel host'lari; proxy yalnizca bunlara
# istek atar (SSRF yuzeyi dar tutulur).
ALLOWED_ARTWORK_HOSTS = frozenset(
    {
        "image.tmdb.org",
        "covers.openlibrary.org",
        "books.google.com",
        "books.googleusercontent.com",
        "cdn.myanimelist.net",
        "s4.anilist.co",
        "is1-ssl.mzstatic.com",
        "coverartarchive.org",
        "media.rawg.io",
    }
)
ALLOWED_ARTWORK_HOST_SUFFIXES = (".archive.org",)

CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class ArtworkError(ValueError):
    pass


def default_asset_dir() -> Path:
    configured = os.getenv("MEDIA_ASSET_DIR")
    if configured:
        return Path(configured)
    if Path("/app").is_dir():
        return Path("/app/data/media")
    return Path(__file__).resolve().parents[3] / "data" / "media"


def _remove_file(path: Path) -> int | None:
    """Dosyayi siler; basarisizsa None, basariliysa kazanilan bayt sayisi doner."""
    try:
        size = path.stat().st_size
        path.unlink()
    except OSError:
        return None
    return size


def _artwork_host_allowed(host: str) -> bool:
    normalized = host.lower().rstrip(".")
    return normalized in ALLOWED_ARTWORK_HOSTS or normalized.endswith(
        ALLOWED_ARTWORK_HOST_SUFFIXES
    )


class ArtworkStore:
    def __init__(
        self,
        root: str | Path | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        max_bytes: int = MAX_BYTES,
    ) -> None:
        self.root = Path(root) if root else default_asset_dir()
        self.client = client
        self.max_bytes = max_bytes

    @asynccontextmanager
    async def _stream(self, url: str):
        if self.client is not None:
            async with self.client.stream("GET", url, follow_redirects=True) as response:
                yield response
            return
        async with (
            httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client,
            client.stream("GET", url) as response,
        ):
            yield response

    async def cache(self, url: str, *, previous: str | None) -> str:
        """Uzak gorseli sha256 adiyla yerel dizine indirir.

        `previous` yalnizca geriye uyumlu cagri imzasi icin durur ve
        KULLANILMAZ; eski dosya burada silinmez, temizligi `prune` ustlenir.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        digest = hashlib.sha256()
        size = 0
        try:
            async with self._stream(url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0]
                extension = CONTENT_TYPES.get(content_type.lower())
                if extension is None:
                    raise ArtworkError("Desteklenmeyen artwork MIME tipi")
                fd, temporary_name = tempfile.mkstemp(
                    prefix=".artwork-", suffix=".tmp", dir=self.root
                )
                os.close(fd)
                temporary = Path(temporary_name)
                with temporary.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > self.max_bytes:
                            raise ArtworkError("Artwork boyut sınırını aşıyor")
                        digest.update(chunk)
                        handle.write(chunk)
            target = self.root / f"{digest.hexdigest()}{extension}"
            temporary.replace(target)
            return target.name
        except (httpx.HTTPError, OSError) as exc:
            raise ArtworkError(str(exc)) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def resolve(self, asset_name: str) -> Path | None:
        if not asset_name or Path(asset_name).name != asset_name:
            return None
        candidate = self.root / asset_name
        try:
            candidate.resolve().relative_to(self.root.resolve())
        except (OSError, ValueError):
            return None
        return candidate if candidate.is_file() else None

    def stats(self) -> tuple[int, int]:
        """Dizindeki onbellek dosya sayisi ve toplam bayt (gecici dosyalar haric)."""
        files = 0
        total = 0
        if not self.root.is_dir():
            return files, total
        for entry in self.root.iterdir():
            if not entry.is_file() or entry.name.startswith("."):
                continue
            try:
                size = entry.stat().st_size
            except OSError:
                continue
            files += 1
            total += size
        return files, total

    def prune(
        self,
        keep: set[str],
        *,
        max_total_bytes: int | None = None,
        older_than_days: int = MAX_AGE_DAYS,
    ) -> tuple[int, int]:
        """Referanssiz + eski dosyalari, gerekirse en eskiden baslayarak siler.

        Adim 1: `keep` disindaki ve `older_than_days`'ten eski dosyalar silinir.
        Adim 2: toplam boyut `max_total_bytes`'i asarsa en eski (mtime asc)
        dosyalardan baslanarak ek dosya silinir; bu adimda `keep` korumaz cunku
        adim 1 zaten tum yasli referanssiz dosyalari temizler. `older_than_days`
        ten yeni dosyalar (az once yazilanlar) her iki adimda da korunur.
        Donen deger: (silinen dosya, kazanilan bayt).
        """
        limit = MAX_TOTAL_BYTES if max_total_bytes is None else max_total_bytes
        if not self.root.is_dir():
            return 0, 0
        cutoff = time.time() - older_than_days * SECONDS_PER_DAY
        removed = 0
        freed = 0
        survivors: list[tuple[float, str, int]] = []
        for entry in self.root.iterdir():
            if not entry.is_file() or entry.name.startswith("."):
                continue
            try:
                stat = entry.stat()
            except OSError:
                continue
            if entry.name in keep or stat.st_mtime >= cutoff:
                survivors.append((stat.st_mtime, entry.name, stat.st_size))
                continue
            freed_now = _remove_file(entry)
            if freed_now is None:
                survivors.append((stat.st_mtime, entry.name, stat.st_size))
                continue
            removed += 1
            freed += freed_now

        total = self.stats()[1]
        # Butce asilirsa en eski dosyadan baslanir; `keep` bu asamada korumaz
        # (aksi halde adim 2 hicbir zaman is goremez), yeni yazilanlar korunur.
        for mtime, name, _ in sorted(survivors, key=lambda row: (row[0], row[1])):
            if total <= limit:
                break
            if mtime >= cutoff:
                continue
            freed_now = _remove_file(self.root / name)
            if freed_now is None:
                continue
            total -= freed_now
            removed += 1
            freed += freed_now
        return removed, freed


async def artwork_stats() -> MediaArtworkStatsOut:
    files, total = ArtworkStore().stats()
    return MediaArtworkStatsOut(files=files, bytes=total, max_bytes=MAX_TOTAL_BYTES)


async def prune_artwork(session: AsyncSession) -> MediaArtworkPruneOut:
    """DB'de referans edilmeyen gorsel dosyalarini temizler.

    Silme yikici bir islem oldugu icin sonuc `media.artwork_pruned` event'iyle
    de kaydedilir (dosya sayisi + kazanilan bayt); event satiri hangi turda ne
    kadar temizlendigini izlenebilir kilar.
    """
    keep: set[str] = set()
    for column in (MediaItem.cover_path, MediaItem.backdrop_path, MediaUnit.cover_path):
        rows = await session.execute(select(column).where(column.is_not(None)))
        keep.update(Path(value).name for (value,) in rows if value)
    removed, freed = ArtworkStore().prune(keep)
    if removed:
        await log_event(
            session,
            verb="media.artwork_pruned",
            entity_id=None,
            entity_type="media_item",
            payload={"removed": removed, "freed_bytes": freed},
        )
        await session.commit()
    return MediaArtworkPruneOut(removed=removed, freed_bytes=freed)


async def cache_artwork(url: str) -> Path | None:
    """Izinli bir gorsel host'undan indirip yerel dosya yolunu doner."""
    parts = urlsplit(url.strip())
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or not _artwork_host_allowed(parts.hostname)
    ):
        raise MediaCommandError("Bu görsel adresi izinli değil")
    store = ArtworkStore()
    try:
        asset_name = await store.cache(url, previous=None)
    except ArtworkError as exc:
        # Ham hata metni (URL icerebilir) disari sizmasin.
        logger.warning(
            "Artwork indirilemedi (host=%s error_type=%s)", parts.hostname, type(exc).__name__
        )
        raise MediaCommandError("Görsel indirilemedi") from exc
    return store.resolve(asset_name)
