from __future__ import annotations

import asyncio
import hashlib
import html
import io
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import httpx
from pypdf import PdfReader
from selectolax.parser import HTMLParser

from app.sources.base import FetchOutcome, RawItem


def parse_turkish_heading_date(title: str):
    """``taxonomy.parse_turkish_heading_date`` için tembel sarmalayıcı.

    taxonomy modülü ``app.modules`` paketini tetikler; o paket de bu modülü
    içe aktarır. Üst düzey import döngü yaratıyordu (özellikle bu modül ilk
    yüklendiğinde), bu yüzden çağrı anında çözülür.
    """
    from app.modules.opportunity.taxonomy import parse_turkish_heading_date as parse

    return parse(title)


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(c for c in value if not unicodedata.combining(c)).replace("ı", "i")


async def _request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int = 3,
    **kwargs,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code < 500 and response.status_code != 429:
                response.raise_for_status()
                return response
            last_exc = httpx.HTTPStatusError(
                f"HTTP {response.status_code}", request=response.request, response=response
            )
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            last_exc = exc
        if attempt < max_retries - 1:
            await asyncio.sleep(1.0 * (2**attempt))
    if last_exc:
        raise last_exc
    raise RuntimeError(f"Request failed for {url}")


class AnnouncementSource:
    interval_minutes = 720
    #: Yenileme sıralaması için kaynak sınıfı: critical | normal | slow_optin.
    source_class = "normal"

    def __init__(self, source_id: str, url: str, keywords: tuple[str, ...], kind: str):
        self.id, self.url, self.keywords, self.kind = source_id, url, keywords, kind

    async def fetch(self) -> list[RawItem]:
        async with httpx.AsyncClient(
            timeout=25,
            follow_redirects=True,
            headers={"User-Agent": "forkOS/0.1 local announcement monitor"},
        ) as client:
            response = await _request_with_retry(
                client, "GET", self.url, headers={"Accept": "text/html"}
            )
        return self.parse_html(response.text, base_url=str(response.url))

    def parse_html(self, body: str, *, base_url: str) -> list[RawItem]:
        """Ağdan bağımsız parser; fixture testleri gerçek fetch ile aynı yolu kullanır."""
        items: list[RawItem] = []
        for anchor in HTMLParser(body).css("a"):
            title = " ".join(anchor.text(deep=True).split())
            href = anchor.attributes.get("href")
            normalized = _norm(title)
            if not href or len(title) < 8 or not any(_norm(k) in normalized for k in self.keywords):
                continue
            url = urljoin(base_url, href)
            published_at = parse_turkish_heading_date(title)
            # ÖSYM sayfasındaki menü bağlantıları da "sınav" kelimesi taşır;
            # gerçek duyurular resmi gün/ay/yıl başlığıyla yayınlanır.
            if self.id == "osym" and published_at is None:
                continue
            items.append(
                RawItem(
                    external_id=hashlib.sha256(url.encode()).hexdigest(),
                    title=title,
                    url=url,
                    published_at=published_at,
                    extra={"organization": self.id.upper(), "kind": self.kind},
                )
            )
        return list({item.external_id: item for item in items}.values())


class OsymAnnouncementSource(AnnouncementSource):
    """ÖSYM duyuruları: ilgi profilleri + tarih/kılavuz/başvuru çıkarımı.

    Kullanıcı kendi ilgi kelimelerini ``extra_keywords`` ile ekler. ÖSYM sınav
    takvimi ve sonuç duyuruları için kanonik kaynaktır (``canonical``).
    """

    interval_minutes = 360
    source_class = "critical"
    official = True
    canonical = True

    def __init__(
        self,
        source_id: str = "osym",
        url: str = "https://www.osym.gov.tr/Duyurular/Index",
        extra_keywords: tuple[str, ...] = (),
        kind: str = "exam",
    ) -> None:
        super().__init__(source_id, url, OSYM_KEYWORDS, kind)
        self.extra_keywords = tuple(extra_keywords)

    def parse_html(
        self,
        body: str,
        *,
        base_url: str,
        extra_keywords: tuple[str, ...] = (),
        now: datetime | None = None,
    ) -> list[RawItem]:
        """İlanları ilgi profillerine göre süzer; tarih/URL alanlarını çıkarır."""
        items: list[RawItem] = []
        keywords = (*self.extra_keywords, *extra_keywords)
        for anchor in HTMLParser(body).css("a"):
            href = anchor.attributes.get("href")
            title = " ".join((anchor.text(deep=True) or "").split())
            if not href or len(title) < 8:
                continue
            profiles = osym_interest_profiles(title, keywords)
            if not profiles:
                continue
            url = urljoin(base_url, href)
            heading_date = parse_turkish_heading_date(title)
            # ÖSYM menü bağlantıları da ilgi kelimelerini taşır; gerçek
            # duyurular resmi gün/ay/yıl başlığıyla yayınlanır.
            if heading_date is None:
                continue
            context = announcement_context(anchor, title)
            dates = parse_announcement_dates(f"{title}. {context}", now=now)
            stage = announcement_stage(title)
            guide_url, apply_url = announcement_urls(
                announcement_container(anchor, title), base_url, skip_href=href
            )
            items.append(
                RawItem(
                    external_id=hashlib.sha256(url.encode()).hexdigest(),
                    title=title,
                    url=url,
                    summary=context if context != title else None,
                    published_at=heading_date or dates.get("published_at"),
                    extra={
                        "organization": "ÖSYM",
                        "kind": self.kind,
                        "category": f"osym-{stage}",
                        "channel": "osym-announcements",
                        "profiles": profiles,
                        "announcement": announcement_payload(
                            official=True,
                            canonical=True,
                            stage=stage,
                            dates=dates,
                            guide_url=guide_url,
                            apply_url=apply_url,
                            profiles=profiles,
                        ),
                    },
                )
            )
        return link_corrections(dedupe_announcement_items(items))


_YLSY_RSS_URL = "https://yyegm.meb.gov.tr/meb_iys_dosyalar/xml/rss_duyurular.xml"
_YLSY_AJAX_URL = "https://yyegm.meb.gov.tr/www/icerik_listele_ajax.php"
_YLSY_TERMS = ("ylsy", "1416", "burs", "lisansüstü")
_YLSY_MONTHS = {
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
_YLSY_DATE = re.compile(
    r"(?P<day>\d{1,2})\s+"
    r"(?P<month>ocak|subat|mart|nisan|mayis|haziran|temmuz|agustos|eylul|ekim|kasim|aralik)\s+"
    r"(?P<year>20\d{2})"
    r"(?:[^\d]{0,35}saat\s+(?P<hour>\d{1,2})[.:](?P<minute>\d{2}))?"
)


def ylsy_phase(title: str) -> str:
    normalized = _norm(title)
    if "sure uzat" in normalized or "suresi uzat" in normalized:
        return "extension"
    if "basvuru ve tercih kilavuzu" in normalized or "basvurulari basla" in normalized:
        return "application"
    if "kurum tercih" in normalized or "dil tercih" in normalized:
        return "preference"
    if "sonuc" in normalized or "hak kazanan" in normalized:
        return "result"
    if "sinav" in normalized:
        return "exam"
    if "dil kurs" in normalized:
        return "language"
    if "kilavuz" in normalized:
        return "guide"
    return "general"


def ylsy_deadline(text: str) -> datetime | None:
    """Duyuru metnindeki en guclu son tarih sinyalini Istanbul saatinde dondurur."""
    normalized = _norm(text)
    candidates: list[tuple[int, datetime]] = []
    for match in _YLSY_DATE.finditer(normalized):
        context = normalized[max(0, match.start() - 100) : match.end() + 100]
        score = sum(
            signal in context
            for signal in (
                "sona er",
                "son tarih",
                "son gun",
                "basvuru",
                "tercih",
                "belge teslim",
                "suresi",
            )
        )
        if score == 0:
            continue
        time_match = re.search(r"saat\s+(\d{1,2})[.:](\d{2})", normalized[match.end() : match.end() + 80])
        hour = int(match.group("hour") or (time_match.group(1) if time_match else 23))
        minute = int(match.group("minute") or (time_match.group(2) if time_match else 59))
        try:
            value = datetime(
                int(match.group("year")),
                _YLSY_MONTHS[match.group("month")],
                int(match.group("day")),
                hour,
                minute,
                tzinfo=ZoneInfo("Europe/Istanbul"),
            ).astimezone(UTC)
        except ValueError:
            continue
        candidates.append((score, value))
    if not candidates:
        return None
    best_score = max(score for score, _ in candidates)
    return max(value for score, value in candidates if score == best_score)


# ═════════════════════════════════════════════════════════════════════
# Duyuru çekirdeği (ÖSYM / YLSY / kamu kurumları ortak kullanır).
#
# Kurum adaptörleri bu modüldeki yardımcıları içe aktarır. announcements.py
# institutions.py'yi yalnızca modül düzeyindeki __getattr__ içinden, ihtiyaç
# anında yükler; böylece iki modül birbirini yarım hâlde görmez.

#: ÖSYM ilgi profilleri: slug -> başlıkta aranan normalize ifadeler.
#: Kullanıcı tanımlı kelimeler adapter'a `extra_keywords` ile eklenir.
OSYM_INTEREST_PROFILES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ales", ("ales", "akademik personel ve lisansustu egitim giris sinavi")),
    ("yokdil", ("yokdil", "yok dil")),
    ("yds", ("yds", "e-yds", "eyds", "yabanci dil bilgisi seviye tespit sinavi")),
    ("kpss", ("kpss", "kamu personel secme sinavi")),
    ("dgs", ("dgs", "dikey gecis sinavi")),
    ("yks", ("yks", "tyt", "ayt", "ydt", "yuksekogretim kurumlari sinavi")),
    ("tercih", ("tercih kilavuzu", "tercih kilavuzlari", "tercih islemleri", "tercih sureci")),
    ("basvuru", ("basvuru", "basvurulari", "basvurular")),
    ("sonuc", ("sonuc", "sonuclari", "sonuclarinin aciklanmasi")),
    ("ek-yerlestirme", ("ek yerles", "ekyerles", "ek kontenjan")),
    ("sinav-takvimi", ("sinav takvimi", "sinav tarihleri", "takvim")),
    ("kilavuz", ("kilavuz", "kilavuzu")),
)

#: ÖSYM kataloğunun başlık filtresi: profillerin birleşimi.
OSYM_KEYWORDS: tuple[str, ...] = tuple(
    dict.fromkeys(needle for _slug, needles in OSYM_INTEREST_PROFILES for needle in needles)
)

_ISTANBUL = ZoneInfo("Europe/Istanbul")
_MONTH_PATTERN = "|".join(_YLSY_MONTHS)
_TR_RANGE = re.compile(
    r"(?P<start>\d{1,2})\s*(?:-|–|—|\bile\b|\bila\b|\bve\b)\s*(?P<end>\d{1,2})\s+"
    r"(?P<month>" + _MONTH_PATTERN + r")\s+(?P<year>20\d{2})"
)
_TR_MONTH_DATE = re.compile(
    r"(?P<day>\d{1,2})\s+(?P<month>" + _MONTH_PATTERN + r")(?:\s+(?P<year>20\d{2}))?"
)
_TR_NUMERIC_DATE = re.compile(r"(?P<day>\d{1,2})[./](?P<month>\d{1,2})[./](?P<year>20\d{2})")
_TR_ISO_DATE = re.compile(r"(?P<year>20\d{2})-(?P<month>\d{1,2})-(?P<day>\d{1,2})")
_TR_CLOCK = re.compile(r"saat\s*(?P<hour>[01]?\d|2[0-3])[.:](?P<minute>[0-5]\d)")

#: Kategori -> metin penceresinde aranan sinyaller. Tarihe EN YAKIN sinyal
#: kazanır; eşitlikte sinyal sayısı, sonra bu sözlüğün sırası belirler.
_ANNOUNCEMENT_DATE_SIGNALS: dict[str, tuple[str, ...]] = {
    "application_end": (
        "son basvuru",
        "son tarih",
        "son gun",
        "sona er",
        "kadar",
        "bitis",
        "basvurularin son",
        "son odeme",
    ),
    "exam_at": ("sinav", "sinava", "sinavlar"),
    "result_at": ("sonuc", "aciklan", "ilan edil"),
    "published_at": ("yayimlan", "yayinlandi", "duyuruldu"),
    "application_start": ("basvuru", "kayit", "basla", "basliyor", "baslayacak"),
}
_DATE_SIGNAL_ORDER = tuple(_ANNOUNCEMENT_DATE_SIGNALS)

_ANNOUNCEMENT_STAGES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("correction", ("duzeltme", "revize", "guncelleme")),
    ("additional_placement", ("ek yerles", "ek kontenjan")),
    ("calendar", ("sinav takvimi", "sinav tarihleri")),
    ("guide", ("kilavuz",)),
    ("preference", ("tercih",)),
    ("result", ("sonuc", "aciklan", "hak kazanan")),
    ("exam", ("sinav",)),
    ("application", ("basvuru",)),
    ("extension", ("sure uzat", "suresi uzat")),
)


def osym_interest_profiles(title: str, extra_keywords: tuple[str, ...] = ()) -> list[str]:
    """Başlığın eşleştiği ilgi profillerini döndürür (kullanıcı kelimeleri dâhil)."""
    normalized = _norm(title)
    profiles = [
        slug
        for slug, needles in OSYM_INTEREST_PROFILES
        if any(_norm(needle) in normalized for needle in needles)
    ]
    profiles.extend(
        keyword.strip()
        for keyword in extra_keywords
        if keyword.strip() and _norm(keyword) in normalized
    )
    return list(dict.fromkeys(profiles))


def announcement_stage(text: str) -> str:
    """Duyurunun yaşam döngüsü aşaması (opportunity.stage serbest metindir)."""
    normalized = _norm(text)
    return next(
        (stage for stage, needles in _ANNOUNCEMENT_STAGES if any(n in normalized for n in needles)),
        "general",
    )


def _turkish_clock(normalized: str, end: int) -> tuple[int, int] | None:
    match = _TR_CLOCK.search(normalized, end, end + 30)
    return (int(match.group("hour")), int(match.group("minute"))) if match else None


def _istanbul_datetime(year: int, month: int, day: int, clock: tuple[int, int] | None):
    hour, minute = clock or (0, 0)
    try:
        return datetime(year, month, day, hour, minute, tzinfo=_ISTANBUL).astimezone(UTC)
    except ValueError:
        return None


def _date_mentions(normalized: str, *, default_year: int) -> list[dict]:
    """Toleranslı Türkçe tarih tarayıcı: aralık, gün-ay adı, 26.08.2026, 2026-08-26."""
    consumed: list[tuple[int, int]] = []
    mentions: list[dict] = []

    def overlaps(start: int, end: int) -> bool:
        return any(start < other_end and end > other_start for other_start, other_end in consumed)

    for match in _TR_RANGE.finditer(normalized):
        month = _YLSY_MONTHS[match.group("month")]
        clock = _turkish_clock(normalized, match.end())
        start_value = _istanbul_datetime(int(match.group("year")), month, int(match.group("start")), clock)
        end_value = _istanbul_datetime(int(match.group("year")), month, int(match.group("end")), clock)
        consumed.append(match.span())
        if start_value is not None:
            mentions.append({"category": "application_start", "value": start_value, "clock": clock, "start": match.start(), "end": match.end()})
        if end_value is not None:
            mentions.append({"category": "application_end", "value": end_value, "clock": clock, "start": match.start(), "end": match.end()})

    scans = (
        (_TR_ISO_DATE, ("year", "month", "day")),
        (_TR_NUMERIC_DATE, ("year", "month", "day")),
        (_TR_MONTH_DATE, ("year", "month", "day")),
    )
    for regex, _groups in scans:
        for match in regex.finditer(normalized):
            if overlaps(*match.span()):
                continue
            consumed.append(match.span())
            if regex is _TR_MONTH_DATE:
                month = _YLSY_MONTHS[match.group("month")]
                year = int(match.group("year") or default_year)
            else:
                month = int(match.group("month"))
                year = int(match.group("year"))
            clock = _turkish_clock(normalized, match.end())
            value = _istanbul_datetime(year, month, int(match.group("day")), clock)
            if value is not None:
                mentions.append({"category": None, "value": value, "clock": clock, "start": match.start(), "end": match.end()})
    return mentions


def _signal_distance(window: str, signal: str, anchor: int) -> int | None:
    """Sinyalin tarihe en yakın örneğinin mesafesi (yoksa None).

    Türkçede yüklem tarihten SONRA gelir ("... tarihinde başlayacaktır"), bu
    yüzden tarihten sonraki sinyaller 0.6 katsayısıyla daha güçlü sayılır.
    """
    best: int | None = None
    cursor = 0
    while True:
        position = window.find(signal, cursor)
        if position < 0:
            return best
        end = position + len(signal)
        if position <= anchor <= end:
            distance = 0
        else:
            distance = min(abs(anchor - position), abs(anchor - end))
            if position > anchor:
                distance = distance * 3 // 5
        best = distance if best is None else min(best, distance)
        cursor = position + 1


def _classify_mention(normalized: str, mention: dict) -> tuple[str | None, int]:
    """Tarihe en yakın sinyalin kategorisini ve mesafesini döndürür."""
    window_start = max(0, mention["start"] - 160)
    window = normalized[window_start : mention["end"] + 80]
    anchor = mention["start"] - window_start
    scores: dict[str, int] = {}
    for category, signals in _ANNOUNCEMENT_DATE_SIGNALS.items():
        distances = [
            distance
            for signal in signals
            if (distance := _signal_distance(window, signal, anchor)) is not None
        ]
        if distances:
            scores[category] = min(distances)
    if not scores:
        return None, 0
    category = min(
        scores,
        key=lambda name: (scores[name], _DATE_SIGNAL_ORDER.index(name)),
    )
    return category, scores[category]


def parse_announcement_dates(text: str, *, now: datetime | None = None) -> dict[str, datetime]:
    """Duyuru metninden başvuru/sınav/sonuç/yayın tarihlerini çıkarır.

    Dönüş anahtarları: published_at, application_start_at, application_end_at,
    exam_at, result_at (yalnızca bulunanlar). Tüm değerler UTC'dir. Aynı
    kategori için açık saatli ve tarihe daha yakın ifade aralık tahminini yener.
    """
    normalized = _norm(text)
    default_year = (now or datetime.now(UTC)).year
    # (öncelik, değer); öncelik = (açık saat, -mesafe). Aralık eşleşmeleri 0'dır.
    buckets: dict[str, list[tuple[tuple[int, int], datetime]]] = {}
    for mention in _date_mentions(normalized, default_year=default_year):
        category = mention["category"]
        if category is None:
            category, distance = _classify_mention(normalized, mention)
            if category is None:
                continue
            priority = (1 if mention["clock"] else 0, -distance)
        else:
            priority = (0, 0)
        value = mention["value"]
        if category == "application_end" and mention["clock"] is None:
            value = value.astimezone(_ISTANBUL).replace(hour=23, minute=59).astimezone(UTC)
        buckets.setdefault(category, []).append((priority, value))

    result: dict[str, datetime] = {}
    for category, values in buckets.items():
        best = max(priority for priority, _ in values)
        winners = [value for priority, value in values if priority == best]
        result[category] = max(winners) if category == "application_end" else min(winners)
    # Payload/DB sütun adlarıyla aynı anahtarlar (application_start_at/end_at).
    return {
        {"application_start": "application_start_at", "application_end": "application_end_at"}.get(
            category, category
        ): value
        for category, value in result.items()
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def announcement_payload(
    *,
    official: bool,
    canonical: bool,
    stage: str,
    dates: dict[str, datetime] | None = None,
    guide_url: str | None = None,
    apply_url: str | None = None,
    quota_total: int | None = None,
    fields: list[str] | None = None,
    parent_external_id: str | None = None,
    corrects_external_id: str | None = None,
    profiles: list[str] | None = None,
) -> dict:
    """`RawItem.extra["announcement"]` gövdesi.

    Ingest bu sözlüğü opportunity'nin duyuruya özel sütunlarına eşler:
    official, stage, application_start_at, application_end_at, exam_at,
    result_at, guide_url, apply_url, quota_total, fields (+parent/correction
    bağlantıları). Tarihler ISO-8601 metnidir; JSONB'ye doğrudan yazılır.
    """
    dates = dates or {}
    return {
        "official": official,
        "canonical": canonical,
        "stage": stage,
        "application_start_at": _iso(dates.get("application_start_at")),
        "application_end_at": _iso(dates.get("application_end_at")),
        "exam_at": _iso(dates.get("exam_at")),
        "result_at": _iso(dates.get("result_at")),
        "guide_url": guide_url,
        "apply_url": apply_url,
        "quota_total": quota_total,
        "fields": list(fields or []),
        "parent_external_id": str(parent_external_id) if parent_external_id else None,
        "corrects_external_id": str(corrects_external_id) if corrects_external_id else None,
        "profiles": list(profiles or []),
    }


def announcement_urls(node, base_url: str, *, skip_href: str | None = None) -> tuple[str | None, str | None]:
    """Bir duyuru satırındaki kılavuz/PDF ve başvuru bağlantılarını bulur."""
    guide_url: str | None = None
    apply_url: str | None = None
    candidates = list(node.css("a")) if node is not None else []
    for anchor in candidates:
        href = anchor.attributes.get("href")
        if not href or href == skip_href or href.startswith(("mailto:", "javascript:", "#")):
            continue
        target = urljoin(base_url, href)
        label = _norm(anchor.text(deep=True) or "")
        path = target.split("?", 1)[0].lower()
        if guide_url is None and ("kilavuz" in label or "kilavuz" in _norm(target) or path.endswith(".pdf")):
            guide_url = target
        if apply_url is None and (
            "basvuru" in label or "basvuru" in _norm(target) or "ais.osym" in target.lower()
        ):
            apply_url = target
    return guide_url, apply_url


_LINK_ELEMENT = re.compile(r"<a\b[^>]*>.*?</a>", re.IGNORECASE | re.DOTALL)
_HTML_TAG = re.compile(r"<[^>]*>")


def anchor_title(anchor) -> str:
    """Bağlantı başlığı; metin boşsa title/aria-label/img alt'a düşer.

    Gerçek listelerde duyuru kartları görsel bağlantı olur (metin boş,
    başlık ``title`` attribute'unda) — DSI/Haber kartları gibi.
    """
    title = " ".join((anchor.text(deep=True) or "").split())
    if len(title) >= 8:
        return title
    for attribute in ("title", "aria-label"):
        value = anchor.attributes.get(attribute)
        if value and len(value.strip()) >= 8:
            return " ".join(value.split())
    image = anchor.css_first("img")
    if image is not None:
        alt = image.attributes.get("alt")
        if alt and len(alt.strip()) >= 8:
            return " ".join(alt.split())
    return title


def _node_text(node, *, skip_links: bool) -> str:
    fragment = node.html or ""
    if skip_links:
        fragment = _LINK_ELEMENT.sub(" ", fragment)
    return " ".join(html.unescape(_HTML_TAG.sub(" ", fragment)).split())


def announcement_container(anchor, title: str, *, limit: int = 420, minimum_extra: int = 24):
    """Başlığın en yakın anlamlı kabı; sayfanın tamamına taşmayı engeller.

    Yalnızca başlığı saran ``<h3>`` gibi düğümler atlanır: duyuru tarihi ve
    kılavuz/başvuru bağlantıları kardeş düğümlerde yaşar.
    """
    node = anchor.parent
    fallback = anchor.parent
    for _ in range(4):
        if node is None:
            break
        try:
            text = " ".join((node.text(deep=True) or "").split())
        except Exception:  # noqa: BLE001 - bozuk ağaçta en dar bağlamı koru
            break
        if len(title) + minimum_extra <= len(text) <= len(title) + limit:
            return node
        node = node.parent
    return fallback


def announcement_context(anchor, title: str, *, limit: int = 420) -> str:
    """Konteyner metni (bağlantı etiketleri hariç); alınamazsa başlığa düşer.

    Bağlantı etiketleri ("Başvuru Kılavuzu" gibi) tarih sınıflandırmasını
    yanıltır; bu yüzden metinden çıkarılır. Satırın tamamı tek bir bağlantıysa
    bağlantılı metne düşülür.
    """
    node = announcement_container(anchor, title, limit=limit)
    if node is None:
        return title
    try:
        text = _node_text(node, skip_links=True)
        if len(text) < len(title) + 10:
            text = _node_text(node, skip_links=False)
    except Exception:  # noqa: BLE001
        return title
    return text or title


def link_corrections(items: list[RawItem]) -> list[RawItem]:
    """Düzeltme/revize duyurusunu, düzelttiği önceki duyuruya bağlar."""
    marked = {}
    for item in items:
        normalized = set(_norm(item.title).split())
        marker = any(
            signal in _norm(item.title)
            for signal in ("duzeltme", "revize", "guncelleme")
        )
        if marker:
            marked[item.external_id] = normalized
    if not marked:
        return items
    for item in items:
        tokens = marked.get(item.external_id)
        if not tokens:
            continue
        base = {
            token
            for token in tokens
            if token not in {"duzeltme", "ilani", "revize", "guncelleme", "guncel", "ek"}
        }
        best: RawItem | None = None
        best_overlap = 0.0
        for other in items:
            if other is item:
                continue
            other_tokens = set(_norm(other.title).split())
            if any(signal in _norm(other.title) for signal in ("duzeltme", "revize", "guncelleme")):
                continue
            shared = len(base & other_tokens)
            if shared < 2:
                continue
            overlap = shared / max(len(other_tokens), 1)
            if overlap >= 0.5 and overlap > best_overlap:
                best, best_overlap = other, overlap
        if best is not None:
            payload = item.extra.setdefault("announcement", {})
            payload["corrects_external_id"] = best.external_id
    return items


def dedupe_announcement_items(items: list[RawItem]) -> list[RawItem]:
    """Aynı duyuruyu kanonik URL ve normalize başlık üzerinden tekleştirir."""
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[RawItem] = []
    for item in items:
        url_key = item.url or ""
        title_key = _norm(item.title)
        if (url_key and url_key in seen_urls) or title_key in seen_titles:
            continue
        if url_key:
            seen_urls.add(url_key)
        seen_titles.add(title_key)
        unique.append(item)
    return unique


_YLSY_ROW = re.compile(r"^\s*(?P<group_code>\d{7})\s+(?P<area_code>\d{8})\s+")
_YLSY_LEVEL = re.compile(r"Yüksek Lisans ve Doktora|Yüksek Lisans|Sadece Doktora")


def _ylsy_page_columns(lines: list[str], table_kind: str) -> dict[str, tuple[int, int | None]]:
    """PDF sayfasinin kendi sütun başlangıçlarını ilk veri satırından bul.

    MEB tablolarinda sütunlar sayfalar arasında birkaç karakter kayıyor. Sabit
    offset kullanmak kurum adlarını bölüp aynı kurumu onlarca sahte kuruma
    çeviriyordu.
    """
    first = next((line for line in lines if _YLSY_ROW.match(line)), None)
    if first is None:
        return {}
    parts = re.split(r"\s{2,}", first.strip())
    core_names = (
        ("group", "organization", "unit", "field", "quota")
        if table_kind == "university"
        else ("group", "organization", "field", "quota")
    )
    core_values = parts[2 : 2 + len(core_names)]
    if len(core_values) != len(core_names):
        return {}

    starts: dict[str, int] = {}
    cursor = _YLSY_ROW.match(first).end()  # type: ignore[union-attr]
    for name, value in zip(core_names, core_values, strict=True):
        position = first.find(value, cursor)
        if position < 0:
            return {}
        starts[name] = position
        cursor = position + len(value)

    level_match = _YLSY_LEVEL.search(first, cursor)
    if level_match is not None:
        starts["level"] = level_match.start()
        tail = first[level_match.end() :]
        tail_parts = re.split(r"\s{2,}", tail.strip())
        if tail_parts:
            country_pos = first.find(tail_parts[0], level_match.end())
            if country_pos >= 0:
                starts["countries"] = country_pos
        if len(tail_parts) >= 2:
            role_pos = first.rfind(tail_parts[-1])
            if role_pos > starts.get("countries", level_match.start()):
                starts["role"] = role_pos

    ordered = sorted(starts.items(), key=lambda item: item[1])
    columns = {
        name: (start, ordered[index + 1][1] if index + 1 < len(ordered) else None)
        for index, (name, start) in enumerate(ordered)
    }
    if table_kind == "public":
        columns["unit"] = (0, 0)
    return columns


def parse_ylsy_preference_layout(pages: list[str], table_kind: str) -> list[dict]:
    """pypdf layout metnini satir bazli YLSY kontenjanlarina cevirir."""
    if table_kind not in {"public", "university"}:
        raise ValueError(f"bilinmeyen YLSY tablo turu: {table_kind}")
    rows: list[dict] = []

    def append_piece(row: dict, line: str, columns: dict[str, tuple[int, int | None]]) -> None:
        for name, (start, end) in columns.items():
            piece = " ".join(line[start:end].split())
            if piece:
                row[name].append(piece)

    for page_number, page in enumerate(pages, start=1):
        lines = page.splitlines()
        columns = _ylsy_page_columns(lines, table_kind)
        if not columns:
            continue
        current: dict | None = None
        for line in lines:
            match = _YLSY_ROW.match(line)
            if match is not None:
                if current is not None:
                    rows.append(current)
                current = {
                    "group_code": match.group("group_code"),
                    "area_code": match.group("area_code"),
                    "page": page_number,
                    **{name: [] for name in columns},
                }
                append_piece(current, line, columns)
            elif current is not None:
                append_piece(current, line, columns)
        if current is not None:
            rows.append(current)

    parsed: list[dict] = []
    for row in rows:
        compact = {
            key: " ".join(dict.fromkeys(value)).strip() if isinstance(value, list) else value
            for key, value in row.items()
        }
        quota_match = re.search(r"\d+", compact["quota"])
        compact["quota"] = int(quota_match.group()) if quota_match else 0
        if compact["organization"] and compact["group"]:
            parsed.append(compact)
    return parsed


def build_ylsy_hierarchy(
    *,
    guide_external_id: str,
    guide_url: str,
    guide_year: int,
    published_at: datetime | None,
    dates: dict[str, datetime] | None,
    tables: dict[str, tuple[str, list[dict]]],
    apply_url: str | None = None,
) -> tuple[dict, list[RawItem]]:
    """YLSY kılavuzundan (parent payload, child RawItem'lar) üretir.

    Parent = ana kılavuz duyurusu; children = kamu kurumu/üniversite kontenjan
    grupları. Düz yüzlerce satır yerine iki seviyeli kayıt: ingest
    ``announcement.parent_external_id`` alanını ``opportunity.parent_id``'ye
    çevirir. Dönen sözlük parent duyurunun announcement payload'ıdır.
    """
    dates = dates or {}
    children: list[RawItem] = []
    all_fields: list[str] = []
    total_quota = 0
    for table_kind, (pdf_url, rows) in tables.items():
        if table_kind not in {"public", "university"}:
            raise ValueError(f"bilinmeyen YLSY tablo turu: {table_kind}")
        grouped: dict[str, dict] = {}
        for row in rows:
            group = grouped.setdefault(
                _norm(row["organization"]),
                {
                    "organization": row["organization"],
                    "page": row["page"],
                    "quota": 0,
                    "slots": [],
                },
            )
            group["quota"] += row["quota"]
            group["slots"].append(row)
        label = "Kamu kurumu" if table_kind == "public" else "Üniversite"
        for key, group in grouped.items():
            digest = hashlib.sha256(key.encode()).hexdigest()[:16]
            fields = list(dict.fromkeys(row["field"] or row["group"] for row in group["slots"]))
            countries = list(
                dict.fromkeys(
                    country
                    for row in group["slots"]
                    for country in (part.strip() for part in row["countries"].split(","))
                    if country
                )
            )
            total_quota += group["quota"]
            all_fields.extend(fields)
            extra = {
                "organization": group["organization"],
                "kind": "scholarship",
                "category": f"ylsy-{table_kind}-slot",
                "channel": "yyegm-preference-table",
                "guide_year": guide_year,
                "slot_type": table_kind,
                "quota_total": group["quota"],
                "fields": fields,
                "countries": countries,
                "slots": group["slots"],
                "guide_url": guide_url,
                "pdf_url": pdf_url,
                "announcement": announcement_payload(
                    official=True,
                    canonical=True,
                    stage="quota",
                    dates=dates,
                    guide_url=guide_url,
                    apply_url=apply_url,
                    quota_total=group["quota"],
                    fields=fields,
                    parent_external_id=guide_external_id,
                    profiles=["ylsy", table_kind],
                ),
            }
            if dates.get("application_end_at") is not None:
                extra["deadline_at"] = dates["application_end_at"].isoformat()
            children.append(
                RawItem(
                    external_id=f"ylsy:{guide_year}:{table_kind}:{digest}",
                    title=f"{guide_year} YLSY · {group['organization']}",
                    url=f"{pdf_url}#page={group['page']}&institution={digest}",
                    summary=(
                        f"{label} YLSY kontenjanı: {group['quota']} kontenjan. "
                        f"Alanlar: {', '.join(fields)}. Ülkeler: {', '.join(countries)}."
                    ),
                    published_at=published_at,
                    extra=extra,
                )
            )

    parent = announcement_payload(
        official=True,
        canonical=True,
        stage="guide",
        dates=dates,
        guide_url=guide_url,
        apply_url=apply_url,
        quota_total=total_quota,
        fields=list(dict.fromkeys(all_fields)),
        profiles=["ylsy"],
    )
    return parent, children


class YlsySource(AnnouncementSource):
    page_size = 100
    max_records = 1000
    #: MEB/YYEGM YLSY'nin kanonik başvuru/kontenjan kaynağıdır; kurum siteleri
    #: yalnızca erken sinyal verir (bkz. institutions.py).
    source_class = "critical"
    official = True
    canonical = True

    @staticmethod
    def _form(start: int) -> dict[str, str]:
        return {
            "kategori": "2",
            "dil": "tr",
            "draw": "1",
            "start": str(start),
            "length": str(YlsySource.page_size),
            "order[0][column]": "2",
            "order[0][dir]": "desc",
            "search[value]": "",
            "columns[0][data]": "ISLEMSAAT",
            "columns[1][data]": "BASLIK",
            "columns[2][data]": "SIRAID",
        }

    def parse_rows(self, rows: list[dict]) -> list[RawItem]:
        items: list[RawItem] = []
        for row in rows:
            title = " ".join(html.unescape(row.get("BASLIK", "")).split())
            if not any(_norm(keyword) in _norm(title) for keyword in _YLSY_TERMS):
                continue
            href = row.get("LINK")
            if not href:
                continue
            url = urljoin(self.url, href)
            try:
                published_at = datetime.strptime(row["ISLEMSAAT"], "%d/%m/%Y").replace(tzinfo=UTC)
            except (KeyError, ValueError):
                published_at = None
            items.append(
                RawItem(
                    external_id=(
                        f"ylsy:{row.get('SIRAID') or hashlib.sha256(url.encode()).hexdigest()}"
                    ),
                    title=title,
                    url=url,
                    published_at=published_at,
                    extra={
                        "organization": "YLSY",
                        "kind": self.kind,
                        "category": f"ylsy-{ylsy_phase(title)}",
                        "channel": "yyegm-announcements",
                        "announcement": announcement_payload(
                            official=True,
                            canonical=True,
                            stage=announcement_stage(title),
                            dates=parse_announcement_dates(title),
                            profiles=["ylsy", ylsy_phase(title)],
                        ),
                    },
                )
            )
        return items

    def parse_rss(self, body: bytes) -> list[RawItem]:
        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            raise RuntimeError(f"YLSY RSS okunamadi: {exc}") from exc
        items: list[RawItem] = []
        for node in root.findall("./channel/item"):
            title = " ".join((node.findtext("title") or "").split())
            if not any(_norm(keyword) in _norm(title) for keyword in _YLSY_TERMS):
                continue
            url = (node.findtext("link") or "").strip()
            if not url:
                continue
            try:
                published_at = parsedate_to_datetime(node.findtext("pubDate") or "").astimezone(UTC)
            except (TypeError, ValueError):
                published_at = None
            items.append(
                RawItem(
                    external_id=f"ylsy:rss:{hashlib.sha256(url.encode()).hexdigest()}",
                    title=title,
                    url=url,
                    published_at=published_at,
                    extra={
                        "organization": "YLSY",
                        "kind": self.kind,
                        "category": f"ylsy-{ylsy_phase(title)}",
                        "channel": "yyegm-rss",
                        "announcement": announcement_payload(
                            official=True,
                            canonical=True,
                            stage=announcement_stage(title),
                            dates=parse_announcement_dates(title),
                            profiles=["ylsy", ylsy_phase(title)],
                        ),
                    },
                )
            )
        return items

    @staticmethod
    def _table_links(body: str, base_url: str) -> dict[str, str]:
        links: dict[str, str] = {}
        for anchor in HTMLParser(body).css("a"):
            href = anchor.attributes.get("href")
            if not href:
                continue
            candidate = _norm(f"{href} {anchor.text(deep=True)}")
            if "tablo1" in candidate and "pdf" in candidate:
                links["university"] = urljoin(base_url, href)
            elif "tablo2" in candidate and "pdf" in candidate:
                links["public"] = urljoin(base_url, href)
        return links

    @staticmethod
    def _pdf_rows(body: bytes, table_kind: str) -> list[dict]:
        reader = PdfReader(io.BytesIO(body))
        pages = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
        rows = parse_ylsy_preference_layout(pages, table_kind)
        if not rows:
            raise RuntimeError(f"YLSY {table_kind} tercih tablosu bos ayrisildi")
        return rows

    async def _guide_items(
        self, client: httpx.AsyncClient, items: list[RawItem]
    ) -> list[RawItem]:
        candidates = [
            item
            for item in items
            if "basvuru ve tercih kilavuzu" in _norm(item.title)
            and "eki" not in _norm(item.title)
            and item.url
        ]
        if not candidates:
            return []
        guide = max(
            candidates,
            key=lambda item: item.published_at or datetime.min.replace(tzinfo=UTC),
        )
        response = await _request_with_retry(client, "GET", guide.url)
        tree = HTMLParser(response.text)
        page_text = tree.text(separator=" ", strip=True)
        dates = parse_announcement_dates(page_text)
        deadline_at = dates.get("application_end_at") or ylsy_deadline(page_text)
        if deadline_at is not None:
            dates.setdefault("application_end_at", deadline_at)
        _, apply_url = announcement_urls(tree, str(response.url), skip_href=guide.url)
        year_match = re.search(r"20\d{2}", guide.title)
        guide_year = int(year_match.group()) if year_match else datetime.now(UTC).year

        links = self._table_links(response.text, str(response.url))
        tables: dict[str, tuple[str, list[dict]]] = {}
        for table_kind in ("public", "university"):
            pdf_url = links.get(table_kind)
            if pdf_url is None:
                raise RuntimeError(f"YLSY kilavuzunda {table_kind} tercih tablosu bulunamadi")
            pdf = await _request_with_retry(
                client,
                "GET",
                pdf_url,
                headers={"Accept": "application/pdf"},
            )
            tables[table_kind] = (str(pdf.url), self._pdf_rows(pdf.content, table_kind))

        parent_patch, children = build_ylsy_hierarchy(
            guide_external_id=guide.external_id,
            guide_url=guide.url or "",
            guide_year=guide_year,
            published_at=guide.published_at,
            dates=dates,
            tables=tables,
            apply_url=apply_url,
        )
        # Ana kılavuz duyurusu parent olur; kontenjan satırları ona bağlanır.
        guide.extra["announcement"] = parent_patch
        guide.extra["quota_total"] = parent_patch["quota_total"]
        guide.extra["fields"] = parent_patch["fields"]
        guide.extra["guide_url"] = guide.url
        if deadline_at is not None:
            guide.extra["deadline_at"] = deadline_at.isoformat()
        return children

    async def fetch(self) -> list[RawItem] | FetchOutcome:
        """Ana duyuru listesi + yardimci RSS + kilavuz/kontenjan tablolari.

        Ana AJAX listesi birincildir: alinamazsa kosum hatadir. Yardimci
        kaynaklar (RSS, kilavuz PDF'leri) bozulursa ana sonuclar KORUNUR ve
        kosum `partial` olur -- eksik kapsamla kapanma taramasi yapilamaz.
        """
        headers = {
            "User-Agent": "forkOS/0.1 local announcement monitor",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.url,
        }
        partial = False
        details: list[str] = []
        async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=headers) as client:
            await _request_with_retry(client, "GET", self.url)
            rows: list[dict] = []
            start = 0
            while start < self.max_records:
                try:
                    response = await _request_with_retry(
                        client,
                        "POST",
                        _YLSY_AJAX_URL,
                        data=self._form(start),
                    )
                    payload = response.json()
                    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                        raise RuntimeError(f"YLSY duyuru API beklenmeyen cevap: {payload!r}")
                except Exception as exc:  # noqa: BLE001 - ilk sayfa disinda kismi sonuc korunur
                    if not rows:
                        raise
                    partial = True
                    details.append(
                        f"duyuru sayfalamasi {start}. kayitta durdu ({type(exc).__name__})"
                    )
                    break
                page = payload["data"]
                rows.extend(page)
                try:
                    total = int(payload.get("recordsFiltered") or payload.get("recordsTotal"))
                except (TypeError, ValueError):
                    total = len(rows)
                if not page or len(rows) >= total:
                    break
                start += len(page)

            items = self.parse_rows(rows)

            try:
                rss_response = await _request_with_retry(
                    client,
                    "GET",
                    _YLSY_RSS_URL,
                    headers={"Accept": "application/rss+xml, application/xml, text/xml"},
                )
                known_titles = {_norm(item.title) for item in items}
                items.extend(
                    item
                    for item in self.parse_rss(rss_response.content)
                    if _norm(item.title) not in known_titles
                )
            except Exception as exc:  # noqa: BLE001 - yardimci feed: ana sonuc korunur
                partial = True
                details.append(f"rss: {type(exc).__name__}")

            try:
                items.extend(await self._guide_items(client, items))
            except Exception as exc:  # noqa: BLE001 - kilavuz/kontenjan: ana sonuc korunur
                partial = True
                details.append(f"kilavuz/kontenjan: {type(exc).__name__}")

        deduped = list({item.external_id: item for item in link_corrections(items)}.values())
        if not partial:
            return deduped
        return FetchOutcome(items=deduped, partial=True, detail="; ".join(details))


class YokAnnouncementSource(AnnouncementSource):
    source_class = "normal"
    official = True
    canonical = True

    def __init__(self) -> None:
        super().__init__(
            "yok-msc",
            "https://www.yok.gov.tr/tr/announcements",
            ("yüksek lisans", "lisansüstü", "burs", "başvuru"),
            "msc",
        )

    def parse_html(
        self, body: str, *, base_url: str, year: int | None = None
    ) -> list[RawItem]:
        items: list[RawItem] = []
        publication_year = year or datetime.now(UTC).year
        for card in HTMLParser(body).css(".blog-item"):
            # Guncel YOK kartlarinda ilk baglanti yalnizca gorseli sarar ve metni
            # bostur. Once baslik baglantisini, eski semalarda ise metni en dolu
            # baglantiyi kullan.
            anchor = card.css_first("h3.title a[href]")
            if anchor is None:
                anchors = [node for node in card.css("a") if node.attributes.get("href")]
                anchor = max(
                    anchors,
                    key=lambda node: len(" ".join(node.text(deep=True).split())),
                    default=None,
                )
            if anchor is None:
                continue
            title = " ".join(anchor.text(deep=True).split())
            if not any(_norm(keyword) in _norm(title) for keyword in self.keywords):
                continue
            href = anchor.attributes.get("href")
            month_node = card.css_first(".date-block .month")
            day_node = card.css_first(".date-block .day")
            published_at = None
            if month_node is not None and day_node is not None:
                published_at = parse_turkish_heading_date(
                    f"{day_node.text(strip=True)} {month_node.text(strip=True)} {publication_year}"
                )
            url = urljoin(base_url, href)
            stage = announcement_stage(title)
            items.append(
                RawItem(
                    external_id=hashlib.sha256(url.encode()).hexdigest(),
                    title=title,
                    url=url,
                    published_at=published_at,
                    extra={
                        "organization": "YÖK",
                        "kind": self.kind,
                        "announcement": announcement_payload(
                            official=True,
                            canonical=True,
                            stage=stage,
                            dates=parse_announcement_dates(title),
                            profiles=[stage],
                        ),
                    },
                )
            )
        return list({item.external_id: item for item in items}.values())


#: Çekirdek duyuru kaynakları. Kurum adaptörleri institutions.py'de tanımlıdır.
#: İki modül birbirini yarım hâlde içe aktarmasın diye SOURCES tembel birleşir
#: (PEP 562): worker/router `from ... import SOURCES` ile aynı listeyi görür,
#: institutions.py ise announcements.py'yi normal yoldan içe aktarır.
_BASE_SOURCES = [
    OsymAnnouncementSource(),
    YlsySource(
        "ylsy",
        "https://yyegm.meb.gov.tr/www/duyurular/kategori/2",
        _YLSY_TERMS,
        "scholarship",
    ),
    YokAnnouncementSource(),
]


def __getattr__(name: str):
    if name == "SOURCES":
        from app.sources.institutions import INSTITUTION_SOURCES

        return [*_BASE_SOURCES, *INSTITUTION_SOURCES]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
