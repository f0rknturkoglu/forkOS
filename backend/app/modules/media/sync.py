from __future__ import annotations

import uuid
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import touch_entity
from app.core.events import log_event
from app.core.models import Entity, SourceRun
from app.core.notifications import notify
from app.core.source_sync import batch_out, create_or_extend_batch, finish_batch_source
from app.db import SessionLocal
from app.modules.media import service
from app.modules.media.artwork import ArtworkError, ArtworkStore
from app.modules.media.models import MediaItem
from app.modules.media.providers.base import (
    ProviderDetails,
    ProviderExpectedEmpty,
    ProviderUnit,
)
from app.modules.media.schemas import MediaUnitUpsert
from app.modules.media.service import provider_registry
from app.modules.system.models import Setting
from app.sources.base import RawItem


class MediaSourceAdapter:
    """Provider snapshot'ını ortak SourceAdapter fetch biçimine çevirir."""

    interval_minutes = 60

    def __init__(self, provider, item: MediaItem, *, upcoming_days: int) -> None:
        self.provider = provider
        self.item = item
        self.upcoming_days = upcoming_days
        self.id = f"media:{provider.id}:{item.id}"

    async def fetch(self) -> list[RawItem]:
        snapshot = getattr(self.provider, "snapshot", None)
        async with snapshot() if snapshot is not None else nullcontext():
            try:
                details = await self.provider.details(str(self.item.provider_id))
                if details is None:
                    return []
                units = (
                    await self.provider.units(str(self.item.provider_id))
                    if self.provider.capabilities.units
                    else []
                )
                upcoming = (
                    await self.provider.upcoming(
                        str(self.item.provider_id),
                        days=self.upcoming_days,
                        units=units,
                    )
                    if self.provider.capabilities.upcoming
                    else []
                )
            except ProviderExpectedEmpty:
                return []
        normalized: dict[tuple[str, str], ProviderUnit] = {}
        for unit in [*units, *upcoming]:
            normalized[(unit.unit_type, unit.provider_id)] = unit
        return [
            RawItem(
                external_id=str(self.item.provider_id),
                title=details.title,
                summary=details.summary,
                extra={"details": details, "units": list(normalized.values())},
            )
        ]


async def provider_statuses(session: AsyncSession) -> list[dict]:
    registry = await provider_registry(session)
    recent = list(
        (
            await session.execute(
                select(SourceRun)
                .where(SourceRun.source.like("media:%"))
                .order_by(SourceRun.started_at.desc(), SourceRun.id.desc())
            )
        ).scalars()
    )
    latest: dict[str, SourceRun] = {}
    for row in recent:
        provider_id = row.source.split(":", 2)[1]
        latest.setdefault(provider_id, row)
    output = []
    for provider_id, variants in registry.provider_groups().items():
        providers = [provider for _, provider in variants]
        capabilities = [provider.capabilities for provider in providers]
        row = latest.get(provider_id)
        output.append(
            {
                "id": provider_id,
                "kinds": list(dict.fromkeys(kind for kind, _ in variants)),
                "capabilities": {
                    "search": any(value.search for value in capabilities),
                    "details": any(value.details for value in capabilities),
                    "units": any(value.units for value in capabilities),
                    "upcoming": any(value.upcoming for value in capabilities),
                    "cache_artwork": any(
                        value.cache_artwork for value in capabilities
                    ),
                    "requires_settings": list(
                        dict.fromkeys(
                            setting
                            for value in capabilities
                            for setting in value.requires_settings
                        )
                    ),
                },
                "ready": any(provider.ready for provider in providers),
                "missing_settings": list(
                    dict.fromkeys(
                        setting
                        for provider in providers
                        for setting in provider.missing_settings
                    )
                ),
                "last_run_at": row.finished_at if row else None,
                "last_status": row.status if row else None,
                "last_error": row.error if row else None,
            }
        )
    return output


async def queue_sync(
    session: AsyncSession,
    *,
    provider_id: str | None = None,
    item_id: uuid.UUID | None = None,
) -> dict | None:
    registry = await provider_registry(session)
    if item_id:
        row = (
            await session.execute(
                select(MediaItem, Entity)
                .join(Entity, Entity.id == MediaItem.id)
                .where(MediaItem.id == item_id)
            )
        ).first()
        if row is None:
            raise ValueError("Medya bulunamadı")
        item, entity = row
        if entity.archived_at is not None or not item.monitored:
            raise ValueError("Yalnızca takip edilen aktif medya senkronize edilebilir")
        selected = provider_id or item.provider
        if not selected or selected != item.provider:
            raise ValueError("Öğenin provider kimliğiyle eşleşen provider gerekli")
        provider = registry.by_id(selected, kind=item.kind)
        if provider is None or not provider.ready:
            raise ValueError("Provider hazır değil")
        source_ids = [f"media:{selected}:{item.id}"]
    else:
        stmt = (
            select(MediaItem.provider, MediaItem.kind)
            .join(Entity, Entity.id == MediaItem.id)
            .where(
                MediaItem.monitored.is_(True),
                MediaItem.provider.is_not(None),
                Entity.archived_at.is_(None),
            )
            .distinct()
        )
        rows = (await session.execute(stmt)).all()
        applicable = [
            (selected, kind)
            for selected, kind in rows
            if not provider_id or selected == provider_id
        ]
        if provider_id and applicable:
            readiness = [registry.by_id(provider_id, kind=kind) for _, kind in applicable]
            not_ready = [
                provider
                for provider in readiness
                if provider is None or not provider.ready
            ]
            if not_ready:
                missing = sorted(
                    {
                        key
                        for provider in not_ready
                        if provider is not None
                        for key in provider.missing_settings
                    }
                )
                suffix = f": {', '.join(missing)}" if missing else ""
                raise ValueError(f"Provider hazır değil{suffix}")
        source_ids = []
        for selected, kind in rows:
            if provider_id and selected != provider_id:
                continue
            provider = registry.by_id(selected, kind=kind)
            if provider and provider.ready:
                source_ids.append(f"media:{selected}")
        source_ids = list(dict.fromkeys(source_ids))
        if provider_id and not registry.by_id(provider_id):
            raise ValueError("Provider bulunamadı")
    if not source_ids:
        return None
    batch, _ = await create_or_extend_batch(session, source_ids, scope="media")
    await session.commit()
    return batch_out(batch)


async def _cache_artwork(
    store: ArtworkStore,
    url: str | None,
    previous: str | None,
    *,
    allowed: bool,
) -> str | None:
    if not url or not allowed:
        return previous
    try:
        asset_name = await store.cache(url, previous=previous)
        return f"/api/media/assets/{asset_name}"
    except ArtworkError:
        return previous


async def _apply_snapshot(
    session: AsyncSession,
    item: MediaItem,
    details: ProviderDetails,
    units: list[ProviderUnit],
    *,
    cache_artwork: bool,
    upcoming_days: int,
) -> int:
    store = ArtworkStore()
    before = (
        item.provider_id,
        item.summary,
        item.release_date,
        item.total,
        item.progress_measure,
        item.cover_url,
        item.backdrop_url,
        item.provider_ids,
        item.meta,
    )
    item.summary = details.summary
    item.release_date = details.release_date
    item.total = details.total
    item.progress_measure = details.progress_measure
    item.cover_url = details.cover_url
    item.backdrop_url = details.backdrop_url
    item.provider_ids = {**(item.provider_ids or {}), **details.provider_ids}
    item.meta = {**(item.meta or {}), **details.meta}
    item.provider_id = details.provider_id
    item.cover_path = await _cache_artwork(
        store, details.cover_url, item.cover_path, allowed=cache_artwork
    )
    item.backdrop_path = await _cache_artwork(
        store, details.backdrop_url, item.backdrop_path, allowed=cache_artwork
    )
    after = (
        item.provider_id,
        item.summary,
        item.release_date,
        item.total,
        item.progress_measure,
        item.cover_url,
        item.backdrop_url,
        item.provider_ids,
        item.meta,
    )
    metadata_changed = before != after
    item.last_synced_at = datetime.now(UTC)
    await touch_entity(session, item.id, title=details.title, search_text=details.summary or "")

    discovered = 0
    changed_units = 0
    for unit in units:
        publisher_art = bool(unit.meta.get("publisher_artwork"))
        cover_path = await _cache_artwork(
            store,
            unit.cover_url,
            None,
            allowed=cache_artwork or publisher_art,
        )
        result = await service.upsert_unit_in_transaction(
            session,
            item.id,
            MediaUnitUpsert(
                title=unit.title,
                unit_type=unit.unit_type,
                number=unit.number,
                duration_min=unit.duration_min,
                release_at=unit.release_at,
                progress_total=unit.progress_total,
                progress_measure=unit.progress_measure,
                provider=details.provider,
                provider_id=unit.provider_id,
                provider_ids=unit.provider_ids,
                cover_url=unit.cover_url,
                cover_path=cover_path,
                meta=unit.meta,
            ),
        )
        changed_units += int(result.changed)
        if result.created:
            discovered += 1
            await log_event(
                session,
                verb="media.release_discovered",
                entity_id=item.id,
                entity_type="media_item",
                payload={
                    "title": unit.title,
                    "unit_id": str(result.id),
                    "release_at": unit.release_at.isoformat() if unit.release_at else None,
                    "provider": details.provider,
                    "provider_id": unit.provider_id,
                },
            )
        now = datetime.now(UTC)
        if unit.release_at and now < unit.release_at <= now + timedelta(days=upcoming_days):
            await notify(
                session,
                kind="media_release",
                title=f"Yaklaşan yayın: {unit.title}",
                body=unit.release_at.isoformat(),
                dedup_key=(
                    f"media-release:{item.id}:{details.provider}:{unit.provider_id}"
                ),
                entity_id=item.id,
            )
    return changed_units or discovered or int(metadata_changed)


async def _record_failure_health(
    session: AsyncSession, source: str, status: str, item_id: uuid.UUID | None
) -> None:
    recent = list(
        (
            await session.execute(
                select(SourceRun.status)
                .where(SourceRun.source == source, SourceRun.status != "running")
                .order_by(SourceRun.started_at.desc(), SourceRun.id.desc())
                .limit(3)
            )
        ).scalars()
    )
    if len(recent) < 3 or any(value not in {"empty", "error"} for value in recent):
        return
    provider_id = source.split(":", 2)[1]
    await notify(
        session,
        kind="media_sync",
        title=f"{provider_id} medya senkronu başarısız",
        body="Son üç beklenen koşu veri bulamadı veya hata verdi.",
        dedup_key=f"media-sync-health:{provider_id}",
        entity_id=item_id,
        importance=2,
    )
    await log_event(
        session,
        verb="media.sync_failed" if status == "error" else "media.sync_empty",
        entity_id=item_id,
        entity_type="media_item" if item_id else "media_sync",
        payload={"source": source, "consecutive_failures": 3},
    )


async def poll_media_source(source_id: str, *, batch_id: uuid.UUID | None = None) -> int:
    parts = source_id.split(":", 2)
    if len(parts) < 2 or parts[0] != "media":
        raise ValueError("Geçersiz media source kimliği")
    provider_id = parts[1]
    item_id = uuid.UUID(parts[2]) if len(parts) == 3 else None
    async with SessionLocal() as session:
        stmt = (
            select(MediaItem, Entity)
            .join(Entity, Entity.id == MediaItem.id)
            .where(
                MediaItem.provider == provider_id,
                MediaItem.monitored.is_(True),
                Entity.archived_at.is_(None),
            )
        )
        if item_id:
            stmt = stmt.where(MediaItem.id == item_id)
        rows = (await session.execute(stmt)).all()
        run = None
        if batch_id:
            run = (
                await session.execute(
                    select(SourceRun)
                    .where(
                        SourceRun.batch_id == batch_id,
                        SourceRun.source == source_id,
                        SourceRun.status == "running",
                    )
                    .order_by(SourceRun.id.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
        if not rows:
            if batch_id:
                if run is None:
                    run = SourceRun(source=source_id, status="running", batch_id=batch_id)
                    session.add(run)
                await session.flush()
                run.status = "empty"
                run.finished_at = datetime.now(UTC)
                await finish_batch_source(session, batch_id, status="empty")
                await session.commit()
            return 0
        if run is None:
            run = SourceRun(source=source_id, status="running", batch_id=batch_id)
            session.add(run)
        await session.commit()
        run_id = run.id
        changed = 0
        snapshots_found = 0
        status = "empty"
        error = None
        try:
            registry = await provider_registry(session)
            upcoming_setting = await session.get(Setting, "media.upcoming_days")
            upcoming_days = (
                int(upcoming_setting.value)
                if upcoming_setting and upcoming_setting.value is not None
                else 30
            )
            for item, _ in rows:
                provider = registry.by_id(provider_id, kind=item.kind)
                if provider is None or not provider.ready:
                    raise RuntimeError(f"Provider hazır değil: {provider_id}")
                snapshots = await MediaSourceAdapter(
                    provider, item, upcoming_days=upcoming_days
                ).fetch()
                snapshots_found += len(snapshots)
                for snapshot in snapshots:
                    changed += await _apply_snapshot(
                        session,
                        item,
                        snapshot.extra["details"],
                        snapshot.extra["units"],
                        cache_artwork=provider.capabilities.cache_artwork,
                        upcoming_days=upcoming_days,
                    )
            status = "ok" if snapshots_found else "empty"
            if changed:
                await log_event(
                    session,
                    verb="media.sync_completed",
                    entity_id=item_id,
                    entity_type="media_item" if item_id else "media_sync",
                    payload={"source": source_id, "count": changed},
                )
        except Exception as exc:
            await session.rollback()
            status = "error"
            error = f"{type(exc).__name__}: {exc}"[:2000]
            changed = 0
        run = await session.get(SourceRun, run_id)
        if run is None:
            raise RuntimeError("Source run kaydı kayboldu")
        run.status = status
        run.items_found = changed
        run.error = error
        run.finished_at = datetime.now(UTC)
        await session.flush()
        if status in {"empty", "error"}:
            await _record_failure_health(session, source_id, status, item_id)
        if batch_id:
            await finish_batch_source(session, batch_id, status=status, items_found=changed)
        await session.commit()
        return changed


async def poll_media_sources(*, ignore_interval: bool = False) -> int:
    async with SessionLocal() as session:
        interval = await session.get(Setting, "media.sync_interval_hours")
        hours = int(interval.value) if interval and interval.value is not None else 24
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        stmt = (
            select(MediaItem.id, MediaItem.provider)
            .join(Entity, Entity.id == MediaItem.id)
            .where(
                MediaItem.monitored.is_(True),
                MediaItem.provider.is_not(None),
                Entity.archived_at.is_(None),
            )
        )
        if not ignore_interval:
            stmt = stmt.where(
                (MediaItem.last_synced_at.is_(None)) | (MediaItem.last_synced_at <= cutoff)
            )
        due_items = (await session.execute(stmt.order_by(MediaItem.last_synced_at))).all()
    total = 0
    for item_id, provider_id in due_items:
        total += await poll_media_source(f"media:{provider_id}:{item_id}")
    return total
