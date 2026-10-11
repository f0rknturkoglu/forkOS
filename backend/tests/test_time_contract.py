"""Faz 14: is kararlarinda tarayici/container gunu degil, ortak zaman servisi.

- Backend gun kararlari `app.core.time` uzerinden doner (`local_today`,
  `local_day_bounds`, `local_zone`); `settings.timezone` tek otoritedir.
- Odakli guardrail: is karari ureten dosyalarda `date.today()` (container
  gunu) ve sabit `ZoneInfo("Europe/Istanbul")` (ayar disi tz) yasak.
  Scraper'lar gibi harici veri toplayanlar kapsam disidir.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from app.core.time import local_today

APP_DIR = Path(__file__).resolve().parents[1] / "app"

# Is karari ureten dosyalar. Scraper'lar (tecnoempleo gibi) bilincli olarak
# disarida: harici sitemap tarihleri is karari degil.
BUSINESS_FILES = [
    "core/contributions.py",
    "core/time.py",
    "modules/todo/service.py",
    "modules/todo/router.py",
    "modules/today/service.py",
    "modules/today/router.py",
    "modules/system/backup.py",
    "modules/calendar/service.py",
    "modules/review/service.py",
    "modules/pomodoro/service.py",
    "modules/bookmark/service.py",
    "modules/rss/service.py",
    "modules/proactivity/service.py",
]


@pytest.mark.parametrize("relative", BUSINESS_FILES)
def test_no_naive_day_decisions_in_business_code(relative: str) -> None:
    source = (APP_DIR / relative).read_text(encoding="utf-8")
    assert "date.today()" not in source, (
        f"{relative}: date.today() container gunudur; local_today() kullan"
    )
    assert 'ZoneInfo("Europe/Istanbul")' not in source, (
        f"{relative}: sabit tz string yerine settings.timezone / local_zone()"
    )


def test_istanbul_evening_is_next_day() -> None:
    """2026-01-14T21:30:00Z Istanbul'da ertesi gundur (UTC+3)."""
    instant = datetime.fromisoformat("2026-01-14T21:30:00+00:00")
    assert local_today(instant) == date(2026, 1, 15)


def test_istanbul_morning_keeps_day() -> None:
    """Istanbul sabahina denk gelen UTC ani ayni gundur."""
    instant = datetime.fromisoformat("2026-01-14T06:00:00+00:00")
    assert local_today(instant) == date(2026, 1, 14)


def test_sunday_night_belongs_to_next_week() -> None:
    """Pazar gecesi -> hafta donumu: o anin gunu pazartesiden onceki haftada."""
    from app.modules.review.service import period_bounds

    sunday = date(2026, 1, 11)  # Pazar
    monday, end = period_bounds("weekly", sunday)
    assert monday == date(2026, 1, 5)
    assert end == date(2026, 1, 12)
    # Pazartesi gunu verilirse donem o gun baslar.
    monday2, _ = period_bounds("weekly", date(2026, 1, 12))
    assert monday2 == date(2026, 1, 12)
