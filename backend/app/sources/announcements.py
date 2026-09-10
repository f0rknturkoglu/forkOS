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

from app.modules.opportunity.taxonomy import parse_turkish_heading_date
from app.sources.base import RawItem


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


class YlsySource(AnnouncementSource):
    page_size = 100
    max_records = 1000

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
    def _table_items(
        body: bytes,
        *,
        table_kind: str,
        pdf_url: str,
        guide_url: str,
        guide_year: int,
        published_at: datetime | None,
        deadline_at: datetime | None,
    ) -> list[RawItem]:
        reader = PdfReader(io.BytesIO(body))
        pages = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
        rows = parse_ylsy_preference_layout(pages, table_kind)
        if not rows:
            raise RuntimeError(f"YLSY {table_kind} tercih tablosu bos ayrisildi")

        grouped: dict[str, dict] = {}
        for row in rows:
            key = _norm(row["organization"])
            group = grouped.setdefault(
                key,
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
        items: list[RawItem] = []
        for key, group in grouped.items():
            digest = hashlib.sha256(key.encode()).hexdigest()[:16]
            fields = list(
                dict.fromkeys(row["field"] or row["group"] for row in group["slots"])
            )
            countries = list(
                dict.fromkeys(
                    country
                    for row in group["slots"]
                    for country in (part.strip() for part in row["countries"].split(","))
                    if country
                )
            )
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
            }
            if deadline_at is not None:
                extra["deadline_at"] = deadline_at.isoformat()
            items.append(
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
        return items

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
        page_text = HTMLParser(response.text).text(separator=" ", strip=True)
        deadline_at = ylsy_deadline(page_text)
        if deadline_at is not None:
            guide.extra["deadline_at"] = deadline_at.isoformat()
        year_match = re.search(r"20\d{2}", guide.title)
        guide_year = int(year_match.group()) if year_match else datetime.now(UTC).year
        links = self._table_links(response.text, str(response.url))
        table_items: list[RawItem] = []
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
            table_items.extend(
                self._table_items(
                    pdf.content,
                    table_kind=table_kind,
                    pdf_url=str(pdf.url),
                    guide_url=guide.url,
                    guide_year=guide_year,
                    published_at=guide.published_at,
                    deadline_at=deadline_at,
                )
            )
        return table_items

    async def fetch(self) -> list[RawItem]:
        headers = {
            "User-Agent": "forkOS/0.1 local announcement monitor",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.url,
        }
        async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=headers) as client:
            await _request_with_retry(client, "GET", self.url)
            rows: list[dict] = []
            start = 0
            while start < self.max_records:
                response = await _request_with_retry(
                    client,
                    "POST",
                    _YLSY_AJAX_URL,
                    data=self._form(start),
                )
                payload = response.json()
                if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                    raise RuntimeError(f"YLSY duyuru API beklenmeyen cevap: {payload!r}")
                page = payload["data"]
                rows.extend(page)
                try:
                    total = int(payload.get("recordsFiltered") or payload.get("recordsTotal"))
                except (TypeError, ValueError):
                    total = len(rows)
                if not page or len(rows) >= total:
                    break
                start += len(page)

            rss_response = await _request_with_retry(
                client,
                "GET",
                _YLSY_RSS_URL,
                headers={"Accept": "application/rss+xml, application/xml, text/xml"},
            )
            items = self.parse_rows(rows)
            known_titles = {_norm(item.title) for item in items}
            items.extend(
                item for item in self.parse_rss(rss_response.content) if _norm(item.title) not in known_titles
            )
            items.extend(await self._guide_items(client, items))
        return list({item.external_id: item for item in items}.values())


class YokAnnouncementSource(AnnouncementSource):
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
            items.append(
                RawItem(
                    external_id=hashlib.sha256(url.encode()).hexdigest(),
                    title=title,
                    url=url,
                    published_at=published_at,
                    extra={"organization": "YÖK", "kind": self.kind},
                )
            )
        return list({item.external_id: item for item in items}.values())


SOURCES = [
    AnnouncementSource(
        "osym",
        "https://www.osym.gov.tr/Duyurular/Index",
        ("ales", "yökdil", "yabancı dil", "sınav"),
        "exam",
    ),
    YlsySource(
        "ylsy",
        "https://yyegm.meb.gov.tr/www/duyurular/kategori/2",
        _YLSY_TERMS,
        "scholarship",
    ),
    YokAnnouncementSource(),
]
