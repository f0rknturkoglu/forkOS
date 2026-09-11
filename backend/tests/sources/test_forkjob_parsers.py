from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.sources.announcements import (
    AnnouncementSource,
    OsymAnnouncementSource,
    YlsySource,
    YokAnnouncementSource,
    build_ylsy_hierarchy,
    osym_interest_profiles,
    parse_ylsy_preference_layout,
    ylsy_deadline,
    ylsy_phase,
)
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


def _layout_row(length: int, fields: list[tuple[int, str]]) -> str:
    value = [" "] * length
    for start, text in fields:
        value[start : start + len(text)] = text
    return "".join(value)


def test_ylsy_public_preference_layout_becomes_a_structured_slot():
    page = _layout_row(
        690,
        [
            (22, "2025801"),
            (40, "20258001"),
            (57, "AFAD- AFET YÖNETİMİ"),
            (166, "Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)"),
            (254, "Deprem Erken Uyarı"),
            (344, "1"),
            (520, "Yüksek Lisans"),
            (550, "Almanya, Japonya"),
            (659, "Mühendis"),
        ],
    )

    rows = parse_ylsy_preference_layout([page], "public")

    assert rows == [
        {
            "group_code": "2025801",
            "area_code": "20258001",
            "page": 1,
            "group": "AFAD- AFET YÖNETİMİ",
            "organization": "Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)",
            "unit": "",
            "field": "Deprem Erken Uyarı",
            "quota": 1,
            "level": "Yüksek Lisans",
            "countries": "Almanya, Japonya",
            "role": "Mühendis",
        }
    ]


def test_ylsy_layout_detects_page_specific_column_shift():
    first_page = _layout_row(
        690,
        [
            (22, "2025801"),
            (40, "20258001"),
            (57, "AFAD- AFET YÖNETİMİ"),
            (166, "Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)"),
            (254, "Deprem Erken Uyarı"),
            (344, "1"),
            (520, "Yüksek Lisans"),
            (550, "Almanya"),
            (659, "Mühendis"),
        ],
    )
    shifted_page = _layout_row(
        690,
        [
            (21, "2025802"),
            (39, "20258002"),
            (55, "TUA- UZAY TEKNOLOJİLERİ"),
            (161, "Türkiye Uzay Ajansı"),
            (247, "Uydu Sistemleri"),
            (335, "2"),
            (508, "Yüksek Lisans"),
            (534, "Japonya"),
            (640, "Mühendis"),
        ],
    )

    rows = parse_ylsy_preference_layout([first_page, shifted_page], "public")

    assert [(row["organization"], row["quota"]) for row in rows] == [
        ("Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)", 1),
        ("Türkiye Uzay Ajansı", 2),
    ]


def test_ylsy_rss_covers_1416_news_missing_from_ajax_category():
    source = YlsySource("ylsy", "https://yyegm.meb.gov.tr/www/duyurular/kategori/2", (), "scholarship")
    body = b"""<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0"><channel><item>
      <title>1416 Burslari Kurum Tercih Islemleri Basladi</title>
      <link>https://yyegm.meb.gov.tr/www/kurum-tercihi/icerik/1</link>
      <pubDate>Mon, 18 May 2026 12:00:00 +0300</pubDate>
    </item></channel></rss>"""

    items = source.parse_rss(body)

    assert len(items) == 1
    assert items[0].extra["category"] == "ylsy-preference"
    assert items[0].published_at.isoformat() == "2026-05-18T09:00:00+00:00"


def test_ylsy_phase_and_deadline_extract_actionable_dates():
    assert ylsy_phase("2026 YLSY Başvuru Süresi Uzatıldı") == "extension"
    deadline = ylsy_deadline(
        "Başvurular 19-30 Aralık 2025 tarihleri arasında alınacak ve "
        "30 Aralık 2025 tarihinde saat 17.00'de sona erecektir."
    )
    assert deadline is not None
    assert deadline.isoformat() == "2025-12-30T14:00:00+00:00"


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


# ── ÖSYM ilgi profilleri + tarih çıkarımı ─────────────────────────────


def test_osym_interest_profiles_cover_required_profiles_and_custom_keywords():
    required = {
        "ales": "2026 ALES/1 başvuruları başladı",
        "yokdil": "2026 YÖKDİL/1 kılavuzu",
        "yds": "2026 e-YDS/1 sonuçları",
        "kpss": "2026 KPSS lisans başvuruları",
        "dgs": "2026 DGS başvuru işlemleri",
        "yks": "2026 YKS tercih kılavuzu",
        "tercih": "2026 tercih kılavuzu yayımlandı",
        "basvuru": "2026 başvuruları başladı",
        "sonuc": "2026 sonuçları açıklandı",
        "ek-yerlestirme": "2026 ek yerleştirme kontenjanları",
        "sinav-takvimi": "2026 sınav takvimi yayımlandı",
        "kilavuz": "2026 başvuru kılavuzu",
    }

    for profile, title in required.items():
        assert profile in osym_interest_profiles(title), title

    assert osym_interest_profiles("2026 Özel Yetenek Sınavı", ("özel yetenek",)) == [
        "özel yetenek",
    ]


def test_osym_announcement_fixture_extracts_dates_guides_and_applies_urls():
    source = OsymAnnouncementSource()
    items = source.parse_html(
        (FIXTURES / "osym_duyurular.html").read_text(),
        base_url="https://www.osym.gov.tr/Duyurular/Index",
    )
    by_url = {item.url: item for item in items}

    assert len(items) == 8
    ales = by_url["https://www.osym.gov.tr/duyurular/2026-ales-1-basvuru"]
    announcement = ales.extra["announcement"]
    assert {"ales", "basvuru"} <= set(ales.extra["profiles"])
    assert ales.published_at.isoformat() == "2026-08-26T00:00:00+00:00"
    assert announcement["stage"] == "application"
    assert announcement["application_start_at"] == "2026-08-25T21:00:00+00:00"
    assert announcement["exam_at"] == "2026-10-17T21:00:00+00:00"
    assert announcement["result_at"] == "2026-11-09T21:00:00+00:00"
    assert announcement["guide_url"] == "https://www.osym.gov.tr/dosyalar/2026-ales-1-kilavuzu.pdf"
    assert announcement["apply_url"] == "https://ais.osym.gov.tr"
    assert announcement["official"] is True
    assert announcement["canonical"] is True

    yokdil = by_url["https://www.osym.gov.tr/duyurular/2026-yokdil-1-basvuru"]
    assert yokdil.extra["announcement"]["application_start_at"] == "2026-08-31T21:00:00+00:00"
    assert yokdil.extra["announcement"]["application_end_at"] == "2026-09-12T20:59:00+00:00"

    yds = by_url["https://www.osym.gov.tr/duyurular/2026-e-yds-1-sonuc"]
    assert "yds" in yds.extra["profiles"]
    assert yds.extra["announcement"]["stage"] == "result"

    ek_yerlestirme = by_url["https://www.osym.gov.tr/duyurular/2026-yks-ek-yerlestirme"]
    assert "ek-yerlestirme" in ek_yerlestirme.extra["profiles"]
    assert ek_yerlestirme.extra["announcement"]["stage"] == "additional_placement"

    for item in items:
        assert item.extra["announcement"]["profiles"] or item.extra["profiles"]


def test_osym_correction_links_to_amended_announcement():
    source = OsymAnnouncementSource()
    items = source.parse_html(
        (FIXTURES / "osym_duyurular.html").read_text(),
        base_url="https://www.osym.gov.tr/Duyurular/Index",
    )
    by_url = {item.url: item for item in items}

    corrected = by_url["https://www.osym.gov.tr/duyurular/2026-ales-1-basvuru"]
    correction = by_url["https://www.osym.gov.tr/duyurular/2026-ales-1-kilavuz-duzeltme"]

    assert correction.extra["announcement"]["stage"] == "correction"
    assert correction.extra["announcement"]["corrects_external_id"] == corrected.external_id


# ── YLSY parent/child hiyerarşisi ─────────────────────────────────────


def _ylsy_slot(organization: str, field: str, quota: int, *, page: int = 1) -> dict:
    return {
        "group_code": "2026801",
        "area_code": "20268001",
        "page": page,
        "group": "GRUP",
        "organization": organization,
        "unit": "",
        "field": field,
        "quota": quota,
        "level": "Yüksek Lisans",
        "countries": "Almanya, Japonya",
        "role": "Mühendis",
    }


def test_ylsy_hierarchy_builds_one_parent_and_linked_children():
    parent, children = build_ylsy_hierarchy(
        guide_external_id="ylsy:2026:guide",
        guide_url="https://yyegm.meb.gov.tr/www/basvuru-kilavuzu/icerik/1",
        guide_year=2026,
        published_at=datetime(2026, 5, 18, tzinfo=UTC),
        dates={
            "application_start_at": datetime(2026, 5, 19, tzinfo=UTC),
            "application_end_at": datetime(2026, 6, 5, 23, 59, tzinfo=UTC),
        },
        tables={
            "public": (
                "https://yyegm.meb.gov.tr/tablo2.pdf",
                [
                    _ylsy_slot("Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)", "Deprem", 1),
                    _ylsy_slot("Türkiye Uzay Ajansı", "Uydu", 2),
                ],
            ),
            "university": (
                "https://yyegm.meb.gov.tr/tablo1.pdf",
                [_ylsy_slot("Boğaziçi Üniversitesi", "Bilgisayar", 3)],
            ),
        },
        apply_url="https://basvuru.yyegm.meb.gov.tr",
    )

    assert parent["stage"] == "guide"
    assert parent["official"] is True and parent["canonical"] is True
    assert parent["parent_external_id"] is None
    assert parent["quota_total"] == 6
    assert set(parent["fields"]) == {"Deprem", "Uydu", "Bilgisayar"}
    assert parent["guide_url"] == "https://yyegm.meb.gov.tr/www/basvuru-kilavuzu/icerik/1"
    assert parent["apply_url"] == "https://basvuru.yyegm.meb.gov.tr"

    assert len(children) == 3
    assert all(child.extra["announcement"]["parent_external_id"] == "ylsy:2026:guide" for child in children)
    assert all(child.extra["announcement"]["stage"] == "quota" for child in children)
    assert sum(child.extra["announcement"]["quota_total"] for child in children) == 6

    afad = next(child for child in children if "AFAD" in child.title)
    assert afad.extra["announcement"]["quota_total"] == 1
    assert afad.extra["announcement"]["fields"] == ["Deprem"]
    assert afad.extra["deadline_at"] == "2026-06-05T23:59:00+00:00"
    assert "tablo2.pdf" in afad.url


def test_ylsy_hierarchy_rejects_unknown_table_kind():
    with pytest.raises(ValueError):
        build_ylsy_hierarchy(
            guide_external_id="ylsy:2026:guide",
            guide_url="https://yyegm.meb.gov.tr/icerik/1",
            guide_year=2026,
            published_at=None,
            dates=None,
            tables={"private": ("https://yyegm.meb.gov.tr/tablo3.pdf", [])},
        )
