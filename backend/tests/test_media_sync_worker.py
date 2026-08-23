from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.models import Event, Notification, SourceRun
from app.db import SessionLocal
from app.modules.media import service
from app.modules.media.models import MediaUnit
from app.modules.media.providers.base import (
    ProviderCapabilities,
    ProviderDetails,
    ProviderUnit,
)
from app.modules.media.schemas import MediaItemIn
from app.modules.media.sync import poll_media_source, poll_media_sources


class FakeProvider:
    id = "tmdb"
    kinds = ("show",)
    capabilities = ProviderCapabilities(units=True, upcoming=True)
    ready = True
    missing_settings = ()

    async def details(self, provider_id: str):
        return ProviderDetails(
            provider=self.id,
            provider_id=provider_id,
            title="Severance",
            summary="Work is mysterious.",
            total=2,
            progress_measure="episode",
        )

    async def units(self, provider_id: str):
        return [
            ProviderUnit(
                provider_id=f"{provider_id}:2",
                title="Hello, Ms. Cobel",
                unit_type="episode",
                number=2,
                release_at=datetime.now(UTC) + timedelta(days=2),
                progress_total=1,
                progress_measure="episode",
            )
        ]


class FakeRegistry:
    def by_id(self, provider_id: str, *, kind: str | None = None):
        return FakeProvider() if provider_id == "tmdb" else None


class FailingProvider(FakeProvider):
    async def details(self, provider_id: str):
        raise RuntimeError("upstream unavailable")


class FailingRegistry:
    def by_id(self, provider_id: str, *, kind: str | None = None):
        return FailingProvider()


class EmptyProvider(FakeProvider):
    async def details(self, provider_id: str):
        return None


class EmptyRegistry:
    def by_id(self, provider_id: str, *, kind: str | None = None):
        return EmptyProvider()


async def test_automatic_poll_with_no_monitored_items_writes_no_source_run(monkeypatch):
    from app.modules.media import sync as media_sync

    monkeypatch.setattr(media_sync, "provider_registry", lambda session: _async(FakeRegistry()))
    assert await poll_media_sources(ignore_interval=True) == 0

    async with SessionLocal() as session:
        count = await session.scalar(
            select(func.count()).select_from(SourceRun).where(SourceRun.source.like("media:%"))
        )
    assert count == 0


async def test_provider_poll_upserts_unit_and_logs_release_only_once(monkeypatch):
    from app.modules.media import sync as media_sync

    monkeypatch.setattr(media_sync, "provider_registry", lambda session: _async(FakeRegistry()))
    async with SessionLocal() as session:
        item = await service.create_item(
            session,
            MediaItemIn(
                source="provider",
                title="Severance",
                kind="show",
                provider="tmdb",
                provider_id="95396",
                monitored=True,
            ),
        )

    assert await poll_media_source(f"media:tmdb:{item.id}") == 1
    assert await poll_media_source(f"media:tmdb:{item.id}") == 0

    async with SessionLocal() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(MediaUnit).where(MediaUnit.media_id == item.id)
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Event)
                .where(Event.entity_id == item.id, Event.verb == "media.release_discovered")
            )
            == 1
        )
        runs = list(
            (
                await session.execute(
                    select(SourceRun)
                    .where(SourceRun.source == f"media:tmdb:{item.id}")
                    .order_by(SourceRun.id)
                )
            ).scalars()
        )
        # Başarılı snapshot, değişiklik olmasa da upstream sağlıklıdır.
        assert [run.status for run in runs] == ["ok", "ok"]


async def test_three_provider_errors_create_one_deduplicated_notification(monkeypatch):
    from app.modules.media import sync as media_sync

    monkeypatch.setattr(media_sync, "provider_registry", lambda session: _async(FailingRegistry()))
    async with SessionLocal() as session:
        item = await service.create_item(
            session,
            MediaItemIn(
                source="provider",
                title="Severance",
                kind="show",
                provider="tmdb",
                provider_id="95396",
                monitored=True,
            ),
        )

    for _ in range(4):
        assert await poll_media_source(f"media:tmdb:{item.id}") == 0

    async with SessionLocal() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.dedup_key == "media-sync-health:tmdb")
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Event)
                .where(Event.entity_id == item.id, Event.verb == "media.sync_failed")
            )
            == 2
        )


async def test_three_unexpected_empty_snapshots_log_empty_health_event(monkeypatch):
    from app.modules.media import sync as media_sync

    monkeypatch.setattr(media_sync, "provider_registry", lambda session: _async(EmptyRegistry()))
    async with SessionLocal() as session:
        item = await service.create_item(
            session,
            MediaItemIn(
                source="provider",
                title="Severance",
                kind="show",
                provider="tmdb",
                provider_id="95396",
                monitored=True,
            ),
        )

    for _ in range(3):
        assert await poll_media_source(f"media:tmdb:{item.id}") == 0

    async with SessionLocal() as session:
        verbs = list(
            (await session.execute(select(Event.verb).where(Event.entity_id == item.id))).scalars()
        )
        assert "media.sync_empty" in verbs
        assert "media.sync_failed" not in verbs


async def _async(value):
    return value
