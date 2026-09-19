"""Arka plan otomasyonu: hangi modul DIS KAYNAGA cikabilir.

`modules.disabled` bir ARAYUZ kararidir: rotayi, widget'i ve komutu gizler.
Arka plan otomasyonu BASKA bir sorudur: modul gorunurken de "arka planda
guncellenmesin" denebilmelidir. Ikisi ayni anahtara baglanirsa, kullanici bir
modulu gizlediginde worker'in ona hala erismesi tutarsiz kalir; tersi de
yanlis olurdu (gorunurluk = ag trafigi degildir).

Model:

  Göster               -> `modules.disabled`      (mevcut; arayuz)
  Arka planda güncelle -> `automation.<domain>.enabled`  (bu modul)

Varsayilan ACIK: mevcut davranis korunur, kullanici kapatmadikca hicbir sey
degismez.

RSS istisnasi: RSS'in arka plan anahtari KENDI ARALIGIDIR
(`rss.interval_minutes = 0` -> yalniz manuel). Ayni davranisi iki ayara
baglamak kullaniciyi yanlis yere yonlendirir; bu yuzden `automation.rss.*`
diye ikinci bir anahtar YOK.

Manuel aksiyonlar (arayuzdeki "Yenile" / "Tumunu tazele" / POST uclari) bu
ayarlardan BAGIMSIZDIR: otomasyonu kapatmak elle yapilan isi yasaklamaz.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.system.models import Setting

#: Arka plan isi yapan domain'ler. RSS burada DEGIL (bkz. modul docstring).
DOMAINS: tuple[str, ...] = ("opportunity", "media", "calendar", "github")

#: Domain -> "arka planda guncelle" anahtari.
ENABLED_KEYS: dict[str, str] = {domain: f"automation.{domain}.enabled" for domain in DOMAINS}

#: Domain -> tur araligi ayari. Media KENDI mevcut ayarini kullanir
#: (`media.sync_interval_hours`); ikinci bir anahtar acmak ayni davranisi iki
#: yere baglar ve hangisinin kazandigini belirsizlestirirdi.
INTERVAL_KEYS: dict[str, str] = {
    "opportunity": "automation.opportunity.interval_minutes",
    "media": "media.sync_interval_hours",
    "calendar": "automation.calendar.interval_minutes",
    "github": "automation.github.interval_hours",
}

#: Araligi SAAT cinsinden saklayan domain'ler (okurken dakikaya cevrilir).
HOUR_DOMAINS: frozenset[str] = frozenset({"media", "github"})

#: Domain -> arka plan tur araligi varsayilani (mevcut worker davranisiyla ayni;
#: github SAAT cinsinden tutulur).
DEFAULT_INTERVALS: dict[str, int] = {"opportunity": 15, "media": 24, "calendar": 30, "github": 3}

#: Ayar anahtari -> varsayilan deger. `media` HARIC: kendi anahtari zaten
#: DEFAULTS'te tasiniyor, iki kaynak ayni seyi soylemesin.
INTERVAL_DEFAULTS: dict[str, int] = {
    INTERVAL_KEYS[domain]: value
    for domain, value in DEFAULT_INTERVALS.items()
    if domain != "media"
}

#: Hazir profiller: kullaniciya teknik scheduler degerleri yerine bunlar sunulur.
#: `None` -> o domain icin anahtara DOKUNMA.
PROFILES: dict[str, dict[str, Any]] = {
    "manual": {
        "automation.opportunity.enabled": False,
        "automation.media.enabled": False,
        "automation.calendar.enabled": False,
        "automation.github.enabled": False,
        "rss.interval_minutes": 0,
    },
    "balanced": {
        "automation.opportunity.enabled": True,
        "automation.media.enabled": True,
        "automation.calendar.enabled": True,
        "automation.github.enabled": True,
        "automation.opportunity.interval_minutes": 30,
        "automation.calendar.interval_minutes": 60,
        "automation.github.interval_hours": 3,
        "rss.interval_minutes": 60,
    },
    #: "active" mevcut (daha sik) davranisa yakin kalir.
    "active": {
        "automation.opportunity.enabled": True,
        "automation.media.enabled": True,
        "automation.calendar.enabled": True,
        "automation.github.enabled": True,
        "automation.opportunity.interval_minutes": 15,
        "automation.calendar.interval_minutes": 30,
        "automation.github.interval_hours": 3,
        "rss.interval_minutes": 30,
    },
}

PROFILE_KEY = "automation.profile"
DEFAULT_PROFILE = "balanced"


async def _value(session: AsyncSession, key: str) -> Any:
    row = await session.get(Setting, key)
    return row.value if row is not None else None


async def is_enabled(session: AsyncSession, domain: str) -> bool:
    """Domain icin arka plan otomasyonu acik mi? (varsayilan: acik)"""
    value = await _value(session, ENABLED_KEYS[domain])
    return True if not isinstance(value, bool) else value


async def interval_minutes(session: AsyncSession, domain: str) -> int:
    """Domain'in arka plan tur araligi DAKIKA cinsinden."""
    key = INTERVAL_KEYS[domain]
    value = await _value(session, key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        value = DEFAULT_INTERVALS[domain]
    return value * 60 if domain in HOUR_DOMAINS else value


async def is_due(
    session: AsyncSession, domain: str, last_run: datetime | None, *, now: datetime | None = None
) -> bool:
    """Domain turu zamani geldi mi? Kayit yoksa EVET (telafi edilir)."""
    if last_run is None:
        return True
    moment = now or datetime.now(UTC)
    return last_run <= moment - timedelta(minutes=await interval_minutes(session, domain))


async def active_domains(session: AsyncSession) -> dict[str, bool]:
    return {domain: await is_enabled(session, domain) for domain in DOMAINS}


async def set_profile(session: AsyncSession, profile: str) -> dict[str, Any]:
    """Profili uygula: ilgili ayarlari yaz. Commit ETMEZ (cagiran commit eder).

    Bilinmeyen profil adi ValueError verir; sessizce yok sayilmaz.
    """
    if profile not in PROFILES:
        raise ValueError("bilinmeyen profil")
    targets = PROFILES[profile]
    for key, value in {**targets, PROFILE_KEY: profile}.items():
        row = await session.get(Setting, key)
        if row is None:
            session.add(Setting(key=key, value=value))
        else:
            row.value = value
    return dict(targets)


async def snapshot(session: AsyncSession) -> dict[str, Any]:
    """Arayuz icin tek okuma: profil + domain ayarlari."""
    domains = {}
    for domain in DOMAINS:
        domains[domain] = {
            "enabled": await is_enabled(session, domain),
            "interval_minutes": await interval_minutes(session, domain),
        }
    return {
        "profile": await current_profile(session),
        "profiles": sorted(PROFILES),
        "domains": domains,
    }


async def current_profile(session: AsyncSession) -> str:
    value = await _value(session, PROFILE_KEY)
    return value if isinstance(value, str) and value in PROFILES else DEFAULT_PROFILE
