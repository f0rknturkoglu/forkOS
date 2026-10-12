"""Recorded public wire format, bounded fetching and canonical import fixtures."""

import httpx
import pytest
from sqlalchemy import func, select
from test_flashcard import build_apkg

from app.core.models import SourceRun
from app.db import SessionLocal
from app.modules.flashcard import catalog
from app.sources import ankiweb


def v(value):
    out = bytearray()
    while value > 127:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)


def number(key, value):
    return v(key << 3) + v(value)


def blob(key, value):
    value = value.encode() if isinstance(value, str) else value
    return v((key << 3) | 2) + v(len(value)) + value


@pytest.mark.no_database
async def test_public_wire_decoding_and_limit(monkeypatch):
    payload = b"".join(
        blob(1, number(1, i + 1) + blob(2, f"English {i}") + number(3, i) + number(6, 4))
        for i in range(15)
    )

    async def get(path, **kwargs):
        assert path == "/svc/shared/list-decks?search=english+grammar"
        return payload

    monkeypatch.setattr(ankiweb, "public_get", get)
    result = await ankiweb.AnkiWebSource("english grammar").fetch()
    assert len(result.items) == 12 and result.items[0].external_id == "15"
    assert result.telemetry.cap_hit and result.telemetry.items_seen == 15


@pytest.mark.no_database
@pytest.mark.parametrize("payload", [b"\x00", b"\x0a\x09x", b"\x80" * 11, b"\x0f"])
async def test_corrupt_wire_format_is_rejected(payload):
    with pytest.raises(ValueError):
        ankiweb.fields(payload)


@pytest.mark.no_database
async def test_preview_decodes_text_not_html_and_enforces_size(monkeypatch):
    sample = blob(1, blob(1, "Front") + blob(2, "<script>sample</script>"))
    deck = number(1, 1) + blob(4, sample) + blob(5, "public-download-token")
    payload = blob(1, blob(5, "English") + number(7, 128) + blob(10, deck))

    async def get(path, **kwargs):
        assert "sharedId=123" in path
        return payload

    monkeypatch.setattr(ankiweb, "public_get", get)
    preview = await catalog.preview(123)
    assert preview["samples"] == [["<script>sample</script>"]]
    assert "download_key" not in preview
    payload = blob(1, blob(5, "Large") + number(7, 32_000_001) + blob(10, deck))
    with pytest.raises(Exception, match="32 MB"):
        await ankiweb.deck_info(123)


@pytest.mark.no_database
async def test_429_sets_cooldown_and_sends_no_second_request(monkeypatch):
    calls = []

    async def get(client, url, **kwargs):
        calls.append(url)
        return httpx.Response(429, headers={"Retry-After": "10"}, request=httpx.Request("GET", url))

    monkeypatch.setattr(ankiweb, "get_public", get)
    monkeypatch.setattr(ankiweb, "_NOT_BEFORE", 0)
    monkeypatch.setattr(ankiweb.time, "monotonic", lambda: 100)
    for _ in range(2):
        with pytest.raises(httpx.HTTPStatusError):
            await ankiweb.public_get("/svc/shared/list-decks?search=english")
    assert len(calls) == 1


async def test_catalog_records_source_run_caches_and_imports_canonical_cards(monkeypatch):
    async def fetch(self):
        from app.sources.base import FetchOutcome, RawItem, ScrapeTelemetry

        return FetchOutcome(
            items=[
                RawItem(
                    "123",
                    "English",
                    "https://ankiweb.net/shared/info/123",
                    extra={"notes": 1, "likes": 2, "has_media": False},
                )
            ],
            telemetry=ScrapeTelemetry(items_seen=1, items_returned=1),
        )

    async def download(shared_id):
        assert shared_id == 123
        return {"title": "English"}, build_apkg([("Question", "Answer")], "English")

    monkeypatch.setattr(catalog.AnkiWebSource, "fetch", fetch)
    monkeypatch.setattr(catalog, "download_deck", download)
    monkeypatch.setattr(catalog, "_CACHE", {})
    async with SessionLocal() as db:
        assert (await catalog.list_catalog(db, "english"))[0]["id"] == 123
        await catalog.list_catalog(db, "english")
        assert await db.scalar(select(func.count()).select_from(SourceRun)) == 1
        result = await catalog.import_shared(db, 123)
        assert result["added"] == 1
        assert await db.scalar(select(func.count()).select_from(SourceRun)) == 2
        cards = await catalog.service.list_cards(db, result["deck_id"], due=False)
        assert cards[0]["front"] == "Question" and cards[0]["back"] == "Answer"
