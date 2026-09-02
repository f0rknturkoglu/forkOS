"""RSS tam-metin (fulltext) ozelligi testleri.

- extract_full_text: readability cikarimi (saf, DB yok).
- /rss/items/{id}/fulltext ucu: cache'ten doner / talebe bagli fetch edip
  kalicilastirir; eszamanli cift fetch null gorur. Fetch monkeypatch ile
  sabitlenir -- gercek aga cikilmaz.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.entity import create_entity
from app.db import SessionLocal
from app.main import app
from app.modules.rss import service
from app.modules.rss.models import Feed, FeedItem
from app.modules.rss.service import extract_full_text

ARTICLE_HTML = """
<html><head><title>Deneme</title></head><body>
<nav><a href="/">Ana sayfa</a></nav>
<header>Site basligi ve logosu</header>
<article>
  <h1>Makale basligi</h1>
  <p>Ilk paragraf. Bu paragraf makalenin gercek icerigidir; uzun ve anlamli
  bir metin tasir ki okunmasi gereken kisim tam olarak burasidir.</p>
  <script>alert("xss")</script>
  <p>Ikinci paragraf da ayni sekilde gercek icerik barindirir ve en az ilki
  kadar okunmasi gereken anlamli bir anlatim sunar.</p>
  <img src="https://cdn.example.com/foto.png" alt="foto">
  <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7">
  <footer>Alt bilgi metni</footer>
</article>
<aside>Reklam kutusu</aside>
</body></html>
"""

DENSITY_HTML = """
<html><body>
<div id="az">
  <p>Kisa bir paragraf.</p>
  <p>Bir paragraf daha.</p>
</div>
<div id="cok">
  <p>Birinci uzun icerik paragrafi -- cok fazla anlamli metin icerir ve
  paragraf yogunlugu skorlamasinda agirlikli olmasi gereken metindir.</p>
  <p>Ikinci uzun icerik paragrafi -- yine anlamli ve uzun bir anlatim sunar,
  kesinlikle korunmasi gereken asil govde metnidir.</p>
  <p>Ucuncu uzun icerik paragrafi -- paragraf yogunlugu karsilastirmasinda bu
  divin secilmesini saglayan son uzun govde paragrafidir.</p>
</div>
</body></html>
"""

SHORT_HTML = "<html><body><article><p>Kisa metin</p></article></body></html>"


# ── Extraction unit testleri (DB yok) ─────────────────────────────────────

@pytest.mark.no_database
def test_extract_article_readability():
    result = extract_full_text(ARTICLE_HTML)

    assert result is not None
    assert "<nav" not in result
    assert "<script" not in result
    assert "<aside" not in result
    assert "<header" not in result
    assert "<footer" not in result
    assert "Ilk paragraf" in result
    assert "Ikinci paragraf" in result
    assert "<p>" in result
    assert '<img src="https://cdn.example.com/foto.png">' in result
    assert "data:image" not in result       # lazy-load placeholder'i yok sayilir
    assert "alert" not in result


@pytest.mark.no_database
def test_extract_prefers_denser_paragraph_section():
    result = extract_full_text(DENSITY_HTML)

    assert result is not None
    assert "Birinci uzun icerik paragrafi" in result
    assert "Kisa bir paragraf" not in result


@pytest.mark.no_database
def test_extract_short_text_returns_none():
    assert extract_full_text(SHORT_HTML) is None
    assert extract_full_text("<html><body><div>icerik yok</div></body></html>") is None


# ── Endpoint testleri ──────────────────────────────────────────────────────

@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


async def _seed_item(*, full_text: str | None = None,
                     url: str | None = "https://example.com/yazi") -> str:
    async with SessionLocal() as session:
        feed_entity = await create_entity(session, type=Feed.ENTITY_TYPE, title="Test Feed")
        feed = Feed(id=feed_entity.id, url="https://example.com/feed.xml")
        session.add(feed)
        await session.flush()
        item_entity = await create_entity(
            session, type=FeedItem.ENTITY_TYPE, title="Makale", search_text="ozet metin",
        )
        item = FeedItem(id=item_entity.id, feed_id=feed.id, guid="g-1",
                        url=url, summary="Ozet", full_text=full_text)
        session.add(item)
        await session.commit()
        return str(item.id)


async def _stored_full_text(item_id: str) -> str | None:
    async with SessionLocal() as session:
        item = await session.get(FeedItem, uuid.UUID(item_id))
        return item.full_text if item else None


async def test_fulltext_returns_cached_without_fetch(client: AsyncClient, monkeypatch) -> None:
    item_id = await _seed_item(full_text="<p>Hazir tam metin</p>")

    async def boom(*args, **kwargs):       # cagrilirsa test patlar
        raise AssertionError("cache doluyken fetch cagrilmamali")

    monkeypatch.setattr(service, "fetch_full_text", boom)
    response = await client.get(f"/api/rss/items/{item_id}/fulltext")

    assert response.status_code == 200
    assert response.json() == {"full_text": "<p>Hazir tam metin</p>"}
    assert await _stored_full_text(item_id) == "<p>Hazir tam metin</p>"


async def test_fulltext_fetches_and_persists(client: AsyncClient, monkeypatch) -> None:
    item_id = await _seed_item()
    calls = {"n": 0}

    async def fake_fetch(session, item):
        calls["n"] += 1
        return "<p>Fetch edilen tam metin</p>"

    monkeypatch.setattr(service, "fetch_full_text", fake_fetch)
    response = await client.get(f"/api/rss/items/{item_id}/fulltext")

    assert response.status_code == 200
    assert response.json() == {"full_text": "<p>Fetch edilen tam metin</p>"}
    assert calls["n"] == 1
    assert await _stored_full_text(item_id) == "<p>Fetch edilen tam metin</p>"


async def test_fulltext_null_when_fetch_fails(client: AsyncClient, monkeypatch) -> None:
    item_id = await _seed_item()

    async def failing_fetch(session, item):
        return None

    monkeypatch.setattr(service, "fetch_full_text", failing_fetch)
    response = await client.get(f"/api/rss/items/{item_id}/fulltext")

    assert response.status_code == 200
    assert response.json() == {"full_text": None}
    assert await _stored_full_text(item_id) is None


async def test_fulltext_concurrent_fetch_is_skipped(client: AsyncClient, monkeypatch) -> None:
    item_id = await _seed_item()
    service._fetching.add(str(item_id))
    try:
        async def boom(*args, **kwargs):
            raise AssertionError("kilitliyken fetch baslamamali")

        monkeypatch.setattr(service, "fetch_full_text", boom)
        response = await client.get(f"/api/rss/items/{item_id}/fulltext")

        assert response.status_code == 200
        assert response.json() == {"full_text": None}
    finally:
        service._fetching.discard(str(item_id))


async def test_fulltext_404_for_missing_item(client: AsyncClient) -> None:
    response = await client.get(f"/api/rss/items/{uuid.uuid4()}/fulltext")
    assert response.status_code == 404
