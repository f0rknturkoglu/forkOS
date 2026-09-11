"""Kamu kurumlarının YLSY / kamu bursu / kontenjan / sınav / başvuru duyuruları.

Yetki sırası (AGENTS.md ve ürün kararı):

* **Kanonik kaynak** MEB/YYEGM'dir (``announcements.YlsySource``, id ``ylsy``);
  başvuru takvimi ve kontenjanın tek doğrusu oradadır. ``canonical=True``.
* **Buradaki kurum siteleri** erken sinyal veren ikincil kaynaklardır:
  ``official=True`` ama ``canonical=False``. Aynı duyuru hem kurumda hem
  YYEGM'de çıkarsa ingest URL/başlık üzerinden tekilleştirir.
* **Agregatörler** (örn. memurlar.net) resmî kaynak değildir: ``official=False``
  ve ``source_class="slow_optin"``; yenileme sıralamasında en sona düşer.

Doğrulanmış URL'ler (2026-09-11 canlı smoke, en az bir satır ayrıştırıldı):
``tua``, ``tenmak``, ``tpao``, ``botas``, ``tarim-sarem``, ``dsi``, ``memurlar``.
**En-iyi-çaba** (JS kabuğu veya görsel-only liste; canlı smoke'ta 0 satır):
``tuseb``, ``ogm``, ``tkgm``, ``enerji``, ``mta``, ``mapeg``. En-iyi-çaba
adaptörler bozuk veya değişmiş markup'ta HATA FIRLATMAZ: ``[]`` döner, koşum
``empty`` yazılır ve üst üste 3 boş koşumda Kural 6 alarmı devreye girer.

Ağ erişimi olmayan ortamda (ör. test) `parse_listing` saf fonksiyondur; fixture
testleri gerçek fetch ile aynı yolu kullanır.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

from app.sources.announcements import (
    AnnouncementSource,
    _norm,
    _request_with_retry,
    anchor_title,
    announcement_container,
    announcement_context,
    announcement_payload,
    announcement_stage,
    announcement_urls,
    dedupe_announcement_items,
    link_corrections,
    parse_announcement_dates,
    parse_turkish_heading_date,
)
from app.sources.base import RawItem

#: YLSY başvuru/kontenjan bilgisinin kanonik merkezî kaynağı.
CANONICAL_SOURCE_ID = "ylsy"

_USER_AGENT = "forkOS/0.1 local announcement monitor"

#: Kurum duyurularında aranan içerik kelimeleri. "duyuru"/"ilan" bilerek yok:
#: menü bağlantıları da bu kelimeleri taşır ve gürültü üretir.
_COMMON_KEYWORDS: tuple[str, ...] = (
    "başvuru",
    "burs",
    "kontenjan",
    "sınav",
    "alım",
    "personel",
    "destek",
    "staj",
    "öğrenci",
    "yüksek lisans",
    "doktora",
    "tercih",
    "çağrı",
)


_CTA_LABEL = re.compile(r"^(online\s+)?basvuru(\s+islemleri)?$")


def is_document_link(title: str, url: str) -> bool:
    """Kılavuz/PDF ya da "Online Başvuru" gibi CTA bağlantısı mı?

    Bunlar duyuru satırı değildir; kabın içinden kılavuz/başvuru URL'si olarak
    zaten çıkarılır.
    """
    label = _norm(title)
    if url.split("?", 1)[0].lower().endswith(".pdf"):
        return True
    if "kilavuz" in label:
        return True
    return _CTA_LABEL.match(label) is not None


@dataclass(frozen=True)
class InstitutionSpec:
    """Bir kurum adaptörünün veri tanımı (kod değil, yapılandırma)."""

    id: str
    name: str
    url: str
    detail_pattern: str
    keywords: tuple[str, ...] = _COMMON_KEYWORDS
    interval_minutes: int = 1440
    source_class: str = "normal"
    kind: str = "announcement"
    official: bool = True
    canonical: bool = False
    verified: bool = False
    embedded_json: bool = False
    note: str = ""


class InstitutionAnnouncementSource(AnnouncementSource):
    """Liste sayfasındaki duyuru bağlantılarını ortak kurallarla ayrıştırır.

    Her kurumun "parser fonksiyonu" bu sınıfın ``parse_listing`` metodudur;
    kuruma özgü davranış ``InstitutionSpec`` alanlarıyla verilir:

    * ``keywords`` — başlık filtresi,
    * ``detail_pattern`` — yalnızca gerçek duyuru URL'lerini kabul eden regex
      (menü/kategori bağlantılarını eler),
    * ``embedded_json`` — JS kabuğu sayfalarda ``__NEXT_DATA__`` yedeği.

    Markup farklıysa alt sınıf ``parse_listing``/``_item_from_anchor``ı ezer.
    """

    def __init__(self, spec: InstitutionSpec, extra_keywords: tuple[str, ...] = ()) -> None:
        keywords = tuple(dict.fromkeys((*_COMMON_KEYWORDS, *spec.keywords)))
        super().__init__(spec.id, spec.url, keywords, spec.kind)
        self.spec = spec
        self.extra_keywords = tuple(extra_keywords)
        self.interval_minutes = spec.interval_minutes
        self.source_class = spec.source_class
        self.official = spec.official
        self.canonical = spec.canonical
        self._detail = re.compile(spec.detail_pattern) if spec.detail_pattern else None

    # ── Ağ yolu: ikincil kaynak, asla hata fırlatmaz ────────────────────
    async def fetch(self) -> list[RawItem]:
        try:
            async with httpx.AsyncClient(
                timeout=25, follow_redirects=True, headers={"User-Agent": _USER_AGENT}
            ) as client:
                response = await _request_with_retry(
                    client, "GET", self.url, headers={"Accept": "text/html"}
                )
        except Exception:  # noqa: BLE001 - ikincil kaynak: boş koşum + Kural 6 alarmı
            return []
        return self.parse_listing(response.text, base_url=str(response.url))

    # ── Ayrıştırma yolu ───────────────────────────────────────────────
    def parse_listing(
        self, body: str, *, base_url: str, now: datetime | None = None
    ) -> list[RawItem]:
        """Bozuk/değişmiş markup'ta ``[]`` döner; asla yükseltmez."""
        try:
            items = list(self._link_items(body, base_url, now))
            if self.spec.embedded_json:
                items.extend(self._embedded_json_items(body, base_url, now))
            return link_corrections(dedupe_announcement_items(items))
        except Exception:  # noqa: BLE001 - beklenmeyen ağaç/şema: sessiz boş
            return []

    def _link_items(self, body: str, base_url: str, now: datetime | None):
        for anchor in HTMLParser(body).css("a"):
            item = self._item_from_anchor(anchor, base_url, now)
            if item is not None:
                yield item

    def _item_from_anchor(
        self, anchor, base_url: str, now: datetime | None
    ) -> RawItem | None:
        href = anchor.attributes.get("href")
        title = anchor_title(anchor)
        if not href or href.startswith(("mailto:", "javascript:", "#")) or len(title) < 8:
            return None
        url = urljoin(base_url, href)
        if self._detail is not None and not self._detail.search(url):
            return None
        if is_document_link(title, url):
            return None
        normalized = _norm(title)
        matched = [
            keyword
            for keyword in (*self.keywords, *self.extra_keywords)
            if _norm(keyword) in normalized
        ]
        if not matched:
            return None
        return self._build_item(title=title, url=url, anchor=anchor, base_url=base_url, now=now, matched=matched)

    def _build_item(
        self,
        *,
        title: str,
        url: str,
        anchor,
        base_url: str,
        now: datetime | None,
        matched: list[str],
    ) -> RawItem:
        context = announcement_context(anchor, title) if anchor is not None else title
        dates = parse_announcement_dates(f"{title}. {context}", now=now)
        stage = announcement_stage(title)
        container = announcement_container(anchor, title) if anchor is not None else None
        guide_url, apply_url = announcement_urls(container, base_url, skip_href=url)
        return RawItem(
            external_id=hashlib.sha256(url.encode()).hexdigest(),
            title=title,
            url=url,
            summary=context if context != title else None,
            published_at=parse_turkish_heading_date(title) or dates.get("published_at"),
            extra={
                "organization": self.spec.name,
                "kind": self.kind,
                "category": f"{self.id}-{stage}",
                "channel": f"{self.id}-announcements",
                "source_url": self.spec.url,
                "verified": self.spec.verified,
                "announcement": announcement_payload(
                    official=self.official,
                    canonical=self.canonical,
                    stage=stage,
                    dates=dates,
                    guide_url=guide_url,
                    apply_url=apply_url,
                    profiles=list(dict.fromkeys([stage, *matched])),
                ),
            },
        )

    def _embedded_json_items(
        self, body: str, base_url: str, now: datetime | None
    ) -> list[RawItem]:
        """JS kabuğu sayfalarda (Next.js) gömülü JSON'dan bağlantı toplar."""
        tree = HTMLParser(body)
        node = tree.css_first("script#__NEXT_DATA__") or tree.css_first(
            'script[type="application/json"]'
        )
        if node is None:
            return []
        try:
            payload = json.loads(node.text() or "")
        except (ValueError, TypeError):
            return []
        items: list[RawItem] = []
        for title, link in list(_walk_json_links(payload))[:200]:
            if len(title) < 8:
                continue
            url = urljoin(base_url, link)
            if self._detail is not None and not self._detail.search(url):
                continue
            if is_document_link(title, url):
                continue
            matched = [
                keyword
                for keyword in (*self.keywords, *self.extra_keywords)
                if _norm(keyword) in _norm(title)
            ]
            if not matched:
                continue
            items.append(
                self._build_item(
                    title=title, url=url, anchor=None, base_url=base_url, now=now, matched=matched
                )
            )
        return items


def _walk_json_links(payload, *, depth: int = 0):
    """Gömülü JSON'da başlık+bağlantı çiftlerini toplar (en fazla 12 seviye)."""
    if depth > 12:
        return
    if isinstance(payload, dict):
        link = next(
            (
                payload.get(key)
                for key in ("slug", "url", "href", "link", "path")
                if isinstance(payload.get(key), str) and payload.get(key)
            ),
            None,
        )
        title = next(
            (
                payload.get(key)
                for key in ("title", "baslik", "name", "heading")
                if isinstance(payload.get(key), str) and payload.get(key)
            ),
            None,
        )
        if link and title:
            yield " ".join(title.split()), link
        for value in payload.values():
            yield from _walk_json_links(value, depth=depth + 1)
    elif isinstance(payload, list):
        for value in payload:
            yield from _walk_json_links(value, depth=depth + 1)


#: Kurum kataloğu. `verified` = liste sayfası sunucu HTML'inde gerçek duyuru
#: bağlantısı veriyor (2026-09'da doğrulandı). `note` neden en-iyi-çaba olduğunu
#: açıklar; doğrulanmamış kurumlar erken sinyal için yine de değerlidir.
SPECS: tuple[InstitutionSpec, ...] = (
    InstitutionSpec(
        id="tuseb",
        name="TÜSEB",
        url="https://www.tuseb.gov.tr/tr/duyurular",
        detail_pattern=r"duyuru|haber|\.pdf$",
        keywords=("burs", "destek", "başvuru", "çağrı", "kontenjan", "yüksek lisans", "doktora", "proje"),
        embedded_json=True,
        note="React kabuğu: sunucu HTML'inde duyuru bağlantısı sınırlı; __NEXT_DATA__ yedeği.",
    ),
    InstitutionSpec(
        id="tua",
        name="Türkiye Uzay Ajansı",
        url="https://tua.gov.tr/tr/duyurular",
        detail_pattern=r"tua\.gov\.tr/tr/duyurular/",
        keywords=("burs", "başvuru", "program", "staj", "kontenjan", "sınav", "çağrı"),
        verified=True,
    ),
    InstitutionSpec(
        id="ogm",
        name="Orman Genel Müdürlüğü",
        url="https://www.ogm.gov.tr/tr/duyurular",
        detail_pattern=r"ogm\.gov\.tr/.*duyuru",
        keywords=("alım", "sınav", "başvuru", "personel", "staj", "kontenjan", "burs"),
        note="SharePoint listesi; canlı smoke'ta 0 satır — duyuru satırları JS ile geliyor.",
    ),
    InstitutionSpec(
        id="dsi",
        name="Devlet Su İşleri",
        url="https://www.dsi.gov.tr/duyuru/duyuruListe",
        detail_pattern=r"/Duyuru/Detay/",
        keywords=("alım", "sınav", "başvuru", "personel", "staj", "burs", "kontenjan"),
        verified=True,
    ),
    InstitutionSpec(
        id="tkgm",
        name="Tapu ve Kadastro Genel Müdürlüğü",
        url="https://www.tkgm.gov.tr/duyurular",
        detail_pattern=r"tkgm\.gov\.tr/(duyuru|haber)",
        keywords=("alım", "sınav", "başvuru", "personel", "staj", "kontenjan", "burs"),
        embedded_json=True,
        note="Next.js kabuğu; veri gömülü JSON'da, sunucu HTML'i yetersiz.",
    ),
    InstitutionSpec(
        id="tarim-sarem",
        name="Tarım ve Orman Bakanlığı (SAREM)",
        url="https://www.tarimorman.gov.tr/HaberArsivi",
        detail_pattern=r"tarimorman\.gov\.tr/Haber/",
        keywords=("burs", "alım", "sınav", "başvuru", "personel", "destek", "proje", "staj"),
        verified=True,
    ),
    InstitutionSpec(
        id="enerji",
        name="Enerji ve Tabii Kaynaklar Bakanlığı",
        url="https://enerji.gov.tr/haberler",
        detail_pattern=r"enerji\.gov\.tr/(haber|duyuru)",
        keywords=("alım", "sınav", "başvuru", "personel", "destek", "burs", "staj"),
        note="Sunucu HTML'i çok ince (JS kabuğu); en-iyi-çaba.",
    ),
    InstitutionSpec(
        id="tenmak",
        name="TENMAK",
        url="https://www.tenmak.gov.tr/duyurular",
        detail_pattern=r"tenmak\.gov\.tr/duyurular/",
        keywords=("burs", "alım", "sınav", "başvuru", "personel", "destek", "proje", "kontenjan"),
        verified=True,
    ),
    InstitutionSpec(
        id="mta",
        name="Maden Tetkik ve Arama Genel Müdürlüğü",
        url="https://www.mta.gov.tr/v3.0/duyurular",
        detail_pattern=r"mta\.gov\.tr/.*(duyuru|belge)|\.pdf$",
        keywords=("alım", "sınav", "başvuru", "personel", "burs", "staj", "kontenjan"),
        verified=False,
        note="Liste sayfasında duyuru bağlantısı yok (PDF'ler ayrı sayfada); canlı smoke 0 satır.",
    ),
    InstitutionSpec(
        id="tpao",
        name="Türkiye Petrolleri A.O.",
        url="https://www.tpao.gov.tr/haberler",
        detail_pattern=r"tpao\.gov\.tr/haberler/",
        keywords=("alım", "sınav", "başvuru", "personel", "staj", "burs", "kontenjan"),
        verified=True,
    ),
    InstitutionSpec(
        id="botas",
        name="BOTAŞ",
        url="https://www.botas.gov.tr/Kategori/duyurular/2",
        detail_pattern=r"botas\.gov\.tr/Icerik/",
        keywords=("alım", "sınav", "başvuru", "personel", "staj", "burs", "kontenjan"),
        verified=True,
    ),
    InstitutionSpec(
        id="mapeg",
        name="Maden ve Petrol İşleri Genel Müdürlüğü",
        url="https://www.mapeg.gov.tr/duyurular",
        detail_pattern=r"mapeg\.gov\.tr/(duyuru|haber)",
        keywords=("alım", "sınav", "başvuru", "personel", "ihale", "burs"),
        note="Kök sertifika zinciri doğrulanamadı + JS kabuğu; yalnızca erken sinyal.",
    ),
    InstitutionSpec(
        id="memurlar",
        name="memurlar.net",
        url="https://www.memurlar.net/",
        detail_pattern=r"memurlar\.net/(haber|egitim|sinav|burs)/",
        keywords=("ylsy", "burs", "kontenjan", "sınav", "alım", "başvuru", "personel"),
        interval_minutes=2160,
        source_class="slow_optin",
        kind="announcement",
        official=False,
        canonical=False,
        verified=True,
        note="Agregatör: resmî kaynak değil (official=False), opt-in ve yavaş yenilenir.",
    ),
)


INSTITUTION_SOURCES: list[InstitutionAnnouncementSource] = [
    InstitutionAnnouncementSource(spec) for spec in SPECS
]
