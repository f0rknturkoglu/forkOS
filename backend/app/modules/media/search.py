"""Medya arama/metadata servisleri: provider arama, aranabilir liste, imlecli sayfalama."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import time
import unicodedata
import uuid

from sqlalchemy import ColumnElement, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, EntityTag, Link, Tag
from app.core.search import match_clause
from app.modules.media.models import (
    KINDS,
    MEDIA_COLLECTION_ITEM_RELATION,
    MediaItem,
)
from app.modules.media.progress import MediaCommandError, _number
from app.modules.media.providers.base import MediaProvider, ProviderResult
from app.modules.media.providers.registry import ProviderRegistry
from app.modules.media.schemas import (
    GlobalMetadataSearchOut,
    MediaItemIn,
    MediaItemOut,
    MediaItemUpdate,
    MediaPageOut,
    MetadataResult,
    MetadataSearchWarning,
)
from app.modules.system.models import Setting

logger = logging.getLogger(__name__)

# Katalog aramasi: provider cagrilari sinirli eszamanlilik + sabit sure butcesi.
SEARCH_CONCURRENCY = 4
SEARCH_TIMEOUT_SECONDS = 8.0
# Kisa omurlu process-local onbellek (ag istegi yok).
SEARCH_CACHE_TTL_SECONDS = 60.0
SEARCH_CACHE_MAX_ENTRIES = 128

# Ham ayar anahtari kullaniciya gosterilmez; insan dili karsiligi burada eslenir.
_MISSING_SETTING_MESSAGES = {
    "media.tmdb_key": "TMDB anahtarı tanımlı değil",
    "media.google_books_key": "Google Books anahtarı tanımlı değil",
    "media.igdb_client_id": "IGDB kimlik bilgileri eksik",
    "media.igdb_client_secret": "IGDB kimlik bilgileri eksik",
}
_MISSING_SETTING_FALLBACK = "Medya sağlayıcı ayarı eksik"

# anahtar: (son kullanma anı, yanıt) — süreç içi, FIFO temizlikli.
_search_cache: dict[
    tuple[str, str | None, str | None, int], tuple[float, GlobalMetadataSearchOut]
] = {}

# NFKD aksanlı harfleri çözer; ayrica çözemeyen Turkce 'ı' elle eslenir.
_TURKISH_FOLD = str.maketrans({"ı": "i", "İ": "i"})


def _fold(value: str) -> str:
    """Kucuk harfe indirip aksanlari sadelestirir (siralama/karsilastirma icin)."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        char for char in decomposed if not unicodedata.combining(char)
    ).translate(_TURKISH_FOLD)


def _tokens(value: str | None) -> list[str]:
    return [token for token in (value or "").split() if token]


def clear_search_cache() -> None:
    """Process-local katalog arama onbellegini bosaltir (testler/elle mudahale)."""
    _search_cache.clear()


def _cache_get(key: tuple[str, str | None, str | None, int]) -> GlobalMetadataSearchOut | None:
    entry = _search_cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if expires_at < time.monotonic():
        _search_cache.pop(key, None)
        return None
    return value


def _cache_put(key: tuple[str, str | None, str | None, int], value: GlobalMetadataSearchOut) -> None:
    if len(_search_cache) >= SEARCH_CACHE_MAX_ENTRIES:
        _search_cache.pop(next(iter(_search_cache)), None)  # en eski giris (FIFO)
    _search_cache[key] = (time.monotonic() + SEARCH_CACHE_TTL_SECONDS, value)


def _missing_settings_message(provider_id: str, missing: tuple[str, ...]) -> str:
    """Eksik ayarlari ham anahtar yerine insan diline cevirir."""
    messages: list[str] = []
    for key in missing:
        text = _MISSING_SETTING_MESSAGES.get(key, _MISSING_SETTING_FALLBACK)
        if text not in messages:
            messages.append(text)
    if not messages:
        return f"{provider_id} sağlayıcısı hazır değil"
    return ", ".join(messages)


def _metadata_rank(result: MetadataResult, folded_query: str, tokens: list[str]) -> int:
    """Katalog sonucu ilgi skoru.

    Sorgu token'larinin tamami baslik/alt baslik/ozet icinde gecmeli; gecmeyen
    sonuclar atilmaz, yalnizca en sona duser (provider zaten sunucu tarafinda
    arama yapti, yerel skor yalnizca siralama icin).
    """
    title = _fold(result.title)
    subtitle = _fold(result.subtitle or "")
    summary = _fold(result.summary or "")
    if tokens and not all(token in f"{title}\n{subtitle}\n{summary}" for token in tokens):
        return 0
    if title == folded_query:
        return 100
    if title.startswith(folded_query):
        return 70
    if folded_query in title:
        return 50
    if folded_query in subtitle or folded_query in summary:
        return 20
    return 10


def _provider_id(item: MediaItem) -> str | None:
    return item.provider_id


def _to_item_out(item: MediaItem, entity: Entity) -> MediaItemOut:
    return MediaItemOut(
        id=item.id,
        title=entity.title,
        kind=item.kind,
        status=item.status,
        progress=_number(item.progress),
        total=_number(item.total),
        score=item.score,
        notes=item.notes,
        started_at=item.started_at,
        finished_at=item.finished_at,
        meta=item.meta or {},
        summary=item.summary,
        release_date=item.release_date,
        progress_measure=item.progress_measure,
        review=item.review,
        favorite=item.favorite,
        owned=item.owned,
        ownership=item.ownership or {},
        monitored=item.monitored,
        provider=item.provider,
        provider_id=_provider_id(item),
        provider_ids=item.provider_ids or {},
        cover_url=item.cover_url,
        cover_path=item.cover_path,
        backdrop_url=item.backdrop_url,
        backdrop_path=item.backdrop_path,
        last_synced_at=item.last_synced_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        archived_at=entity.archived_at,
    )


def _search_text(data: MediaItemIn | MediaItemUpdate) -> str:
    values = [
        getattr(data, "summary", None),
        getattr(data, "notes", None),
        getattr(data, "review", None),
    ]
    meta = getattr(data, "meta", None)
    if meta:
        values.append(json.dumps(meta, ensure_ascii=False, sort_keys=True))
    return " ".join(value for value in values if value)


def _item_search_text(item: MediaItem) -> str:
    values = [item.summary, item.notes, item.review]
    if item.meta:
        values.append(json.dumps(item.meta, ensure_ascii=False, sort_keys=True))
    return " ".join(value for value in values if value)


def _encode_cursor(offset: int) -> str:
    raw = json.dumps({"offset": offset}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded).decode())
        offset = int(value["offset"])
        if offset < 0:
            raise ValueError
        return offset
    except (
        binascii.Error,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
    ) as exc:
        raise MediaCommandError("Gecersiz media cursor") from exc


def _accent_lower(value: ColumnElement[str] | str) -> ColumnElement[str]:
    return func.immutable_unaccent(func.lower(value))


def _token_match_clause(token: str) -> ColumnElement[bool]:
    """Tek token icin: FTS/trigram (match_clause) + aksan duyarsiz alt dizi.

    FTS kelime sinirina takilir, `contains` yazim/ek farkini yakalar; ikisi
    birlikte "Kırmızı" <-> "kirmizi" eslesmesini saglar.
    """
    needle = _accent_lower(token)
    return or_(
        match_clause(token),
        _accent_lower(Entity.title).contains(needle),
        _accent_lower(Entity.search_text).contains(needle),
    )


def _relevance_expression(query: str) -> ColumnElement[int]:
    """Yerel ilgi sirasi: tam baslik > baslikta gecme > search_text > diger."""
    needle = _accent_lower(query)
    title = _accent_lower(Entity.title)
    return case(
        (title == needle, 4),
        (title.contains(needle), 3),
        (_accent_lower(Entity.search_text).contains(needle), 2),
        else_=1,
    )


async def provider_registry(session: AsyncSession) -> ProviderRegistry:
    keys = (
        "media.tmdb_key",
        "media.google_books_key",
        "media.igdb_client_id",
        "media.igdb_client_secret",
    )
    rows = list((await session.execute(select(Setting).where(Setting.key.in_(keys)))).scalars())
    return ProviderRegistry.from_settings({row.key: row.value for row in rows})


def _metadata_result(row: ProviderResult, kind: str) -> MetadataResult:
    return MetadataResult(
        kind=kind,
        provider=row.provider,
        provider_id=row.provider_id,
        title=row.title,
        subtitle=row.subtitle,
        year=row.year,
        summary=row.summary,
        total=row.total,
        progress_measure=row.progress_measure,
        cover=row.cover_url,
        backdrop=row.backdrop_url,
        cover_url=row.cover_url,
        backdrop_url=row.backdrop_url,
        provider_ids=row.provider_ids,
        meta=row.meta,
        metadata={
            **row.meta,
            "provider": row.provider,
            "provider_id": row.provider_id,
            "provider_ids": row.provider_ids,
        },
    )


async def _search_provider(
    kind: str,
    provider: MediaProvider,
    q: str,
    limit: int,
    semaphore: asyncio.Semaphore,
) -> tuple[list[MetadataResult], MetadataSearchWarning | None]:
    """Tek provider varyantini cagirir; hata/sure asimi digerlerini engellemez."""
    async with semaphore:
        try:
            async with asyncio.timeout(SEARCH_TIMEOUT_SECONDS):
                rows = await provider.search(q)
        except TimeoutError:
            logger.warning(
                "Media provider search timed out (kind=%s provider=%s)", kind, provider.id
            )
            return [], MetadataSearchWarning(
                provider=provider.id,
                kind=kind,
                message="Sağlayıcı zaman aşımına uğradı",
            )
        except Exception as exc:  # noqa: BLE001 - provider hatasi digerlerini engellemez
            logger.warning(
                "Media provider search failed (kind=%s provider=%s error_type=%s)",
                kind,
                provider.id,
                type(exc).__name__,
            )
            return [], MetadataSearchWarning(
                provider=provider.id,
                kind=kind,
                message="Provider araması başarısız",
            )
    return [_metadata_result(row, kind) for row in rows[:limit]], None


async def search_all_metadata(
    session: AsyncSession,
    q: str,
    *,
    kind: str | None = None,
    provider: str | None = None,
    limit: int = 6,
) -> GlobalMetadataSearchOut:
    from app.modules.media import service as _service

    folded_query = " ".join(_fold(q).split())
    tokens = folded_query.split()
    cache_key = (folded_query, kind, provider, limit)
    cached = _cache_get(cache_key)
    if cached is not None:
        response = cached.model_copy(deep=True)
        response.cached = True
        return response

    registry = await _service.provider_registry(session)
    groups = registry.provider_groups()
    if kind is not None and kind not in KINDS:
        raise MediaCommandError(f"Gecersiz media kind: {kind}")
    if provider is not None and provider not in groups:
        raise MediaCommandError(f"Gecersiz media provider: {provider}")

    variants = [
        (variant_kind, variant_provider)
        for provider_id, group in groups.items()
        for variant_kind, variant_provider in group
        if (kind is None or variant_kind == kind) and (provider is None or provider_id == provider)
    ]

    ready: list[tuple[str, MediaProvider]] = []
    warnings: list[MetadataSearchWarning] = []
    for variant_kind, variant_provider in variants:
        if variant_provider.ready:
            ready.append((variant_kind, variant_provider))
            continue
        warnings.append(
            MetadataSearchWarning(
                provider=variant_provider.id,
                kind=variant_kind,
                message=_missing_settings_message(
                    variant_provider.id, variant_provider.missing_settings
                ),
            )
        )

    semaphore = asyncio.Semaphore(SEARCH_CONCURRENCY)
    outcomes = await asyncio.gather(
        *(
            _search_provider(variant_kind, variant_provider, q, limit, semaphore)
            for variant_kind, variant_provider in ready
        )
    )

    results: list[MetadataResult] = []
    seen: set[tuple[str, str, str]] = set()
    for (_, _provider), (rows, warning) in zip(ready, outcomes, strict=True):
        if warning is not None:
            warnings.append(warning)
            continue
        for row in rows:
            key = (row.provider, row.provider_id, row.kind)
            if key in seen:
                continue
            seen.add(key)
            results.append(row)

    results.sort(
        key=lambda row: (
            -_metadata_rank(row, folded_query, tokens),
            row.provider,
            _fold(row.title),
        )
    )
    response = GlobalMetadataSearchOut(results=results, warnings=warnings)
    _cache_put(cache_key, response.model_copy(deep=True))
    return response


async def list_items(
    session: AsyncSession,
    *,
    kind: str | None = None,
    status: str | None = None,
    q: str | None = None,
    collection_id: uuid.UUID | None = None,
    tag: str | None = None,
    owned: bool | None = None,
    favorite: bool | None = None,
    monitored: bool | None = None,
    provider: str | None = None,
    trashed: bool = False,
    sort: str = "updated",
    cursor: str | None = None,
    limit: int = 48,
) -> MediaPageOut:
    tokens = _tokens(q)
    stmt = select(MediaItem, Entity).join(Entity, Entity.id == MediaItem.id)
    stmt = stmt.where(Entity.archived_at.is_not(None) if trashed else Entity.archived_at.is_(None))
    if kind:
        stmt = stmt.where(MediaItem.kind == kind)
    if status:
        stmt = stmt.where(MediaItem.status == status)
    for token in tokens:
        stmt = stmt.where(_token_match_clause(token))
    if collection_id:
        stmt = stmt.join(
            Link,
            (Link.to_id == MediaItem.id)
            & (Link.from_id == collection_id)
            & (Link.relation == MEDIA_COLLECTION_ITEM_RELATION),
        )
    if tag:
        stmt = stmt.join(EntityTag, EntityTag.entity_id == MediaItem.id).join(
            Tag, (Tag.id == EntityTag.tag_id) & (func.lower(Tag.name) == tag.lower())
        )
    if owned is not None:
        stmt = stmt.where(MediaItem.owned.is_(owned))
    if favorite is not None:
        stmt = stmt.where(MediaItem.favorite.is_(favorite))
    if monitored is not None:
        stmt = stmt.where(MediaItem.monitored.is_(monitored))
    if provider:
        stmt = stmt.where(func.lower(MediaItem.provider) == provider.strip().lower())
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int((await session.execute(count_stmt)).scalar_one())
    orders = {
        "updated": (Entity.updated_at.desc(), MediaItem.id.desc()),
        "created": (Entity.created_at.desc(), MediaItem.id.desc()),
        "title": (func.lower(Entity.title).asc(), MediaItem.id.asc()),
        "score": (
            MediaItem.score.desc().nulls_last(),
            Entity.updated_at.desc(),
            Entity.id.desc(),
        ),
        "progress": (
            MediaItem.progress.desc().nulls_last(),
            Entity.updated_at.desc(),
            Entity.id.desc(),
        ),
    }
    if sort not in {*orders, "relevance"}:
        raise MediaCommandError("Gecersiz media siralamasi")
    effective_sort = sort
    if tokens and effective_sort == "updated":
        # Router varsayilani "updated" gonderir; sorgu varsa ilgi sirasi kullanilir.
        effective_sort = "relevance"
    elif not tokens and effective_sort == "relevance":
        effective_sort = "updated"
    if effective_sort == "relevance":
        order_by = (
            _relevance_expression(" ".join(tokens)).desc(),
            Entity.updated_at.desc(),
            Entity.id.desc(),
        )
    else:
        order_by = orders[effective_sort]
    offset = _decode_cursor(cursor)
    rows = (await session.execute(stmt.order_by(*order_by).offset(offset).limit(limit))).all()
    next_cursor = _encode_cursor(offset + limit) if offset + len(rows) < total else None
    return MediaPageOut(
        items=[_to_item_out(item, entity) for item, entity in rows],
        total=total,
        next_cursor=next_cursor,
    )
