from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.db import SessionLocal
from app.main import app
from app.modules.media import artwork
from app.modules.media.artwork import ArtworkError, ArtworkStore
from app.modules.media.progress import MediaCommandError

DAY_SECONDS = 24 * 60 * 60


def _age(path: Path, days: float) -> None:
    stamp = time.time() - days * DAY_SECONDS
    os.utime(path, (stamp, stamp))


@pytest.mark.no_database
async def test_artwork_cache_uses_sha256_name_and_atomic_replace(tmp_path: Path):
    body = b"valid-image"

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-type": "image/jpeg"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        store = ArtworkStore(tmp_path, client=client)
        asset_name = await store.cache("https://example.test/cover", previous=None)

    assert asset_name.endswith(".jpg")
    assert (tmp_path / asset_name).read_bytes() == body
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.no_database
@pytest.mark.parametrize(
    ("content_type", "body"),
    [("image/gif", b"gif"), ("image/png", b"x" * 33)],
)
async def test_artwork_rejects_mime_and_size_without_overwriting_previous(
    tmp_path: Path, content_type: str, body: bytes
):
    previous = tmp_path / "working.jpg"
    previous.write_bytes(b"working")

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-type": content_type})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        store = ArtworkStore(tmp_path, client=client, max_bytes=32)
        with pytest.raises(ArtworkError):
            await store.cache("https://example.test/cover", previous="working.jpg")

    assert previous.read_bytes() == b"working"
    assert {path.name for path in tmp_path.iterdir()} == {"working.jpg"}


@pytest.mark.no_database
def test_artwork_resolve_blocks_path_traversal(tmp_path: Path):
    store = ArtworkStore(tmp_path)

    assert store.resolve("../secret") is None
    assert store.resolve("nested/file.jpg") is None
    assert store.resolve("missing.jpg") is None


@pytest.mark.no_database
async def test_artwork_cache_follows_cover_art_redirect(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/front-500":
            return httpx.Response(302, headers={"location": "/image.jpg"})
        return httpx.Response(
            200, content=b"jpeg", headers={"content-type": "image/jpeg"}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        asset = await ArtworkStore(tmp_path, client=client).cache(
            "https://cover.test/front-500", previous=None
        )
    assert (tmp_path / asset).read_bytes() == b"jpeg"


@pytest.mark.no_database
def test_artwork_stats_counts_only_cached_files(tmp_path: Path):
    (tmp_path / "a.jpg").write_bytes(b"12345")
    (tmp_path / "b.png").write_bytes(b"123")
    (tmp_path / ".artwork-partial.tmp").write_bytes(b"ignored")

    assert ArtworkStore(tmp_path).stats() == (2, 8)


@pytest.mark.no_database
def test_artwork_prune_removes_stale_unreferenced_files_only(tmp_path: Path):
    referenced = tmp_path / "referenced.jpg"
    referenced.write_bytes(b"referenced")
    stale = tmp_path / "stale.jpg"
    stale.write_bytes(b"orphan-bytes")
    fresh = tmp_path / "fresh.jpg"
    fresh.write_bytes(b"fresh")
    _age(referenced, 10)
    _age(stale, 10)

    removed, freed = ArtworkStore(tmp_path).prune({"referenced.jpg"})

    assert (removed, freed) == (1, len(b"orphan-bytes"))
    assert referenced.exists()
    assert fresh.exists()
    assert not stale.exists()


@pytest.mark.no_database
def test_artwork_prune_never_deletes_recent_files_to_fit_budget(tmp_path: Path):
    (tmp_path / "fresh.jpg").write_bytes(b"x" * 100)

    assert ArtworkStore(tmp_path).prune(set(), max_total_bytes=1) == (0, 0)
    assert (tmp_path / "fresh.jpg").exists()


@pytest.mark.no_database
def test_artwork_prune_trims_size_budget_oldest_first(tmp_path: Path):
    for index, name in enumerate(("a.jpg", "b.jpg", "c.jpg")):
        path = tmp_path / name
        path.write_bytes(b"x" * 10)
        _age(path, 10 - index)  # a en eski, c en yeni
    # Referansli olduklari icin adim 1 dokunmaz; butce asimi adim 2'yi tetikler.
    keep = {"a.jpg", "b.jpg", "c.jpg"}

    removed, freed = ArtworkStore(tmp_path).prune(keep, max_total_bytes=15)

    assert (removed, freed) == (2, 20)
    assert not (tmp_path / "a.jpg").exists()
    assert not (tmp_path / "b.jpg").exists()
    assert (tmp_path / "c.jpg").exists()


@pytest.mark.no_database
async def test_artwork_stats_reports_configured_directory(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(artwork, "default_asset_dir", lambda: tmp_path)
    (tmp_path / "a.jpg").write_bytes(b"1234")

    stats = await artwork.artwork_stats()

    assert (stats.files, stats.bytes, stats.max_bytes) == (1, 4, artwork.MAX_TOTAL_BYTES)


async def test_prune_artwork_keeps_asset_names_referenced_by_rows(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(artwork, "default_asset_dir", lambda: tmp_path)
    referenced = tmp_path / "referenced.jpg"
    referenced.write_bytes(b"referenced")
    orphan = tmp_path / "orphan.jpg"
    orphan.write_bytes(b"orphan-bytes")
    _age(referenced, 10)
    _age(orphan, 10)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/media",
            json={
                "source": "manual",
                "title": "Kapaklı Kitap",
                "kind": "book",
                "cover_path": "/api/media/assets/referenced.jpg",
            },
        )
    assert created.status_code == 201, created.text

    async with SessionLocal() as session:
        result = await artwork.prune_artwork(session)

    assert (result.removed, result.freed_bytes) == (1, len(b"orphan-bytes"))
    assert referenced.exists()
    assert not orphan.exists()


@pytest.mark.no_database
@pytest.mark.parametrize(
    "url",
    [
        "https://evil.test/poster.jpg",
        "https://image.tmdb.org.evil.test/poster.jpg",
        "ftp://image.tmdb.org/poster.jpg",
        "file:///etc/passwd",
        "not-a-url",
    ],
)
async def test_cache_artwork_rejects_hosts_outside_allowlist(url: str):
    with pytest.raises(MediaCommandError, match="izinli değil"):
        await artwork.cache_artwork(url)


@pytest.mark.no_database
@pytest.mark.parametrize(
    "url",
    [
        "https://image.tmdb.org/t/p/w500/poster.jpg",
        "https://covers.openlibrary.org/b/id/1-L.jpg",
        "https://cdn.myanimelist.net/images/anime/1.jpg",
        "https://s4.anilist.co/file/anilistcdn/media/anime/cover/1.jpg",
        "https://is1-ssl.mzstatic.com/image/thumb/1.jpg",
        "https://ia800000.us.archive.org/view_archive.php?x=1",
        "https://ia601504.us.archive.org/cover.jpg",
        "https://media.rawg.io/media/games/1.jpg",
    ],
)
async def test_cache_artwork_downloads_from_allowed_hosts(tmp_path: Path, monkeypatch, url: str):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"jpeg-bytes", headers={"content-type": "image/jpeg"}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(
            artwork, "ArtworkStore", lambda: ArtworkStore(tmp_path, client=client)
        )
        path = await artwork.cache_artwork(url)

    assert path is not None
    assert path.parent == tmp_path
    assert path.read_bytes() == b"jpeg-bytes"


@pytest.mark.no_database
async def test_cache_artwork_reports_download_failure_without_leaking_url(
    tmp_path: Path, monkeypatch
):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"nope", headers={"content-type": "text/plain"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(
            artwork, "ArtworkStore", lambda: ArtworkStore(tmp_path, client=client)
        )
        with pytest.raises(MediaCommandError, match="indirilemedi"):
            await artwork.cache_artwork("https://image.tmdb.org/secret-token.jpg")
