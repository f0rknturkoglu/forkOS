"""Fırsat kategorileri ve kaynak başlıklarından tarih normalizasyonu."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime

CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "data-ai",
        (
            "machine learning",
            "data scientist",
            "data engineer",
            "ai engineer",
            "ml engineer",
            "mlops",
            "artificial intelligence",
            "yapay zeka",
        ),
    ),
    (
        "cloud-security",
        (
            "devops",
            "site reliability",
            "sre",
            "platform engineer",
            "cloud",
            "cyber",
            "security",
            "guvenlik",
        ),
    ),
    (
        "product-design",
        (
            "product manager",
            "product designer",
            "product owner",
            "ux",
            "ui designer",
            "user experience",
        ),
    ),
    (
        "software",
        (
            "software",
            "developer",
            "engineer",
            "backend",
            "frontend",
            "full stack",
            "fullstack",
            "mobile",
            "quality assurance",
            "qa",
            "tester",
            "yazilim",
            "bilisim",
        ),
    ),
    (
        "sales-marketing",
        (
            "sales",
            "marketing",
            "account manager",
            "business development",
            "growth manager",
            "satis",
            "pazarlama",
        ),
    ),
    (
        "business-ops",
        (
            "operations",
            "finance",
            "financial",
            "legal",
            "people",
            "human resources",
            "analyst",
            "customer support",
            "customer success",
            "operasyon",
            "finans",
        ),
    ),
)

_MONTHS = {
    "ocak": 1,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "agustos": 8,
    "eylul": 9,
    "ekim": 10,
    "kasim": 11,
    "aralik": 12,
}
_HEADING_DATE = re.compile(r"^(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})(?:\s|$)")


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(
        "".join(character for character in decomposed if not unicodedata.combining(character))
        .replace("ı", "i")
        .split()
    )


def classify_job(title: str, department: str | None, description: str | None = None) -> str:
    primary = normalize_text(" ".join(filter(None, (title, department))))
    category = next(
        (slug for slug, needles in CATEGORY_RULES if any(needle in primary for needle in needles)),
        None,
    )
    if category is not None or not description:
        return category or "other"
    fallback = normalize_text(description)
    return next(
        (slug for slug, needles in CATEGORY_RULES if any(needle in fallback for needle in needles)),
        "other",
    )


def parse_turkish_heading_date(title: str) -> datetime | None:
    match = _HEADING_DATE.match(title.strip())
    if match is None:
        return None
    day, month_name, year = match.groups()
    month = _MONTHS.get(normalize_text(month_name))
    if month is None:
        return None
    try:
        return datetime(int(year), month, int(day), tzinfo=UTC)
    except ValueError:
        return None
