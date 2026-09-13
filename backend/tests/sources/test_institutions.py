from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.sources.institutions import (
    CANONICAL_SOURCE_ID,
    INSTITUTION_SOURCES,
    SPECS,
)

pytestmark = pytest.mark.no_database
FIXTURES = Path(__file__).parent / "fixtures" / "institutions"


def _source(source_id: str):
    return next(source for source in INSTITUTION_SOURCES if source.id == source_id)


def test_every_adapter_has_stable_catalog_metadata():
    assert INSTITUTION_SOURCES
    ids = [source.id for source in INSTITUTION_SOURCES]
    assert len(ids) == len(set(ids))
    assert all(source.id.strip() for source in INSTITUTION_SOURCES)
    assert all(source.interval_minutes > 0 for source in INSTITUTION_SOURCES)
    assert all(
        source.source_class in {"critical", "normal", "slow_optin"}
        for source in INSTITUTION_SOURCES
    )
    assert {source.spec.id for source in INSTITUTION_SOURCES} == {spec.id for spec in SPECS}
    assert CANONICAL_SOURCE_ID == "ylsy"


@pytest.mark.parametrize("source", INSTITUTION_SOURCES, ids=lambda source: source.id)
def test_institution_fixture_yields_parsed_announcement_rows(source):
    body = (FIXTURES / f"{source.id}.html").read_text()

    items = source.parse_listing(body, base_url=source.url)

    assert len(items) == 2
    assert all(source._detail.search(item.url) for item in items)
    for item in items:
        announcement = item.extra["announcement"]
        assert announcement["official"] is source.official
        assert announcement["canonical"] is source.canonical
        assert item.extra["organization"] == source.spec.name
        assert item.extra["verified"] is source.spec.verified

    first = items[0]
    assert first.extra["announcement"]["guide_url"].endswith(".pdf")
    assert first.extra["announcement"]["apply_url"]
    assert first.extra["announcement"]["application_end_at"] == "2026-09-20T14:00:00+00:00"
    assert first.extra["announcement"]["application_start_at"] == "2026-08-31T21:00:00+00:00"


@pytest.mark.parametrize("source", INSTITUTION_SOURCES, ids=lambda source: source.id)
def test_broken_markup_degrades_to_empty_without_raising(source):
    assert source.parse_listing((FIXTURES / "broken.html").read_text(), base_url=source.url) == []
    assert source.parse_listing("", base_url=source.url) == []
    partial = source.parse_listing("<a href=\"/duyurular/2026-burs>başvuru", base_url=source.url)
    assert isinstance(partial, list)


@pytest.mark.parametrize("source", INSTITUTION_SOURCES, ids=lambda source: source.id)
async def test_fetch_raises_on_network_error_so_the_run_is_not_empty(source, monkeypatch):
    """Kurum sitesi erişilemezse koşum `error` olmalı, sessiz `empty` değil.

    Eski davranış (`except -> []`) kurumun yayındaki duyurularını "kaynakta
    yok" gibi gösteriyordu; devre kesici ve hata bildirimi de hiç devreye
    girmiyordu.
    """

    async def offline(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("app.sources.institutions._request_with_retry", offline)

    with pytest.raises(httpx.HTTPError):
        await source.fetch()


@pytest.mark.parametrize("source", INSTITUTION_SOURCES, ids=lambda source: source.id)
async def test_fetch_returns_complete_outcome_for_a_good_listing(source, monkeypatch):
    """Başarılı çekim `partial=False` bir sonuç döndürür (kapsam tam)."""
    body = (FIXTURES / f"{source.id}.html").read_text()

    class _Response:
        text = body
        url = source.url

    async def ok(*args, **kwargs):
        return _Response()

    monkeypatch.setattr("app.sources.institutions._request_with_retry", ok)

    outcome = await source.fetch()

    assert outcome.partial is False
    assert outcome.items


def test_tuseb_embedded_next_data_is_parsed_as_fallback():
    source = _source("tuseb")

    items = source.parse_listing(
        (FIXTURES / "tuseb_next_data.html").read_text(), base_url=source.url
    )

    assert [item.title for item in items] == ["2026 TÜSEB Aziz Sancar Araştırma Bursu Başvuruları"]
    assert items[0].url == "https://www.tuseb.gov.tr/duyurular/2026-aziz-sancar-bursu"
    assert items[0].extra["announcement"]["official"] is True


def test_tuseb_broken_embedded_json_is_ignored():
    source = _source("tuseb")

    assert (
        source.parse_listing((FIXTURES / "tuseb_broken_json.html").read_text(), base_url=source.url)
        == []
    )


def test_aggregator_is_not_official_and_is_slow_optin():
    source = _source("memurlar")
    assert source.official is False
    assert source.canonical is False
    assert source.source_class == "slow_optin"

    items = source.parse_listing((FIXTURES / "memurlar.html").read_text(), base_url=source.url)

    assert items
    assert all(item.extra["announcement"]["official"] is False for item in items)


def test_image_card_listing_falls_back_to_title_attribute():
    source = _source("dsi")
    body = (
        '<html><body><a href="https://www.dsi.gov.tr/Duyuru/Detay/999" '
        'title="2026 Sözleşmeli Personel Alım İlanı"><img src="kapak.jpg" alt=""></a></body></html>'
    )

    items = source.parse_listing(body, base_url=source.url)

    assert [item.title for item in items] == ["2026 Sözleşmeli Personel Alım İlanı"]
