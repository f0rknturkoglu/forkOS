"""Kaynak teshis yuzeyleri: `retry_at` + hata metni sizinti regresyonu.

Kapsam (uc yuzey ayni kaynagi anlatir):
- `GET /api/sources/catalog`   -> devre durumu + `retry_at`
- `GET /api/sources/coverage`  -> kapsam matrisi + `retry_at` + temiz `last_error`
- `GET /api/sources/health`    -> kosum ozeti (response model alanlari DUSURMEMELI)
- `GET /api/sources/runs`      -> ham kosum listesi (temiz `error`)

`retry_at` yalnizca devre ACIKKEN doludur ve degeri `runs.CIRCUIT_COOLDOWN`
sabitinden turer; test sabiti okur, sayiyi elle yazmaz.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core import runs as run_svc
from app.core.source_sync import create_or_extend_batch
from app.db import SessionLocal, engine
from app.main import app
from app.modules.rss import service as rss_service
from app.modules.rss.schemas import FeedIn
from app.sources.rss_source import EMPTY, ERROR, FetchResult

#: Katalogda GERCEK bir kaynak: coverage/catalog satirlari katalogdan uretilir,
#: uydurma bir id satir uretmez.
SOURCE = "osym"

#: Sir tasiyan ham hata metni: URL userinfo'su + sorgu parametresi token'i.
LEAKY = "ClientError: https://fork:sup3rs3cret@proxy.local:8080/x?access_token=abc123XYZ"
SECRETS = ("sup3rs3cret", "abc123XYZ")


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _rows(client: AsyncClient, path: str, *, params: dict | None = None) -> list[dict]:
    response = await client.get(path, params=params)
    assert response.status_code == 200, response.text
    return response.json()


async def _by_key(client: AsyncClient, path: str, key: str) -> dict[str, dict]:
    return {row[key]: row for row in await _rows(client, path)}


async def _insert_run(
    *, status: str, error: str | None, finished_at: datetime, source: str = SOURCE
) -> None:
    """Kolonlari DOGRUDAN yazar: `finish_run` temizledigi icin onu kullanmak
    (a) ham kolonu, (b) baska yazarlari taklit etmez."""
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "insert into source_run (source, status, items_found, error, started_at, finished_at) "
                "values (:source, :status, 0, :error, :at, :at)"
            ),
            {"source": source, "status": status, "error": error, "at": finished_at},
        )




def _assert_masked(message: str | None) -> None:
    assert message, "hata metni bos olmamali"
    assert "fork:***@proxy.local:8080" in message
    assert "access_token=***" in message
    for secret in SECRETS:
        assert secret not in message


def _assert_no_secret(text: str | None) -> None:
    assert text, "metin bos olmamali"
    for secret in SECRETS:
        assert secret not in text


#: Sir tasiyan ozel feed URL'i: userinfo + sorgu parametresi token'i.
LEAKY_FEED_URL = "https://fork:sup3rs3cret@proxy.local:8080/feed.xml?access_token=abc123XYZ"


async def _add_feed(url: str) -> uuid.UUID:
    """Feed'i servis uzerinden ekler (probe KAPALI: dis aga cikilmaz)."""
    async with SessionLocal() as session:
        feed, created = await rss_service.add_feed(
            session, FeedIn(url=f"https://example.com/{uuid.uuid4()}.xml", title="Teshis feed"), probe=False
        )
        # Eski kayıtlar yeni URL doğrulamasından önce oluşturulmuş olabilir.
        # Teşhis testinin amacı bu kalıcı eski URL'lerin sırlarını maskelemek.
        feed.url = url
        await session.commit()
        assert created
        return feed.id


def _moment(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def test_retry_at_is_present_and_null_while_circuit_is_closed(client: AsyncClient):
    async with SessionLocal() as session:
        run = await run_svc.start_run(session, SOURCE)
        await run_svc.finish_run(session, run, status=run_svc.OK, items_found=4)
        await session.commit()

    catalog = await _by_key(client, "/api/sources/catalog", "id")
    coverage = await _by_key(client, "/api/sources/coverage", "source")
    health = await _by_key(client, "/api/sources/health", "source")

    for row in (catalog[SOURCE], coverage[SOURCE], health[SOURCE]):
        assert row["retry_at"] is None
        assert row["circuit_open"] is False


async def test_retry_at_follows_the_cooldown_constant_when_circuit_is_open(client: AsyncClient):
    last_error_at = datetime.now(UTC) - timedelta(minutes=1)
    for _ in range(run_svc.CIRCUIT_FAILURE_THRESHOLD):
        await _insert_run(status="error", error=None, finished_at=last_error_at)
    expected = last_error_at + run_svc.CIRCUIT_COOLDOWN
    assert expected > datetime.now(UTC)

    catalog = await _by_key(client, "/api/sources/catalog", "id")
    coverage = await _by_key(client, "/api/sources/coverage", "source")
    health = await _by_key(client, "/api/sources/health", "source")

    row = catalog[SOURCE]
    assert row["circuit_open"] is True
    assert row["consecutive_failures"] == run_svc.CIRCUIT_FAILURE_THRESHOLD
    assert _moment(row["retry_at"]) == expected
    assert _moment(coverage[SOURCE]["retry_at"]) == expected
    assert _moment(health[SOURCE]["retry_at"]) == expected
    # Devre acikken bilinmeyen bir "saglikli" durum gosterilmez: retry_at gelecekte.
    assert _moment(row["retry_at"]) > datetime.now(UTC)


async def test_error_text_written_by_finish_run_is_sanitized_on_every_surface(client: AsyncClient):
    async with SessionLocal() as session:
        run = await run_svc.start_run(session, SOURCE)
        await run_svc.finish_run(session, run, status=run_svc.ERROR, error=LEAKY)
        await session.commit()

    coverage = await _by_key(client, "/api/sources/coverage", "source")
    health = await _by_key(client, "/api/sources/health", "source")
    runs = [
        row
        for row in await _rows(client, "/api/sources/runs")
        if row["source"] == SOURCE
    ]

    assert runs, "kosum kaydi /sources/runs icinde gorunmeli"
    for message in (coverage[SOURCE]["last_error"], health[SOURCE]["error"], runs[0]["error"]):
        assert message, "hata metni bos olmamali"
        assert "fork:***@proxy.local:8080" in message
        assert "access_token=***" in message
        for secret in SECRETS:
            assert secret not in message


async def test_raw_column_written_by_another_path_is_masked_on_read(client: AsyncClient):
    """`source_run.error` kolonuna ham metin yazan baska yollar var (media
    senkronu ham istisna metnini yazar, eski satirlar da temizlikten once
    uretilmis olabilir). API yuzeyleri okuma aninda temizlemeli."""
    await _insert_run(status="error", error=LEAKY, finished_at=datetime.now(UTC))

    coverage = await _by_key(client, "/api/sources/coverage", "source")
    health = await _by_key(client, "/api/sources/health", "source")
    runs = [
        row
        for row in await _rows(client, "/api/sources/runs")
        if row["source"] == SOURCE
    ]

    assert runs
    for message in (coverage[SOURCE]["last_error"], health[SOURCE]["error"], runs[0]["error"]):
        assert message
        for secret in SECRETS:
            assert secret not in message


async def test_sources_sync_masks_error_written_to_the_column(client: AsyncClient):
    """`/sources/sync` satir bazli `error` alanini da temizleyici gecirmeli."""
    async with SessionLocal() as session:
        batch, _ = await create_or_extend_batch(session, [SOURCE])
        await session.commit()
        batch_id = batch.id

    async with engine.begin() as connection:
        await connection.execute(
            text(
                "insert into source_run "
                "(source, status, items_found, error, batch_id, started_at, finished_at) "
                "values (:source, 'error', 0, :error, :batch, now(), now())"
            ),
            {"source": SOURCE, "error": LEAKY, "batch": batch_id},
        )

    body = (await client.get("/api/sources/sync", params={"scope": "opportunity"})).json()
    row = next(item for item in body["sources"] if item["source"] == SOURCE)

    assert row["status"] == "error"
    _assert_masked(row["error"])








async def test_catalog_carries_no_error_text(client: AsyncClient):
    """/sources/catalog kosum gecmisi tasimaz: hata metni alani HIC olmamali."""
    catalog = await _rows(client, "/api/sources/catalog")

    assert catalog
    for row in catalog:
        assert [key for key in row if "error" in key] == []


async def test_rss_feed_failure_events_mask_error_and_feed_url(client: AsyncClient):
    """`/activity` (rss.feed_failed / rss.feed_disabled) ham metin ya da ham
    feed URL'i tasimaz: ozel feed URL'i `?token=` / `user:pass@` icerebilir."""
    feed_id = await _add_feed(LEAKY_FEED_URL)

    async with SessionLocal() as session:
        feed = await session.get(rss_service.Feed, feed_id)
        for _ in range(rss_service.MAX_ERRORS_BEFORE_DISABLE):
            await rss_service.record_fetch(
                session, feed, FetchResult(status=ERROR, error=LEAKY)
            )
        await session.commit()

    events = await _rows(client, "/api/activity", params={"limit": 200})
    failed = next(e for e in events if e["verb"] == "rss.feed_failed")
    disabled = next(e for e in events if e["verb"] == "rss.feed_disabled")

    _assert_masked(failed["payload"]["error"])
    for payload in (failed["payload"], disabled["payload"]):
        _assert_no_secret(payload["url"])
        assert payload["url"].endswith("access_token=***")
    _assert_no_secret(disabled["payload"]["message"])


async def test_rss_stalled_notification_masks_the_feed_url(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """Duraksama bildiriminin etiketi feed URL'ini tasir: temizlenmis olmali."""
    feed_id = await _add_feed(f"{LEAKY_FEED_URL}&probe=stalled")
    now = datetime.now(UTC)
    for index in range(2):
        await _insert_run(
            source=f"rss:{feed_id}",
            status="empty",
            error=None,
            finished_at=now - timedelta(minutes=10 * (index + 1)),
        )

    class _EmptySource:
        async def fetch_result(self) -> FetchResult:
            return FetchResult(status=EMPTY)

    monkeypatch.setattr(rss_service, "source_for", lambda _feed: _EmptySource())
    async with SessionLocal() as session:
        feed = await session.get(rss_service.Feed, feed_id)
        status, added = await rss_service.poll_feed(session, feed)

    assert (status, added) == (EMPTY, 0)
    notifications = await _rows(client, "/api/notifications")
    stalled = next(n for n in notifications if n["kind"] == "source_stalled")

    _assert_no_secret(f"{stalled['title']} {stalled['body']}")
    assert "access_token=***" in stalled["title"]




@pytest.mark.no_database
def test_error_message_of_masks_the_raw_column_value():
    """Okuma sinirindaki temizleyici: ham metin asla disari cikmaz."""
    masked = run_svc.error_message_of(SimpleNamespace(error=LEAKY))

    assert masked and "fork:***@proxy.local:8080" in masked
    for secret in SECRETS:
        assert secret not in masked
    assert run_svc.error_message_of(SimpleNamespace(error=None)) is None


@pytest.mark.no_database
def test_sanitize_error_is_idempotent():
    """Okuma aninda tekrar temizlik guvenli: ayni metin ikinci kez degismez."""
    once = run_svc.sanitize_error(LEAKY)

    assert run_svc.sanitize_error(once) == once
    for secret in SECRETS:
        assert secret not in once
