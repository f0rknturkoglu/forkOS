"""ScraperHttpClient on-disk onbellegi: TTL, butce, gzip, kosullu istek.

PostgreSQL gerektirmez; her sey gecici dizinde calisir.
"""

from __future__ import annotations

import gzip
import json
import os
import time
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.sources.base import retry_after_seconds
from app.sources.forkjob_core.scrapers.base import (
    CacheMode,
    RobotsPolicy,
    ScraperConfig,
    ScraperHttpClient,
    cache_stats,
    clear_cache,
    prune_cache,
)

pytestmark = pytest.mark.no_database

URL = "https://example.com/jobs"
FORMULA = "%a, %d %b %Y %H:%M:%S GMT"


def _config(tmp_path, **overrides) -> ScraperConfig:
    base = {
        "cache": CacheMode.WRITE,
        "cache_dir": tmp_path,
        "cache_compress": True,
        "robots": RobotsPolicy.IGNORE,
        "max_retries": 1,
        "backoff_base": 0.0,
        "min_interval": 0.0,
        "cache_prune_interval_seconds": 0.0,
    }
    base.update(overrides)
    return ScraperConfig(**base)


class _FakeHttp:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.calls: list[dict] = []

    async def request(self, method: str, url: str, **kwargs):
        self.calls.append(kwargs)
        return self.response

    async def get(self, *args, **kwargs):
        return self.response

    async def aclose(self) -> None:
        pass


def _seed(client: ScraperHttpClient, url: str, *, text: str, headers: dict | None = None) -> None:
    response = httpx.Response(
        200, headers=headers or {}, text=text, request=httpx.Request("GET", url)
    )
    client._save_cache(url, url, response)


def test_default_cache_mode_is_off_and_bounded():
    config = ScraperConfig()
    assert config.cache is CacheMode.OFF
    assert config.cache_max_bytes > 0
    assert config.cache_max_age_seconds > 0


async def test_off_mode_never_writes_to_disk(tmp_path):
    client = ScraperHttpClient(_config(tmp_path, cache=CacheMode.OFF))
    client._client = _FakeHttp(httpx.Response(200, text="body", request=httpx.Request("GET", URL)))

    await client._request("GET", URL)

    assert list(tmp_path.iterdir()) == []


async def test_write_mode_stores_gzip_and_reads_it_back(tmp_path):
    client = ScraperHttpClient(_config(tmp_path))
    _seed(client, URL, text="hello world", headers={"ETag": 'W/"1"'})

    files = list(tmp_path.iterdir())
    assert len(files) == 1
    assert files[0].name.startswith("example.com--")
    raw = files[0].read_bytes()
    assert raw[:2] == b"\x1f\x8b"  # gzip magic
    assert json.loads(gzip.decompress(raw))["text"] == "hello world"

    cached = client._load_cache(URL, URL)
    assert cached is not None and cached["text"] == "hello world"


async def test_expired_entry_is_a_miss_and_is_removed(tmp_path):
    client = ScraperHttpClient(_config(tmp_path, cache_max_age_seconds=10))
    _seed(client, URL, text="stale")
    path = next(tmp_path.iterdir())
    old = time.time() - 3600
    os.utime(path, (old, old))

    assert client._load_cache(URL, URL) is None
    assert not path.exists()


async def test_conditional_request_revalidates_with_etag_and_last_modified(tmp_path):
    client = ScraperHttpClient(_config(tmp_path))
    _seed(
        client,
        URL,
        text="cached body",
        headers={
            "ETag": 'W/"abc"',
            "Last-Modified": datetime(2015, 10, 21, 7, 28, tzinfo=UTC).strftime(FORMULA),
        },
    )
    fake = _FakeHttp(httpx.Response(304, request=httpx.Request("GET", URL)))
    client._client = fake

    response = await client._request("GET", URL)

    assert response.text == "cached body"
    headers = fake.calls[0]["headers"]
    assert headers["If-None-Match"] == 'W/"abc"'
    assert headers["If-Modified-Since"].startswith("Wed, 21 Oct 2015")


def test_prune_evicts_lru_until_under_byte_budget(tmp_path):
    config = _config(tmp_path, cache_max_bytes=1500)
    base = time.time() - 1000
    for index in range(3):
        path = tmp_path / f"example.com--{index}.json.gz"
        path.write_bytes(b"x" * 1000)
        os.utime(path, (base + index, base + index))

    result = prune_cache(config, max_bytes=1500, max_age_seconds=0)

    assert result["removed"] == 2
    assert result["bytes_remaining"] <= 1500
    assert not (tmp_path / "example.com--0.json.gz").exists()  # en eski once
    assert not (tmp_path / "example.com--1.json.gz").exists()
    assert (tmp_path / "example.com--2.json.gz").exists()


def test_prune_removes_entries_past_ttl(tmp_path):
    config = _config(tmp_path)
    fresh = tmp_path / "h--fresh.json.gz"
    stale = tmp_path / "h--stale.json.gz"
    fresh.write_bytes(b"x" * 10)
    stale.write_bytes(b"x" * 10)
    old = time.time() - 7200
    os.utime(stale, (old, old))

    result = prune_cache(config, max_bytes=0, max_age_seconds=3600)

    assert result["removed"] == 1
    assert not stale.exists()
    assert fresh.exists()


def test_cache_stats_reports_size_files_hosts_and_oldest(tmp_path):
    config = _config(tmp_path)
    (tmp_path / "a.example--1.json.gz").write_bytes(b"x" * 100)
    (tmp_path / "a.example--2.json.gz").write_bytes(b"x" * 50)
    (tmp_path / "b.example--3.json.gz").write_bytes(b"x" * 25)
    old = time.time() - 500
    os.utime(tmp_path / "a.example--1.json.gz", (old, old))

    stats = cache_stats(config)

    assert stats["files"] == 3
    assert stats["bytes"] == 175
    assert stats["hosts"]["a.example"] == 150
    assert stats["hosts"]["b.example"] == 25
    assert stats["oldest"] is not None
    assert stats["max_bytes"] == config.cache_max_bytes


def test_clear_cache_removes_every_file(tmp_path):
    config = _config(tmp_path)
    for index in range(3):
        (tmp_path / f"h--{index}.json.gz").write_bytes(b"x" * 10)

    result = clear_cache(config)

    assert result["removed"] == 3
    assert result["bytes_freed"] == 30
    assert list(tmp_path.iterdir()) == []


def test_retry_after_seconds_and_http_date_forms():
    assert retry_after_seconds("120") == 120
    assert retry_after_seconds(None) is None
    assert retry_after_seconds("not-a-date") is None

    when = datetime.now(UTC) + timedelta(seconds=100)
    value = retry_after_seconds(when.strftime(FORMULA))
    assert value is not None and 90 <= value <= 101
