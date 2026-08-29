from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.opportunity.taxonomy import classify_job, parse_turkish_heading_date

pytestmark = pytest.mark.no_database


@pytest.mark.parametrize(
    ("title", "department", "expected"),
    [
        ("Senior Backend Engineer", "Engineering", "software"),
        ("MLOps Engineer", "Data Scientist", "data-ai"),
        ("Product Designer", "Product", "product-design"),
        ("Cloud Security Specialist", "Security", "cloud-security"),
        ("Financial Operations Analyst", "Finance", "business-ops"),
        ("B2B Sales Manager", "Sales", "sales-marketing"),
        ("Yazılım Geliştirme Uzmanı", "Bilişim", "software"),
        ("Veteriner Hekim", None, "other"),
    ],
)
def test_classify_job(title: str, department: str | None, expected: str) -> None:
    assert classify_job(title, department) == expected


def test_title_category_is_not_overridden_by_generic_description_terms() -> None:
    assert (
        classify_job(
            "Software Engineer",
            "Engineering",
            "Build a cloud SaaS platform with the product team",
        )
        == "software"
    )


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        (
            "26 Ağustos 2026 2026-MEB-AGS: Sınav Sonuçları Açıklandı",
            datetime(2026, 8, 26, tzinfo=UTC),
        ),
        ("5 Ocak 2026 2026-MSÜ Sınavı: Başvuruların Alınması", datetime(2026, 1, 5, tzinfo=UTC)),
        ("Tarih içermeyen duyuru", None),
        ("32 Ağustos 2026 Geçersiz tarih", None),
    ],
)
def test_parse_turkish_heading_date(title: str, expected: datetime | None) -> None:
    assert parse_turkish_heading_date(title) == expected
