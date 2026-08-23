from __future__ import annotations

import hashlib
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import httpx

MAX_BYTES = 8 * 1024 * 1024
CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class ArtworkError(ValueError):
    pass


def default_asset_dir() -> Path:
    configured = os.getenv("MEDIA_ASSET_DIR")
    if configured:
        return Path(configured)
    if Path("/app").is_dir():
        return Path("/app/data/media")
    return Path(__file__).resolve().parents[3] / "data" / "media"


class ArtworkStore:
    def __init__(
        self,
        root: str | Path | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        max_bytes: int = MAX_BYTES,
    ) -> None:
        self.root = Path(root) if root else default_asset_dir()
        self.client = client
        self.max_bytes = max_bytes

    @asynccontextmanager
    async def _stream(self, url: str):
        if self.client is not None:
            async with self.client.stream("GET", url) as response:
                yield response
            return
        async with (
            httpx.AsyncClient(timeout=20.0) as client,
            client.stream("GET", url) as response,
        ):
            yield response

    async def cache(self, url: str, *, previous: str | None) -> str:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        digest = hashlib.sha256()
        size = 0
        try:
            async with self._stream(url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0]
                extension = CONTENT_TYPES.get(content_type.lower())
                if extension is None:
                    raise ArtworkError("Desteklenmeyen artwork MIME tipi")
                fd, temporary_name = tempfile.mkstemp(
                    prefix=".artwork-", suffix=".tmp", dir=self.root
                )
                os.close(fd)
                temporary = Path(temporary_name)
                with temporary.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > self.max_bytes:
                            raise ArtworkError("Artwork boyut sınırını aşıyor")
                        digest.update(chunk)
                        handle.write(chunk)
            target = self.root / f"{digest.hexdigest()}{extension}"
            temporary.replace(target)
            return target.name
        except (httpx.HTTPError, OSError) as exc:
            raise ArtworkError(str(exc)) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def resolve(self, asset_name: str) -> Path | None:
        if not asset_name or Path(asset_name).name != asset_name:
            return None
        candidate = self.root / asset_name
        try:
            candidate.resolve().relative_to(self.root.resolve())
        except (OSError, ValueError):
            return None
        return candidate if candidate.is_file() else None
