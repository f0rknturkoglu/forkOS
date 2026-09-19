"""Depolama gorunurlugu ve esik uyarilari (Phase 20/21).

Teshis ekrani bir SORUNU ANLATMAK icin var: eksik yetki veya beklenmedik
buyume yuzunden cokmemeli, hicbir seyi de otomatik silmemeli.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.system import storage_report


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_storage_report_covers_database_and_files(client: AsyncClient) -> None:
    response = await client.get("/api/system/storage")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["database"]["total_bytes"] > 0
    assert set(body["database"]["rows"]) == set(storage_report.COUNTED_TABLES)
    assert body["database"]["tables"], "en buyuk tablolar listesi bos olmamali"
    # WAL yetkisi olmayabilir; alan YINE DE bulunur (None olabilir).
    assert "wal" in body["database"]
    assert set(body["files"]) == {
        "documents",
        "attachments",
        "media_artwork",
        "scraper_cache",
        "backups",
    }
    assert "warnings" in body


@pytest.mark.no_database
def test_warnings_only_fire_above_the_limit() -> None:
    """Esik altinda uyari YOK; asilinca tek satir."""
    calm = {
        "files": {key: 1 for key in storage_report.WARN_LIMITS if key != "source_run_rows"},
        "database": {"rows": {"source_run": storage_report.WARN_LIMITS["source_run_rows"]}},
    }
    assert storage_report.warnings(calm) == []

    loud = {
        "files": {
            "media_artwork": storage_report.WARN_LIMITS["media_artwork"] + 1,
            "backups": 1,
        },
        "database": {"rows": {"source_run": 1}},
    }
    alerts = storage_report.warnings(loud)
    assert [alert["key"] for alert in alerts] == ["media_artwork"]
    assert alerts[0]["limit"] == storage_report.WARN_LIMITS["media_artwork"]


@pytest.mark.no_database
def test_warnings_tolerate_a_partial_report() -> None:
    """Eksik yanit cokertmemeli (teshis ekrani savunmali okur)."""
    assert storage_report.warnings({}) == []


@pytest.mark.no_database
def test_directory_size_counts_files_not_links(tmp_path) -> None:
    (tmp_path / "a.bin").write_bytes(b"12345")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.bin").write_bytes(b"123")

    assert storage_report._dir_bytes(tmp_path) == 8
    assert storage_report._dir_bytes(tmp_path / "missing") == 0
