from __future__ import annotations

import asyncio
import hashlib
import html
import unicodedata
from datetime import UTC, datetime
from urllib.parse import urljoin

import httpx
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


class YlsySource(AnnouncementSource):
    async def fetch(self) -> list[RawItem]:
        headers = {
            "User-Agent": "forkOS/0.1 local announcement monitor",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.url,
        }
        form = {
            "kategori": "2",
            "dil": "tr",
            "draw": "1",
            "start": "0",
            "length": "100",
            "order[0][column]": "2",
            "order[0][dir]": "desc",
            "search[value]": "",
            "columns[0][data]": "ISLEMSAAT",
            "columns[1][data]": "BASLIK",
            "columns[2][data]": "SIRAID",
        }
        async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=headers) as client:
            await _request_with_retry(client, "GET", self.url)
            response = await _request_with_retry(
                client,
                "POST",
                "https://yyegm.meb.gov.tr/www/icerik_listele_ajax.php",
                data=form,
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError(f"YLSY duyuru API beklenmeyen cevap: {payload!r}")
        items: list[RawItem] = []
        for row in payload.get("data", []):
            title = " ".join(html.unescape(row.get("BASLIK", "")).split())
            if not any(_norm(keyword) in _norm(title) for keyword in self.keywords):
                continue
            url = urljoin(self.url, row["LINK"])
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
                    extra={"organization": "YLSY", "kind": self.kind},
                )
            )
        return items


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
            anchor = next((node for node in card.css("a") if node.attributes.get("href")), None)
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
        ("ylsy", "burs", "lisansüstü"),
        "scholarship",
    ),
    YokAnnouncementSource(),
]
