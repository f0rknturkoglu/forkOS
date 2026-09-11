from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.models import Entity, Event, Notification, SourceRun
from app.core.source_sync import create_or_extend_batch, current_status
from app.db import SessionLocal
from app.modules.media import service
from app.modules.media.models import MediaItem, MediaUnit
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
                release_at=datetime(2030, 1, 2, tzinfo=UTC),
                progress_total=1,
                progress_measure="episode",
            )
        ]

    async def upcoming(self, provider_id: str, *, days: int, units=None):
        return []


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


class UpcomingProvider(FakeProvider):
    requested_days: list[int] = []
    unit_calls = 0

    async def units(self, provider_id: str):
        self.unit_calls += 1
        return [
            ProviderUnit(
                provider_id=f"{provider_id}:upcoming",
                title="Future episode",
                unit_type="episode",
                number=3,
                release_at=datetime.now(UTC) + timedelta(days=5),
                progress_total=1,
                progress_measure="episode",
            )
        ]

    async def upcoming(self, provider_id: str, *, days: int, units=None):
        self.requested_days.append(days)
        source_units = units if units is not None else await self.units(provider_id)
        return [
            unit
            for unit in source_units
            if unit.release_at
            and datetime.now(UTC)
            <= unit.release_at
            <= datetime.now(UTC) + timedelta(days=days)
        ]


class UpcomingRegistry:
    provider = UpcomingProvider()

    def by_id(self, provider_id: str, *, kind: str | None = None):
        return self.provider


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


async def test_poll_uses_upcoming_setting_persists_unit_and_dedups_notification(monkeypatch):
    from app.modules.media import sync as media_sync
    from app.modules.system.models import Setting

    registry = UpcomingRegistry()
    registry.provider.requested_days.clear()
    registry.provider.unit_calls = 0
    monkeypatch.setattr(media_sync, "provider_registry", lambda session: _async(registry))
    async with SessionLocal() as session:
        session.add(Setting(key="media.upcoming_days", value=14))
        item = await service.create_item(
            session,
            MediaItemIn(
                source="provider",
                title="Severance",
                kind="show",
                provider="tmdb",
                provider_id="tv:95396",
                monitored=True,
            ),
        )

    source = f"media:tmdb:{item.id}"
    await poll_media_source(source)
    await poll_media_source(source)

    async with SessionLocal() as session:
        assert await session.scalar(
            select(func.count()).select_from(MediaUnit).where(MediaUnit.media_id == item.id)
        ) == 1
        assert await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.dedup_key.like(f"media-release:{item.id}:%"))
        ) == 1
    assert registry.provider.requested_days == [14, 14]
    assert registry.provider.unit_calls == 2


async def test_existing_unit_notifies_once_when_it_enters_upcoming_window(monkeypatch):
    from app.modules.media import sync as media_sync
    from app.modules.system.models import Setting

    class FarFutureProvider(UpcomingProvider):
        async def units(self, provider_id: str):
            self.unit_calls += 1
            return [
                ProviderUnit(
                    provider_id=f"{provider_id}:far",
                    title="Far future episode",
                    unit_type="episode",
                    number=9,
                    release_at=datetime.now(UTC) + timedelta(days=60),
                )
            ]

    provider = FarFutureProvider()

    class Registry:
        def by_id(self, provider_id: str, *, kind: str | None = None):
            return provider

    monkeypatch.setattr(media_sync, "provider_registry", lambda session: _async(Registry()))
    async with SessionLocal() as session:
        session.add(Setting(key="media.upcoming_days", value=30))
        item = await service.create_item(
            session,
            MediaItemIn(
                source="provider",
                title="Long wait",
                kind="show",
                provider="tmdb",
                provider_id="tv:60",
                monitored=True,
            ),
        )

    source = f"media:tmdb:{item.id}"
    await poll_media_source(source)
    async with SessionLocal() as session:
        assert await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.dedup_key.like(f"media-release:{item.id}:%"))
        ) == 0
        setting = await session.get(Setting, "media.upcoming_days")
        setting.value = 90
        await session.commit()

    await poll_media_source(source)
    await poll_media_source(source)
    async with SessionLocal() as session:
        assert await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.dedup_key.like(f"media-release:{item.id}:%"))
        ) == 1


async def test_automatic_due_selection_is_per_item(monkeypatch):
    from app.modules.media import sync as media_sync

    async with SessionLocal() as session:
        due = await service.create_item(
            session,
            MediaItemIn(
                source="provider",
                title="Due",
                kind="show",
                provider="tmdb",
                provider_id="tv:1",
                monitored=True,
            ),
        )
        fresh = await service.create_item(
            session,
            MediaItemIn(
                source="provider",
                title="Fresh",
                kind="show",
                provider="tmdb",
                provider_id="tv:2",
                monitored=True,
            ),
        )
        due_row = await session.get(MediaItem, due.id)
        fresh_row = await session.get(MediaItem, fresh.id)
        due_row.last_synced_at = datetime.now(UTC) - timedelta(days=2)
        fresh_row.last_synced_at = datetime.now(UTC)
        await session.commit()

    called: list[str] = []

    async def fake_poll(source_id: str, *, batch_id=None):
        called.append(source_id)
        return 0

    monkeypatch.setattr(media_sync, "poll_media_source", fake_poll)
    await poll_media_sources()
    assert called == [f"media:tmdb:{due.id}"]


async def test_provider_batch_finishes_empty_when_items_disappear():
    async with SessionLocal() as session:
        batch, _ = await create_or_extend_batch(
            session, ["media:tmdb"], scope="media"
        )
        batch.status = "running"
        batch_id = batch.id
        await session.commit()

    assert await poll_media_source("media:tmdb", batch_id=batch_id) == 0
    async with SessionLocal() as session:
        status = await current_status(session, scope="media")
        runs = list(
            (
                await session.execute(
                    select(SourceRun).where(SourceRun.batch_id == batch_id)
                )
            ).scalars()
        )
    assert status["active"] is None
    assert status["last_completed"]["id"] == str(batch_id)
    assert [run.status for run in runs] == ["empty"]


async def test_snapshot_unit_and_release_event_roll_back_together(monkeypatch):
    from app.modules.media import sync as media_sync

    monkeypatch.setattr(media_sync, "provider_registry", lambda session: _async(FakeRegistry()))
    async with SessionLocal() as session:
        item = await service.create_item(
            session,
            MediaItemIn(
                source="provider",
                title="Atomic",
                kind="show",
                provider="tmdb",
                provider_id="tv:9",
                monitored=True,
            ),
        )

    original_log_event = media_sync.log_event

    async def fail_release_event(session, *, verb, **kwargs):
        if verb == "media.release_discovered":
            raise RuntimeError("crash between unit and event")
        return await original_log_event(session, verb=verb, **kwargs)

    monkeypatch.setattr(media_sync, "log_event", fail_release_event)
    await poll_media_source(f"media:tmdb:{item.id}")

    async with SessionLocal() as session:
        assert await session.scalar(
            select(func.count()).select_from(MediaUnit).where(MediaUnit.media_id == item.id)
        ) == 0
        item_row = await session.get(MediaItem, item.id)
        entity = await session.get(Entity, item.id)
        assert item_row.last_synced_at is None
        assert entity.title == "Atomic"


async def test_sync_keeps_user_notes_and_review_in_search_text(monkeypatch):
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
                notes="kullanici notu",
                review="inceleme metni",
                meta={"language": "tr"},
            ),
        )

    assert await poll_media_source(f"media:tmdb:{item.id}") == 1

    async with SessionLocal() as session:
        entity = await session.get(Entity, item.id)
        # Saglayici ozeti eklenir ama kullanicinin alanlari SILINMEZ.
        assert "Work is mysterious." in entity.search_text
        assert "kullanici notu" in entity.search_text
        assert "inceleme metni" in entity.search_text
        assert "language" in entity.search_text
        page = await service.list_items(session, q="kullanici notu")
        assert [row.id for row in page.items] == [item.id]


async def test_item_sync_state_prefers_item_run_and_falls_back_to_provider(monkeypatch):
    from app.modules.media import sync as media_sync

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

    async with SessionLocal() as session:
        assert await media_sync.item_sync_state(session, item.id) is None

    async with SessionLocal() as session:
        session.add(
            SourceRun(
                source="media:tmdb",
                status="empty",
                items_found=0,
                started_at=datetime(2026, 1, 1, tzinfo=UTC),
                finished_at=datetime(2026, 1, 1, 0, 5, tzinfo=UTC),
            )
        )
        await session.commit()
    async with SessionLocal() as session:
        state = await media_sync.item_sync_state(session, item.id)
    assert state is not None
    assert (state.status, state.items_found) == ("empty", 0)
    assert state.last_run_at == datetime(2026, 1, 1, 0, 5, tzinfo=UTC)

    async with SessionLocal() as session:
        session.add(
            SourceRun(
                source=f"media:tmdb:{item.id}",
                status="ok",
                items_found=3,
                started_at=datetime(2026, 1, 2, tzinfo=UTC),
                finished_at=datetime(2026, 1, 2, 0, 5, tzinfo=UTC),
            )
        )
        await session.commit()
    async with SessionLocal() as session:
        state = await media_sync.item_sync_state(session, item.id)
        detail = await service.get_detail(session, item.id)
    assert (state.status, state.items_found, state.last_error) == ("ok", 3, None)
    # Detay ucu da ayni durumu tasir.
    assert detail.sync is not None
    assert detail.sync.status == "ok"

    async with SessionLocal() as session:
        session.add(
            SourceRun(
                source=f"media:tmdb:{item.id}",
                status="error",
                error="boom",
                started_at=datetime(2026, 1, 3, tzinfo=UTC),
                finished_at=datetime(2026, 1, 3, tzinfo=UTC),
            )
        )
        await session.commit()
    async with SessionLocal() as session:
        state = await media_sync.item_sync_state(session, item.id)
    assert (state.status, state.last_error) == ("error", "boom")


class StatusRegistry:
    """provider_statuses icin sabit registry: ayar gerektirmeyen hazir provider."""

    def provider_groups(self):
        return {"tmdb": [("movie", FakeProvider()), ("show", FakeProvider())]}

    def by_id(self, provider_id: str, *, kind: str | None = None):
        return FakeProvider() if provider_id == "tmdb" else None


async def _provider_state(status: str, **fields) -> str:
    from app.modules.media import sync as media_sync

    async with SessionLocal() as session:
        session.add(
            SourceRun(
                source="media:tmdb",
                status=status,
                started_at=datetime.now(UTC),
                **fields,
            )
        )
        await session.commit()
    async with SessionLocal() as session:
        rows = await media_sync.provider_statuses(session)
    return next(row for row in rows if row["id"] == "tmdb")["state"]


async def test_provider_statuses_reports_run_state(monkeypatch):
    from app.modules.media import sync as media_sync

    monkeypatch.setattr(
        media_sync, "provider_registry", lambda session: _async(StatusRegistry())
    )
    async with SessionLocal() as session:
        rows = await media_sync.provider_statuses(session)
    tmdb = next(row for row in rows if row["id"] == "tmdb")
    assert tmdb["ready"] is True
    assert tmdb["state"] == "never_run"

    assert await _provider_state("running") == "running"
    assert await _provider_state("ok", items_found=4) == "ok"
    assert await _provider_state("empty") == "empty"
    assert await _provider_state("error", error="boom") == "error"


async def test_provider_statuses_marks_missing_settings_over_stale_run():
    from app.modules.media import sync as media_sync

    async with SessionLocal() as session:
        session.add(
            SourceRun(
                source="media:tmdb",
                status="ok",
                started_at=datetime.now(UTC),
            )
        )
        await session.commit()
    async with SessionLocal() as session:
        rows = await media_sync.provider_statuses(session)
    tmdb = next(row for row in rows if row["id"] == "tmdb")
    # Ayar yokken eski "ok" kosusu saglayiciyi hazir gostermez.
    assert tmdb["ready"] is False
    assert tmdb["state"] == "missing_settings"
    assert tmdb["missing_settings"] == ["media.tmdb_key"]
    assert tmdb["last_status"] == "ok"


async def test_bulk_queue_uses_per_item_source_ids():
    from app.modules.media import sync as media_sync
    from app.modules.system.models import Setting

    async with SessionLocal() as session:
        session.add(Setting(key="media.tmdb_key", value="test-key"))
        await session.commit()
    async with SessionLocal() as session:
        first = await service.create_item(
            session,
            MediaItemIn(
                source="provider",
                title="First",
                kind="movie",
                provider="tmdb",
                provider_id="movie:1",
                monitored=True,
            ),
        )
        second = await service.create_item(
            session,
            MediaItemIn(
                source="provider",
                title="Second",
                kind="movie",
                provider="tmdb",
                provider_id="movie:2",
                monitored=True,
            ),
        )

    async with SessionLocal() as session:
        batch = await media_sync.queue_sync(session)
    assert batch is not None
    assert set(batch["source_ids"]) == {
        f"media:tmdb:{first.id}",
        f"media:tmdb:{second.id}",
    }
    assert batch["total_sources"] == 2


async def _async(value):
    return value
