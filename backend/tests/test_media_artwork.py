from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.modules.media.artwork import ArtworkError, ArtworkStore


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
