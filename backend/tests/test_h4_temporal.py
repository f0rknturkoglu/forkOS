"""Deterministik zamansal ayrıştırıcı — belgelenmiş biçimler ve sınırlar."""

from __future__ import annotations

from datetime import date

import pytest

from app.integrations.local_cognition import temporal as temporal_svc


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-09-30", date(2026, 9, 30)),
        ("30.09.2026", date(2026, 9, 30)),
        ("30/09/2026", date(2026, 9, 30)),
        ("30 Eylül 2026", date(2026, 9, 30)),
        ("30 EYLÜL 2026", date(2026, 9, 30)),
        ("September 30, 2026", date(2026, 9, 30)),
        ("September 30 2026", date(2026, 9, 30)),
    ],
)
def test_supported_single_date_formats(text: str, expected: date) -> None:
    assert temporal_svc.parse_single_date(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1 - 5 Eylül 2026", (date(2026, 9, 1), date(2026, 9, 5))),
        ("1–5 Eylül 2026", (date(2026, 9, 1), date(2026, 9, 5))),
        ("1-5 September 2026", (date(2026, 9, 1), date(2026, 9, 5))),
        ("September 1-5, 2026", (date(2026, 9, 1), date(2026, 9, 5))),
        ("25 Ocak - 5 Şubat 2027", (date(2027, 1, 25), date(2027, 2, 5))),
        ("25 January - 5 February 2027", (date(2027, 1, 25), date(2027, 2, 5))),
        ("January 25 - February 5 2027", (date(2027, 1, 25), date(2027, 2, 5))),
        ("Final exams: January 12-20, 2027", (date(2027, 1, 12), date(2027, 1, 20))),
        ("Kayıt yenileme: 1 - 5 Eylül 2026", (date(2026, 9, 1), date(2026, 9, 5))),
    ],
)
def test_supported_date_ranges(text: str, expected: tuple[date, date]) -> None:
    assert temporal_svc.parse_date_range(text) == expected


def test_single_date_range_returns_the_same_day_for_both_ends() -> None:
    assert temporal_svc.parse_date_range("30 Eylül 2026") == (date(2026, 9, 30), date(2026, 9, 30))


@pytest.mark.parametrize(
    "text",
    [
        "31 February 2027",
        "32 Eylül 2026",
        "2026-13-01",
        "30.02.2026",
        "Final sınavı: 20 Kasım",
        "gelecek Cuma",
        "end of next month",
        "after the holiday",
        "süre 90 dakika",
        "",
        "   ",
    ],
)
def test_unsupported_or_invalid_dates_do_not_resolve(text: str) -> None:
    """Tahmin YOK: desteklenmeyen biçim `None` döner (H4.1 §5/§68)."""
    assert temporal_svc.parse_single_date(text) is None
    assert temporal_svc.parse_date_range(text) == (None, None)


def test_no_implicit_year_is_ever_inferred() -> None:
    assert temporal_svc.parse_date_range("20 Kasım") == (None, None)
    assert temporal_svc.parse_date_range("20 November") == (None, None)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Pazartesi 09:00-11:00 Veri Yapıları", ("09:00", "11:00")),
        ("Çarşamba 14:00-16:00 İngilizce", ("14:00", "16:00")),
        ("Monday 9:00 - 11:30", ("09:00", "11:30")),
        ("süre 90 dakika", ()),
        ("12 Ekim 2026", ()),
    ],
)
def test_time_tokens_are_ordered_and_normalized(text: str, expected: tuple[str, ...]) -> None:
    assert temporal_svc.parse_times(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Pazartesi 09:00-11:00", "monday"),
        ("SALI 09:00", "tuesday"),
        ("Çarşamba", "wednesday"),
        ("Perşembe", "thursday"),
        ("Cuma", "friday"),
        ("Cumartesi", "saturday"),
        ("Pazar", "sunday"),
        ("Monday", "monday"),
        ("sunday", "sunday"),
        ("Pazartesi Pazartesi", "monday"),
    ],
)
def test_single_weekday_resolves(text: str, expected: str) -> None:
    assert temporal_svc.find_weekday(text) == expected


@pytest.mark.parametrize("text", ["Pazartesi ve Cuma", "Monday or Tuesday", "serbest metin", ""])
def test_conflicting_or_absent_weekdays_do_not_resolve(text: str) -> None:
    """Belirsizlik tahmin edilmez (§18)."""
    assert temporal_svc.find_weekday(text) is None


def test_weekday_matching_is_word_bounded() -> None:
    """`pazar` ile `pazartesi` karışmaz; `cuma` ile `cumartesi` karışmaz."""
    assert temporal_svc.find_weekday("pazartesi") == "monday"
    assert temporal_svc.find_weekday("cumartesi") == "saturday"
    assert temporal_svc.find_weekday("pazar") == "sunday"
    assert temporal_svc.find_weekday("cuma") == "friday"


def test_normalize_handles_unicode_dashes_and_case() -> None:
    assert temporal_svc.normalize("1 – 5 EYLÜL 2026") == "1 - 5 eylül 2026"
    assert temporal_svc.normalize("  a\tb\n") == "a b"


def test_parser_uses_only_standard_library() -> None:
    """Yeni bağımlılık YOK (§82): modül yalnızca stdlib kullanır."""
    import inspect

    source = inspect.getsource(temporal_svc)
    assert "import dateutil" not in source
    assert "import parsedatetime" not in source
    assert "httpx" not in source
