"""H4 deterministik zamansal ayrıştırıcı — kaynak temellendirmesinin çekirdeği.

Amaç: modelin döndürdüğü normalize edilmiş tarih/saat alanının, **sağlanan
kaynak ifadeden** kod tarafından doğrulanabilmesi. Model önerir; bu modül
karar verir.

İlkeler (§5/§10/§12):

  - **Desteklenmeyen biçim → `None`.** Tahmin yok: "gelecek yıl", "muhtemelen
    gelecek hafta", "yıl belirtilmemişse bu yıl" gibi çıkarımlar YAPILMAZ.
  - **Küçük ve belgelenmiş biçim kümesi.** Doğal dil tarih anlama yoktur
    ("gelecek Cuma", "tatilden sonra" desteklenmez).
  - **Takvim doğrulaması gerçektir:** `datetime.date` kurulur, bu yüzden
    `31 Şubat 2027` veya `2026-13-01` sessizce geçemez.
  - Yeni bağımlılık YOKTUR: yalnızca `re`, `unicodedata`, `datetime`.

Belgelenmiş desteklenen biçimler:

```text
2026-09-30                      ISO
30.09.2026                      DD.MM.YYYY
30/09/2026                      DD/MM/YYYY
30 Eylül 2026                   D Ay YYYY
September 30, 2026              Ay D, YYYY
1 - 5 Eylül 2026                gün aralığı (aynı ay)
1–5 September 2026              gün aralığı (aynı ay, tire varyantı)
25 Ocak - 5 Şubat 2027          ay geçen aralık
January 25 - February 5 2027    ay geçen aralık (EN)
September 1-5, 2026             ay-önce gün aralığı (EN)
09:00 / 9:00                    HH:MM (24 saat) → "09:00"
Pazartesi / Monday              hafta günü
```
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

#: Unicode tire varyantları tek tireye indirilir (kaynak metinlerde karışıktır).
_DASH_CHARS = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\u2043"

TR_MONTHS: dict[str, int] = {
    "ocak": 1,
    "şubat": 2,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "agustos": 8,
    "eylül": 9,
    "eylul": 9,
    "ekim": 10,
    "kasım": 11,
    "kasim": 11,
    "aralık": 12,
    "aralik": 12,
}

EN_MONTHS: dict[str, int] = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

MONTHS: dict[str, int] = {**TR_MONTHS, **EN_MONTHS}

#: Hafta günü adları → normalize gün (contract `DayOfWeek` ile aynı sözlük).
TR_WEEKDAYS: dict[str, str] = {
    "pazartesi": "monday",
    "salı": "tuesday",
    "sali": "tuesday",
    "çarşamba": "wednesday",
    "carsamba": "wednesday",
    "perşembe": "thursday",
    "persembe": "thursday",
    "cuma": "friday",
    "cumartesi": "saturday",
    "pazar": "sunday",
}

EN_WEEKDAYS: dict[str, str] = {
    "monday": "monday",
    "tuesday": "tuesday",
    "wednesday": "wednesday",
    "thursday": "thursday",
    "friday": "friday",
    "saturday": "saturday",
    "sunday": "sunday",
}

WEEKDAYS: dict[str, str] = {**TR_WEEKDAYS, **EN_WEEKDAYS}

#: Ay adı parçası (TR aksanlı harfler dâhil).
_MONTH_TOKEN = r"[^\W\d_]+"

_TIME_RE = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)")

_ISO_RE = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
_DOTTED_RE = re.compile(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)")
_SLASHED_RE = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)")
_DAY_MONTH_YEAR_RE = re.compile(rf"(?<!\d)(\d{{1,2}})\s+({_MONTH_TOKEN})\s+(\d{{4}})(?!\d)")
_MONTH_DAY_YEAR_RE = re.compile(rf"({_MONTH_TOKEN})\s+(\d{{1,2}})\s*,?\s*(\d{{4}})(?!\d)")

_SHARED_MONTH_RANGE_RE = re.compile(
    rf"(?<!\d)(\d{{1,2}})\s*-\s*(\d{{1,2}})\s+({_MONTH_TOKEN})\s+(\d{{4}})(?!\d)"
)
_CROSS_MONTH_RANGE_RE = re.compile(
    rf"(?<!\d)(\d{{1,2}})\s+({_MONTH_TOKEN})\s*-\s*(\d{{1,2}})\s+({_MONTH_TOKEN})\s+(\d{{4}})(?!\d)"
)
_MONTH_DAY_RANGE_RE = re.compile(
    rf"({_MONTH_TOKEN})\s+(\d{{1,2}})\s*-\s*(\d{{1,2}})\s*,?\s*(\d{{4}})(?!\d)"
)
_MONTH_CROSS_RANGE_RE = re.compile(
    rf"({_MONTH_TOKEN})\s+(\d{{1,2}})\s*-\s*({_MONTH_TOKEN})\s+(\d{{1,2}})\s*,?\s*(\d{{4}})(?!\d)"
)


def normalize(text: str) -> str:
    """NFKC + tire normalizasyonu + boşluk daraltma + casefold.

    Ay/gün adları büyük-küçük harf duyarsız eşleşir; aksanlı ve aksansız
    yazımlar (`Eylül`/`Eylul`) aynı aya çözülür.
    """
    value = unicodedata.normalize("NFKC", text or "")
    for dash in _DASH_CHARS:
        value = value.replace(dash, "-")
    return " ".join(value.split()).casefold()


def _build(year: int, month: int, day: int) -> date | None:
    """Geçerli takvim tarihi kurar; geçersizse None (31 Şubat geçemez)."""
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _month(token: str) -> int | None:
    return MONTHS.get(token.casefold())


def parse_single_date(text: str) -> date | None:
    """Metindeki İLK tek tarihi çözer; desteklenmeyen biçimde `None`."""
    value = normalize(text)
    if not value:
        return None

    for pattern in (_ISO_RE, _DOTTED_RE, _SLASHED_RE):
        match = pattern.search(value)
        if match is None:
            continue
        first, second, third = (int(part) for part in match.groups())
        if pattern is _ISO_RE:
            return _build(first, second, third)
        return _build(third, second, first)

    match = _DAY_MONTH_YEAR_RE.search(value)
    if match is not None:
        month = _month(match.group(2))
        if month is not None:
            return _build(int(match.group(3)), month, int(match.group(1)))

    match = _MONTH_DAY_YEAR_RE.search(value)
    if match is not None:
        month = _month(match.group(1))
        if month is not None:
            return _build(int(match.group(3)), month, int(match.group(2)))

    return None


def find_all_dates(text: str) -> tuple[date, ...]:
    """Metinde GÖRÜNME SIRASINA göre bulunan TÜM tarihleri döner.

    "X ile Y", "X to Y", "X - Y" gibi bağlaçlı aralıklar bu tarama ile
    deterministik olarak çözülür: bağlaç sözcüğü ayrıştırılmaz, iki tarih
    bağımsız olarak okunur. Tahmin yoktur.
    """
    value = normalize(text)
    found: list[tuple[int, date]] = []
    for pattern in (_ISO_RE, _DOTTED_RE, _SLASHED_RE):
        for match in pattern.finditer(value):
            parts = [int(part) for part in match.groups()]
            parsed = (
                _build(parts[0], parts[1], parts[2])
                if pattern is _ISO_RE
                else _build(parts[2], parts[1], parts[0])
            )
            if parsed is not None:
                found.append((match.start(), parsed))
    for pattern in (_DAY_MONTH_YEAR_RE, _MONTH_DAY_YEAR_RE):
        for match in pattern.finditer(value):
            month = _month(match.group(2) if pattern is _DAY_MONTH_YEAR_RE else match.group(1))
            if month is None:
                continue
            day = int(match.group(1) if pattern is _DAY_MONTH_YEAR_RE else match.group(2))
            parsed = _build(int(match.group(3)), month, day)
            if parsed is not None:
                found.append((match.start(), parsed))

    ordered: list[date] = []
    for _position, parsed in sorted(found, key=lambda row: row[0]):
        if not ordered or ordered[-1] != parsed:
            ordered.append(parsed)
    return tuple(ordered)


def parse_date_range(text: str) -> tuple[date | None, date | None]:
    """Metindeki tarih ARALIĞINI çözer.

    Döner: `(start, end)`. Aralık yoksa tek tarih `(date, date)` olur; hiçbir
    şey çözülemezse `(None, None)`. Tahmin YAPILMAZ.

    Sıra: önce özel aralık kalıpları (ikinci uçta yıl tekrarı gerektirmeyen
    "1 - 5 Eylül 2026" gibi biçimler), sonra bağlaçlı/yinelenen tam tarihler
    ("1 Eylül 2026 ile 5 Eylül 2026", "7 September 2026 to 11 September 2026").
    İkiden fazla tarih varsa ilk İKİSİ alınır (deterministik, belgelenmiş).
    """
    value = normalize(text)
    if not value:
        return None, None

    match = _SHARED_MONTH_RANGE_RE.search(value)
    if match is not None:
        month = _month(match.group(3))
        if month is not None:
            year = int(match.group(4))
            return _build(year, month, int(match.group(1))), _build(year, month, int(match.group(2)))

    match = _CROSS_MONTH_RANGE_RE.search(value)
    if match is not None:
        start_month, end_month = _month(match.group(2)), _month(match.group(4))
        if start_month is not None and end_month is not None:
            year = int(match.group(5))
            return (
                _build(year, start_month, int(match.group(1))),
                _build(year, end_month, int(match.group(3))),
            )

    match = _MONTH_DAY_RANGE_RE.search(value)
    if match is not None:
        month = _month(match.group(1))
        if month is not None:
            year = int(match.group(4))
            return _build(year, month, int(match.group(2))), _build(year, month, int(match.group(3)))

    match = _MONTH_CROSS_RANGE_RE.search(value)
    if match is not None:
        start_month, end_month = _month(match.group(1)), _month(match.group(3))
        if start_month is not None and end_month is not None:
            year = int(match.group(5))
            return (
                _build(year, start_month, int(match.group(2))),
                _build(year, end_month, int(match.group(4))),
            )

    found = find_all_dates(value)
    if len(found) >= 2:
        return found[0], found[1]
    if len(found) == 1:
        return found[0], found[0]
    return None, None


def parse_times(text: str) -> tuple[str, ...]:
    """Metindeki `HH:MM` saatlerini GÖRÜNME SIRASINA göre döner.

    `9:00` → `09:00` olarak normalize edilir (belgelenmiş davranış). AM/PM
    yorumu YAPILMAZ.
    """
    value = normalize(text)
    return tuple(f"{int(hour):02d}:{minute}" for hour, minute in _TIME_RE.findall(value))


def find_weekday(text: str) -> str | None:
    """Metindeki TEK hafta gününü döner.

    Hiç tanınan gün yoksa ya da birden fazla FARKLI gün geçiyorsa `None`:
    belirsizlik tahmin edilmez (§18).
    """
    value = normalize(text)
    found = {
        normalized
        for token, normalized in WEEKDAYS.items()
        if re.search(rf"(?<!\w){re.escape(token)}(?!\w)", value)
    }
    if len(found) == 1:
        return next(iter(found))
    return None


def weekday_tokens(text: str) -> tuple[str, ...]:
    """Metinde geçen TÜM hafta günü adlarını (görünme sırası) döner.

    `find_weekday` belirsizlikte `None` döndüğü için, çakışmayı ayırt etmek
    isteyen çağıranlar bunu kullanır.
    """
    value = normalize(text)
    tokens: list[str] = []
    for match in re.finditer(rf"(?<!\w)({_MONTH_TOKEN})(?!\w)", value):
        token = match.group(1)
        if token in WEEKDAYS:
            tokens.append(token)
    return tuple(tokens)


__all__ = [
    "EN_MONTHS",
    "find_all_dates",
    "EN_WEEKDAYS",
    "MONTHS",
    "TR_MONTHS",
    "TR_WEEKDAYS",
    "WEEKDAYS",
    "find_weekday",
    "normalize",
    "parse_date_range",
    "parse_single_date",
    "parse_times",
    "weekday_tokens",
]
