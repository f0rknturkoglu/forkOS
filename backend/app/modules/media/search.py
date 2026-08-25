"""Medya arama/metadata servisleri: provider arama, aranabilir liste, imlecli sayfalama."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, EntityTag, Link, Tag
from app.modules.media.models import (
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


async def search_metadata(
    session: AsyncSession, q: str, kind: str, *, provider_id: str | None = None
) -> list[MetadataResult]:
    # provider_registry, service modulu uzerinden cozulur: testler
    # monkeypatch.setattr(service, "provider_registry", ...) ile degistirir.
    from app.modules.media import service as _service

    registry = await _service.provider_registry(session)
    provider = registry.by_id(provider_id, kind=kind) if provider_id else registry.for_kind(kind)
    if provider is None or not provider.ready:
        missing = provider.missing_settings if provider else ()
        suffix = f": {', '.join(missing)}" if missing else ""
        raise RuntimeError(f"{kind} için hazır provider yok{suffix}")
    results = await provider.search(q)
    return [_metadata_result(row, kind) for row in results]


async def search_all_metadata(session: AsyncSession, q: str) -> GlobalMetadataSearchOut:
    from app.modules.media import service as _service

    registry = await _service.provider_registry(session)
    providers: list[tuple[str, MediaProvider]] = [
        variant
        for variants in registry.provider_groups().values()
        for variant in variants
    ]
    ready: list[tuple[str, MediaProvider]] = []
    warnings: list[MetadataSearchWarning] = []

    for kind, provider in providers:
        if provider.ready:
            ready.append((kind, provider))
            continue
        missing = ", ".join(provider.missing_settings)
        suffix = f": {missing}" if missing else ""
        warnings.append(
            MetadataSearchWarning(
                provider=provider.id,
                kind=kind,
                message=f"{kind} için provider hazır değil{suffix}",
            )
        )

    outcomes = await asyncio.gather(
        *(provider.search(q) for _, provider in ready), return_exceptions=True
    )
    results: list[MetadataResult] = []
    seen: set[tuple[str, str]] = set()
    for (kind, provider), outcome in zip(ready, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            logger.warning(
                "Media provider search failed (kind=%s provider=%s error_type=%s)",
                kind,
                provider.id,
                type(outcome).__name__,
            )
            warnings.append(
                MetadataSearchWarning(
                    provider=provider.id,
                    kind=kind,
                    message="Provider araması başarısız",
                )
            )
            continue
        for row in outcome:
            result = _metadata_result(row, kind)
            key = (result.provider, result.provider_id)
            if key not in seen:
                seen.add(key)
                results.append(result)

    return GlobalMetadataSearchOut(results=results, warnings=warnings)


async def list_items(
    session: AsyncSession,
    *,
    kind: str | None = None,
    status: str | None = None,
    q: str | None = None,
    collection_id: uuid.UUID | None = None,
    tag: str | None = None,
    owned: bool | None = None,
    monitored: bool | None = None,
    trashed: bool = False,
    sort: str = "updated",
    cursor: str | None = None,
    limit: int = 48,
) -> MediaPageOut:
    stmt = select(MediaItem, Entity).join(Entity, Entity.id == MediaItem.id)
    stmt = stmt.where(Entity.archived_at.is_not(None) if trashed else Entity.archived_at.is_(None))
    if kind:
        stmt = stmt.where(MediaItem.kind == kind)
    if status:
        stmt = stmt.where(MediaItem.status == status)
    if q:
        for token in q.split():
            pattern = f"%{token}%"
            stmt = stmt.where(or_(Entity.title.ilike(pattern), Entity.search_text.ilike(pattern)))
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
    if monitored is not None:
        stmt = stmt.where(MediaItem.monitored.is_(monitored))
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
    if sort not in orders:
        raise MediaCommandError("Gecersiz media siralamasi")
    offset = _decode_cursor(cursor)
    rows = (await session.execute(stmt.order_by(*orders[sort]).offset(offset).limit(limit))).all()
    next_cursor = _encode_cursor(offset + limit) if offset + len(rows) < total else None
    return MediaPageOut(
        items=[_to_item_out(item, entity) for item, entity in rows],
        total=total,
        next_cursor=next_cursor,
    )
