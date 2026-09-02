from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.sources.announcements import AnnouncementSource, YokAnnouncementSource
from app.sources.forkjob_core.models import Company, DateSource, WorkMode
from app.sources.forkjob_core.scrapers.bulldogjob import _QUERY, BulldogjobScraper
from app.sources.forkjob_core.scrapers.kariyernet import KariyerNetScraper
from app.sources.forkjob_core.scrapers.schemaorg import place
from app.sources.forkjob_core.sources.adapters import GreenhouseAdapter

pytestmark = pytest.mark.no_database
FIXTURES = Path(__file__).parent / "fixtures"


def test_native_announcement_fixture_is_filtered_and_deduplicated():
    source = AnnouncementSource(
        "osym",
        "https://www.osym.gov.tr/Duyurular/Index",
        ("ales",),
        "exam",
    )

    items = source.parse_html(
        (FIXTURES / "announcement.html").read_text(),
        base_url="https://www.osym.gov.tr/Duyurular/Index",
    )

    assert len(items) == 1
    assert items[0].title == "26 Ağustos 2026 Aynı ALES duyurusu"
    assert items[0].url == "https://www.osym.gov.tr/duyurular/2026-ales-basvurulari.html"
    assert items[0].extra == {"organization": "OSYM", "kind": "exam"}
    assert items[0].published_at.isoformat() == "2026-08-26T00:00:00+00:00"


def test_yok_fixture_reads_live_card_shape_and_date():
    source = YokAnnouncementSource()
    items = source.parse_html(
        (FIXTURES / "yok_announcements.html").read_text(),
        base_url="https://www.yok.gov.tr/tr/announcements",
        year=2026,
    )
    assert len(items) == 1
    assert items[0].title == "Yüksek Lisans Burs Başvurusu"
    assert items[0].published_at.isoformat() == "2026-08-24T00:00:00+00:00"
    assert items[0].extra["organization"] == "YÖK"


def test_bulldog_query_matches_current_public_schema():
    assert "salaryFrom" not in _QUERY
    assert "salaryTo" not in _QUERY
    assert "salaryCurrency" not in _QUERY
    jobs = BulldogjobScraper().parse(
        {
            "nodes": [
                {
                    "id": "42-backend",
                    "position": "Backend Engineer",
                    "city": "Warsaw",
                    "publishedAt": "2026-08-28T10:00:00Z",
                    "remote": True,
                    "contractB2b": True,
                    "experienceLevel": "regular",
                }
            ]
        }
    )
    assert jobs[0].title == "Backend Engineer"
    assert jobs[0].salary is None


def test_greenhouse_fixture_normalizes_an_ats_job():
    payload = json.loads((FIXTURES / "greenhouse.json").read_text())
    adapter = GreenhouseAdapter(Company(name="Acme", ats="greenhouse", token="acme"))

    jobs = adapter.parse(payload)

    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_id == "42"
    assert job.title == "Backend Engineer"
    assert job.country == "ES"
    assert job.department == "Engineering"
    assert job.date_source is DateSource.EMPLOYER
    assert "Seniority: Associate" in (job.description or "")


def test_schemaorg_place_resolves_country_names_not_just_prefixes():
    """The old code took the first two letters ("Bahrain" -> "BA")."""
    assert place({"address": {"addressCountry": "Bahrain"}})[1] == "BH"
    assert place({"address": {"addressCountry": "ES"}})[1] == "ES"


def test_kariyer_fixture_uses_stable_card_attributes():
    jobs = KariyerNetScraper(keywords=("backend",), max_pages=1).parse(
        (FIXTURES / "kariyer.html").read_text()
    )

    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_id == "4522282"
    assert job.company == "Acme Teknoloji"
    assert job.city == "İstanbul"
    assert job.country == "TR"
    assert job.work_mode is WorkMode.HYBRID
    assert job.date_source is DateSource.UPDATED
