"""SourceAdapter protokolu.

Job Hunter, OSYM, YLSY, MSc scraper'lari ILERIDE bu arayuze yazilacak.
Boylece worker'i degistirmeden yeni kaynak eklenebilir ve gerekirse
tum scraper katmani bir VPS'e tasinabilir.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from enum import StrEnum
from typing import Protocol


@dataclass
class RawItem:
    external_id: str                    # dedup anahtari
    title: str
    url: str | None = None
    summary: str | None = None
    published_at: datetime | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class FetchOutcome:
    """Tek bir kaynak kosusunun sonucu.

    `partial` kaynagin *calistigini* ama hedefledigi kapsamin tamamini
    tarayamadigini soyler: sayfalama yarida kaldi, yardimci feed/PDF bozuldu,
    bazi istekler zaman asimina dustu. Kayitlar gecerli oldugu icin ingest
    edilirler; ama kapanma taramasi (sweep) YAPILMAZ -- eksik gorunen kayit
    gercekte hala yayinda olabilir.

    `detail` kullaniciya gosterilecek kisa bir aciklamadir (hata sinifi +
    hangi parca bozuldu). Bos ise kosum `complete` sayilir.
    """

    items: list[RawItem] = field(default_factory=list)
    partial: bool = False
    detail: str = ""


def normalize_fetch(raw: list[RawItem] | FetchOutcome | None) -> FetchOutcome:
    """Adapter cevabini tek bir sozlesmeye indirger.

    Eski adaptorler `list[RawItem]` dondurur ve bu tam bir kosum sayilir; yeni
    adaptorler `FetchOutcome` dondurerek kapsam eksikligini bildirir. Worker
    yalnizca bu fonksiyonun ciktisini gorur.
    """
    if raw is None:
        return FetchOutcome()
    if isinstance(raw, FetchOutcome):
        return raw
    return FetchOutcome(items=list(raw))


# ---------------------------------------------------------------------------
# Kaynak sinifi (refresh sirasi, timeout ve kapanma bekleme suresi)
# ---------------------------------------------------------------------------


class SourceClass(StrEnum):
    """Bir kaynagin yenileme onceligi ve maliyeti.

    critical   -- resmi devlet kaynaklari ve hizli ATS API'leri. Ucuz ve
                  yuksek sinyal; genel yenilemede once kosar.
    normal     -- diger is panolari.
    slow_optin -- yavas ve/veya kullanici acikca secmeden kosmayan kaynaklar
                  (eures, linkedin). Genel yenilemeye ASLA girmez.
    """

    CRITICAL = "critical"
    NORMAL = "normal"
    SLOW_OPTIN = "slow_optin"


#: Resmi/kamusal kaynaklar -- her zaman critical.
CRITICAL_SOURCE_IDS = frozenset({"osym", "ylsy", "yok-msc", "yok"})
#: Hizli, anahtarsiz ATS JSON API'leri -- her zaman critical.
CRITICAL_ATS = frozenset(
    {"greenhouse", "lever", "ashby", "recruitee", "smartrecruiters", "workable"}
)
#: Yavas ve/veya opt-in kaynaklar -- genel yenilemeden HARIC.
SLOW_OPTIN_SOURCE_IDS = frozenset({"jobhunter:eures", "jobhunter:linkedin"})

#: Sinif basina sert kosum tavani (saniye). Asan kaynak iptal edilir.
DEFAULT_TIMEOUT_SECONDS: dict[str, float] = {
    "critical": 60.0,
    "normal": 180.0,
    "slow_optin": 900.0,
}
#: UI tahmini icin sinif basina kaba sure (saniye).
DEFAULT_ESTIMATED_SECONDS: dict[str, int] = {
    "critical": 15,
    "normal": 55,
    "slow_optin": 480,
}


def source_id_of(source: object) -> str:
    """Adapter ya da ham id'den kaynak kimligini cikar."""
    if isinstance(source, str):
        return source
    return str(getattr(source, "id", source))


def ats_platform_of(source: object) -> str | None:
    """`jobhunter:<ats>:<token>` id'sinden ATS platformunu cikar."""
    parts = source_id_of(source).split(":")
    if len(parts) >= 3 and parts[0] == "jobhunter":
        return parts[1]
    return None


def source_class(source: object) -> SourceClass:
    """Kaynagin sinifi.

    Sozlesmede adi gecen kimlikler (osym/ylsy/yok-msc ve hizli ATS'ler;
    eures/linkedin) HER ZAMAN kendi sinifindadir -- genel bir adaptor
    varsayilani (or. AnnouncementSource.source_class = "normal") onlari
    yanlislikla dusuremez. Diger kaynaklarda adapter'in `source_class`
    bildirimi kazanir; yoksa id'den turetilir.
    """
    sid = source_id_of(source)
    if getattr(source, "opt_in", False) or getattr(source, "slow_optin", False):
        return SourceClass.SLOW_OPTIN
    if sid in SLOW_OPTIN_SOURCE_IDS:
        return SourceClass.SLOW_OPTIN
    if sid in CRITICAL_SOURCE_IDS or ats_platform_of(sid) in CRITICAL_ATS:
        return SourceClass.CRITICAL
    declared = getattr(source, "source_class", None)
    if declared:
        try:
            return SourceClass(str(declared))
        except ValueError:
            pass
    return SourceClass.NORMAL


def is_opt_in(source: object) -> bool:
    """Genel yenilemeye girmemesi gereken kaynak mi?"""
    return source_class(source) is SourceClass.SLOW_OPTIN


def source_timeout_seconds(source: object) -> float:
    """Sert kosum tavani. Adapter `timeout_seconds` ile degistirebilir."""
    declared = getattr(source, "timeout_seconds", None)
    if isinstance(declared, (int, float)) and declared > 0:
        return float(declared)
    return DEFAULT_TIMEOUT_SECONDS[source_class(source).value]


def source_estimated_seconds(source: object) -> int:
    """Kullanicaya gosterilecek kaba sure tahmini."""
    declared = getattr(source, "estimated_seconds", None)
    if isinstance(declared, (int, float)) and declared > 0:
        return int(declared)
    return DEFAULT_ESTIMATED_SECONDS[source_class(source).value]


CLASS_ORDER: dict[str, int] = {
    SourceClass.CRITICAL.value: 0,
    SourceClass.NORMAL.value: 1,
    SourceClass.SLOW_OPTIN.value: 2,
}


def order_by_class(sources: list) -> list:
    """Critical -> normal -> slow_optin; sinif icinde verilen sira korunur."""
    return sorted(sources, key=lambda source: CLASS_ORDER[source_class(source).value])


def is_general_refresh_source(source: object) -> bool:
    """Genel baslik yenilemesine giren kaynak mi (opt-in haric)?"""
    return not is_opt_in(source)


# ---------------------------------------------------------------------------
# Retry-After
# ---------------------------------------------------------------------------


def retry_after_seconds(value: str | None, *, now: datetime | None = None) -> int | None:
    """Retry-After basligini saniyeye cevir; iki bicimi de destekler.

    Oncelik tamsayi saniye bicimindedir (`Retry-After: 120`). Nadir olan
    HTTP-date bicimi (`Retry-After: Wed, 21 Oct 2015 07:28:00 GMT`) de
    desteklenir. Gecersiz/tanimsizsa None doner; cagiran taraf tavan uygular.
    """
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return max(0, int(text))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    moment = now or datetime.now(UTC)
    return max(0, int((when - moment).total_seconds()))


class SourceAdapter(Protocol):
    id: str
    interval_minutes: int

    #: Opsiyonel: "critical" | "normal" | "slow_optin". Yoksa id'den turetilir.
    source_class: str
    #: Opsiyonel: sert kosum tavani (saniye).
    timeout_seconds: float

    async def fetch(self) -> list[RawItem] | FetchOutcome:
        """Kaynagi cek.

        Hata firlatabilir -- worker `source_run`'a `error` yazar.
        Kapsam eksikliginde firlatma yerine `FetchOutcome(partial=True, detail=...)`
        dondur: kaynak calisiyor ama tam taramamistir, kosum `partial` olur.
        """
        ...
