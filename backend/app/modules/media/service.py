"""Medya izleme is mantigi (Ryot kulvari, yerel implementasyon).

Kural 1: media_item.entity.id FK; Kural 2: entity helper lar; Kural 3: log_event."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import tags as tag_svc
from app.core.entity import create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.modules.media.models import MediaItem
from app.modules.media.schemas import MediaItemIn, MediaItemOut, MediaItemUpdate, MetadataResult
from app.modules.system.models import Setting

TIMEOUT = httpx.Timeout(20.0)
POLL_MAX = 6

ANILIST_QUERY = """
query ($q: String, $t: MediaType) {
  Page(page: 1, perPage: 6) {
    media(search: $q, type: $t) {
      id
      title { romaji }
      coverImage { large }
      episodes
      chapters
      startDate { year }
    }
  }
}
"""

TMDB_IMAGE = "https://image.tmdb.org/t/p/w200"


# ── Metadata araması (yalnizca inbound OKUMA) ──────────────────────────

async def _tmdb_key(session: AsyncSession) -> str | None:
    row = await session.get(Setting, "media.tmdb_key")
    return row.value if row and row.value else None


async def _tmdb_token(session: AsyncSession) -> str | None:
    # v4 read access token; varsa api_key yerine bearer tercih edilir.
    row = await session.get(Setting, "media.tmdb_token")
    return row.value if row and row.value else None


async def _search_openlibrary(q: str) -> list[MetadataResult]:
    # Kitap: OpenLibrary (anahtarsiz).
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            "https://openlibrary.org/search.json",
            params={
                "q": q,
                "limit": POLL_MAX,
                "fields": "key,title,author_name,first_publish_year,cover_i",
            },
        )
        response.raise_for_status()
    results: list[MetadataResult] = []
    for doc in response.json().get("docs", []):
        cover = doc.get("cover_i")
        results.append(MetadataResult(
            title=doc.get("title") or "(basliksiz)",
            subtitle=", ".join(doc.get("author_name", []) or []) or None,
            cover_url=f"https://covers.openlibrary.org/b/id/{cover}-M.jpg" if cover else None,
            year=doc.get("first_publish_year"),
            metadata={"source": "openlibrary", "ol_key": doc.get("key")},
        ))
    return results


# ── iTunes Search (podcast / muzik / sesli kitap; anahtarsiz) ──────────

ITUNES_MEDIA = {"audiobook": "audiobook", "music": "music", "podcast": "podcast"}


def _bigger_artwork(url: str) -> str:
    # artworkUrl100 -> 200px; thumb sunucusu is1..isX degisebilir, sadece boyut degisir.
    return url.replace("100x100bb", "200x200bb")


def _itunes_results(data: dict, kind: str) -> list[MetadataResult]:
    """iTunes arama yanitini normalized sonuclara cevirir (saf fonksiyon, test edilir)."""
    results: list[MetadataResult] = []
    for row in data.get("results", [])[:POLL_MAX]:
        title = row.get("collectionName") or row.get("trackName") or "(basliksiz)"
        artwork = row.get("artworkUrl100")
        results.append(MetadataResult(
            title=title,
            subtitle=row.get("artistName"),
            cover_url=_bigger_artwork(artwork) if artwork else None,
            metadata={
                "source": "itunes",
                "itunes_id": row.get("collectionId") or row.get("trackId"),
                "itunes_kind": kind,
            },
        ))
    return results


async def _search_itunes(q: str, kind: str) -> list[MetadataResult]:
    # iTunes Search API: term + media; muzikte album kumesi doner.
    params: dict[str, str] = {
        "term": q, "media": ITUNES_MEDIA[kind], "limit": str(POLL_MAX), "country": "US",
    }
    if kind == "music":
        params["entity"] = "album"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get("https://itunes.apple.com/search", params=params)
        response.raise_for_status()
    return _itunes_results(response.json(), kind)


# ── RAWG (oyun; kullanici key'i media.rawg_key) ─────────────────────────

def _rawg_results(data: dict) -> list[MetadataResult]:
    """RAWG arama yanitini normalized sonuclara cevirir (saf fonksiyon, test edilir)."""
    results: list[MetadataResult] = []
    for row in data.get("results", [])[:POLL_MAX]:
        cover = row.get("background_image")
        results.append(MetadataResult(
            title=row.get("name") or "(basliksiz)",
            subtitle=row.get("released"),
            cover_url=cover or None,
            metadata={
                "source": "rawg",
                "rawg_id": row.get("id"),
                "rawg_slug": row.get("slug"),
            },
        ))
    return results


async def _search_rawg(q: str, key: str) -> list[MetadataResult]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            "https://api.rawg.io/api/games",
            params={"key": key, "search": q, "page_size": POLL_MAX},
        )
        response.raise_for_status()
    return _rawg_results(response.json())


async def _rawg_key(session: AsyncSession) -> str | None:
    row = await session.get(Setting, "media.rawg_key")
    return row.value if row and row.value else None


# ── Kitsu (anime/manga yedegi; anahtarsiz) ─────────────────────────────

def _kitsu_results(data: dict, kind: str) -> list[MetadataResult]:
    """Kitsu JSON:API yanitini normalized sonuclara cevirir (saf fonksiyon, test edilir)."""
    results: list[MetadataResult] = []
    for row in data.get("data", [])[:POLL_MAX]:
        attrs = row.get("attributes", {})
        poster = (attrs.get("posterImage") or {}).get("medium")
        amount = attrs.get("episodeCount") or attrs.get("chapterCount")
        subtitle = f"{amount} bolum" if amount else attrs.get("startDate")
        results.append(MetadataResult(
            title=attrs.get("canonicalTitle") or "(basliksiz)",
            subtitle=subtitle,
            cover_url=poster,
            metadata={"source": "kitsu", "kitsu_id": row.get("id"), "kitsu_kind": kind},
        ))
    return results


async def _search_kitsu(q: str, kind: str) -> list[MetadataResult]:
    table = "anime" if kind == "anime" else "manga"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"https://kitsu.io/api/edge/{table}",
            params={"filter[text]": q, "page[limit]": POLL_MAX},
            headers={"Accept": "application/vnd.api+json"},
        )
        response.raise_for_status()
    return _kitsu_results(response.json(), kind)


async def _search_anilist(q: str, kind: str) -> list[MetadataResult]:
    # Anime/Manga: AniList GraphQL (anahtarsiz).
    media_type = "ANIME" if kind == "anime" else "MANGA"
    payload = {"query": ANILIST_QUERY, "variables": {"q": q, "t": media_type}}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post("https://graphql.anilist.co", json=payload)
        if response.status_code == 404:
            return []
        response.raise_for_status()
    data = (response.json().get("data") or {}).get("Page", {}).get("media", [])
    results: list[MetadataResult] = []
    for entry in data:
        title = (entry.get("title") or {}).get("romaji") or "(basliksiz)"
        amount = entry.get("episodes") or entry.get("chapters")
        year = (entry.get("startDate") or {}).get("year")
        results.append(MetadataResult(
            title=title,
            subtitle=f"{amount} bolum" if amount else None,
            cover_url=entry.get("coverImage", {}).get("large"),
            year=year,
            metadata={"source": "anilist", "anilist_id": entry.get("id")},
        ))
    return results


async def _search_tmdb(
    q: str, key: str | None, kind: str, token: str | None = None,
) -> list[MetadataResult]:
    # Film/Dizi: TMDB. Bearer token varsa o kullanilir, yoksa api_key parametresi.
    headers = {"Authorization": f"Bearer {token}"} if token else None
    auth_params: dict[str, str] = {} if token else {"api_key": key or ""}
    results: list[MetadataResult] = []
    for table, ttype in (("movie", "movie"), ("tv", "show")):
        if kind == "movie" and ttype != "movie":
            continue
        if kind in ("show", "anime") and ttype != "show":
            continue
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"https://api.themoviedb.org/3/search/{table}",
                params={**auth_params, "query": q, "language": "en-US"},
                headers=headers,
            )
            for row in response.json().get("results", [])[:3]:
                title = row.get("title") or row.get("name") or "(basliksiz)"
                poster = row.get("poster_path")
                results.append(MetadataResult(
                    title=title,
                    subtitle=row.get("release_date") or row.get("first_air_date"),
                    cover_url=TMDB_IMAGE + poster if poster else None,
                    metadata={"source": "tmdb", "tmdb_id": row.get("id"), "tmdb_type": ttype,
                  "original_title": row.get("original_title") or row.get("original_name")},
                ))
    return results[:POLL_MAX]


async def search_metadata(session: AsyncSession, q: str, kind: str) -> list[MetadataResult]:
    # Tur bazini metadata hizmetine yonlendirir. Yalnizca OKUMA.
    try:
        if kind == "book":
            return await _search_openlibrary(q)
        if kind in ("anime", "manga"):
            try:
                return await _search_anilist(q, kind)
            except (httpx.HTTPStatusError, httpx.RequestError):
                # AniList API zaman zaman kapali (durum 403/sunucu); Kitsu'ya dus.
                return await _search_kitsu(q, kind)
        if kind in ("movie", "show"):
            token = await _tmdb_token(session)
            key = await _tmdb_key(session)
            if not token and not key:
                raise RuntimeError(
                    "TMDB anahtarı yok -- Ayarlardan media.tmdb_key veya "
                    "media.tmdb_token ekle"
                )
            return await _search_tmdb(q, key, kind, token=token)
        if kind in ITUNES_MEDIA:
            return await _search_itunes(q, kind)
        if kind == "game":
            key = await _rawg_key(session)
            if not key:
                raise RuntimeError("RAWG anahtarı yok -- Ayarlardan media.rawg_key ekle")
            return await _search_rawg(q, key)
        return []
    except RuntimeError:
        raise
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        # Dis kaynak coktugunde ham 500 yerine okunabilir 400.
        if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
            detail = f" (HTTP {exc.response.status_code})"
        else:
            detail = ""
        raise RuntimeError(f"Metadata saglayicisi yanit vermedi{detail}") from exc

# ── CRUD ────────────────────────────────────────────────────────────────

async def list_items(
    session: AsyncSession, *, kind: str | None = None,
    status: str | None = None, q: str | None = None,
) -> list[MediaItemOut]:
    stmt = (
        select(MediaItem, Entity.title, Entity.created_at)
        .join(Entity, Entity.id == MediaItem.id)
        .order_by(MediaItem.finished_at.desc().nulls_last(),
                  MediaItem.started_at.desc().nulls_last(), Entity.created_at.desc())
    )
    if kind:
        stmt = stmt.where(MediaItem.kind == kind)
    if status:
        stmt = stmt.where(MediaItem.status == status)
    rows = (await session.execute(stmt)).all()
    tag_map = await tag_svc.tags_for(session, [item.id for item, _, _ in rows])
    return [_to_out(item, title, created_at, tag_map.get(item.id, []))
            for item, title, created_at in rows]


async def get_item(session: AsyncSession, item_id: uuid.UUID) -> MediaItemOut | None:
    row = (await session.execute(
        select(MediaItem, Entity.title, Entity.created_at)
        .join(Entity, Entity.id == MediaItem.id)
        .where(MediaItem.id == item_id)
    )).first()
    if row is None:
        return None
    item, title, created_at = row
    tags = (await tag_svc.tags_for(session, [item_id])).get(item_id, [])
    return _to_out(item, title, created_at, tags)


def _to_out(item: MediaItem, title: str, created_at: datetime | None,
            tags: list[str] | None = None) -> MediaItemOut:
    return MediaItemOut(
        id=item.id, title=title, kind=item.kind, status=item.status,
        progress=item.progress, total=item.total, score=item.score, notes=item.notes,
        started_at=item.started_at, finished_at=item.finished_at,
        meta=item.meta or {}, tags=tags or [], created_at=created_at,
    )


async def create_item(session: AsyncSession, data: MediaItemIn) -> MediaItemOut:
    entity = await create_entity(
        session, type=MediaItem.ENTITY_TYPE, title=data.title.strip(),
        search_text=" ".join(filter(None, [data.notes, str(data.total)])))
    item = MediaItem(
        id=entity.id, kind=data.kind, status=data.status,
        progress=data.progress, total=data.total, score=data.score, notes=data.notes,
        started_at=data.started_at, finished_at=data.finished_at,
        meta=data.meta or {},
    )
    session.add(item)
    if data.tags:
        await tag_svc.add_tags(session, entity.id, data.tags)
    await log_event(session, verb="media.item_added", entity_id=entity.id,
                    entity_type="media_item",
                    payload={"kind": data.kind, "status": data.status, "title": data.title})
    await session.commit()
    return await get_item(session, item.id)


async def update_item(
    session: AsyncSession, item_id: uuid.UUID, data: MediaItemUpdate,
) -> MediaItemOut | None:
    item = await session.get(MediaItem, item_id)
    if item is None:
        return None
    changes: list[str] = []
    if data.status is not None and data.status != item.status:
        changes.append(f"{item.status} -> {data.status}")
        item.status = data.status
        if data.status == "completed" and item.finished_at is None:
            item.finished_at = datetime.now(UTC)
    if data.progress is not None:
        item.progress = data.progress
    if data.total is not None:
        item.total = data.total
    if data.score is not None:
        item.score = data.score
    if data.notes is not None:
        item.notes = data.notes
    if data.started_at is not None:
        item.started_at = data.started_at
    if data.finished_at is not None:
        item.finished_at = data.finished_at
    if data.meta is not None:
        item.meta = data.meta
    if data.tags is not None:
        await tag_svc.set_tags(session, item_id, data.tags)
    if data.title is not None:
        await touch_entity(session, item_id, title=data.title.strip())
    if changes:
        await log_event(session, verb="media.status_changed", entity_id=item_id,
                        entity_type="media_item", payload={"change": "; ".join(changes)})
    await session.commit()
    return await get_item(session, item_id)


async def delete_item(session: AsyncSession, item_id: uuid.UUID) -> bool:
    entity = await session.get(Entity, item_id)
    if entity is None:
        return False
    await log_event(session, verb="media.item_deleted", entity_id=item_id,
                    entity_type="media_item", payload={"title": entity.title})
    await session.flush()
    await delete_entity(session, item_id)
    await session.commit()
    return True


async def stats(session: AsyncSession) -> dict:
    by_kind = dict((await session.execute(
        select(MediaItem.kind, func.count()).group_by(MediaItem.kind)
    )).all())
    by_status = dict((await session.execute(
        select(MediaItem.status, func.count()).group_by(MediaItem.status)
    )).all())
    return {
        "total": sum(by_kind.values()),
        "in_progress": by_status.get("in_progress", 0),
        "completed": by_status.get("completed", 0),
        "planned": by_status.get("planned", 0),
        "by_kind": by_kind,
    }
