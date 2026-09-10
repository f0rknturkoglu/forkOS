"""Ayar varsayilanlari ve temel tip dogrulamasi -- TEK kaynak.

`GET /settings` varsayilanlari buradan alir, `PUT /settings/{key}` yazmadan
once `validate_setting()` ile kontrol eder. Arayuz her anahtari kendi
bileseniyle yazsa da backend son sozu soyler: bozuk bir istemci
`rss.retention_days`'e "abc" yazip worker'i sessizce olduramaz.

Dogrulanmayan anahtarlar SERBEST birakilir: burasi beyaz liste degil, bilinen
anahtarlarin sozlesmesidir. Yeni bir ayar eklerken tip kuralini da buraya yaz.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.modules.system.news import DEFAULT_SUBREDDITS

DEFAULTS: dict[str, Any] = {
    "modules.disabled": [],
    "today.widget_order": [],
    # Widget gizleme tercihi de modul sirasi gibi kalicidir (Faz 19).
    "today.widget_hidden": [],
    "today.auto_suggestions": True,
    "rss.retention_days": 90,
    "media.links": [],
    "media.sync_interval_hours": 24,
    "media.upcoming_days": 30,
    "media.tmdb_key": "",
    "media.google_books_key": "",
    "media.igdb_client_id": "",
    "media.igdb_client_secret": "",
    "opportunity.career_profile": {
        "current_location": "Ankara, Türkiye",
        "authorized_countries": ["Türkiye"],
        "willing_to_relocate": False,
    },
    "news.subreddits": list(DEFAULT_SUBREDDITS),
    #: Para birimi -> aylik harcama tavani ({"TRY": 30000}). Bos ise butce yok:
    #: arayuz toplam geliri hedef kabul eder.
    "finance.monthly_budget": {},
    "theme": "dark",
}

#: Kullanici tercihi DEGIL, sistemin kendi calisma durumu. "Ayarlari sifirla"
#: bunlara dokunmaz; silinirlerse worker sagligi ve elle senkron gecmisi kaybolur.
RUNTIME_SETTING_KEYS: frozenset[str] = frozenset({
    "worker.heartbeat",
    "system.manual_refresh",
})


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _is_career_profile(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if not isinstance(value.get("current_location", ""), str):
        return False
    if not _is_str_list(value.get("authorized_countries", [])):
        return False
    return isinstance(value.get("willing_to_relocate", False), bool)


def _is_budget(value: Any) -> bool:
    """{"TRY": 30000, "USD": 500} -- pozitif sayilar, 3 harfli kur kodu."""
    if not isinstance(value, dict):
        return False
    for currency, amount in value.items():
        if not isinstance(currency, str) or len(currency) != 3:
            return False
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
            return False
    return True


def _is_media_links(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, dict) and isinstance(item.get("name"), str) and isinstance(item.get("url"), str)
        for item in value
    )


#: anahtar -> (hata mesaji, dogrulayici). Mesaj kullaniciya arayuzde gorunur.
SETTING_VALIDATORS: dict[str, tuple[str, Callable[[Any], bool]]] = {
    "rss.retention_days": ("1 ile 3650 arasında tam sayı olmalı", lambda v: _is_int(v) and 1 <= v <= 3650),
    "today.auto_suggestions": ("true/false olmalı", lambda v: isinstance(v, bool)),
    "modules.disabled": ("modül kimliklerinden oluşan liste olmalı", _is_str_list),
    "today.widget_order": ("widget kimliklerinden oluşan liste olmalı", _is_str_list),
    "today.widget_hidden": ("widget kimliklerinden oluşan liste olmalı", _is_str_list),
    "news.subreddits": ("subreddit adlarından oluşan liste olmalı", _is_str_list),
    "media.links": ("{name, url} listesi olmalı", _is_media_links),
    "media.upcoming_days": ("0 ile 365 arasında tam sayı olmalı", lambda v: _is_int(v) and 0 <= v <= 365),
    "media.sync_interval_hours": ("1 ile 720 arasında tam sayı olmalı", lambda v: _is_int(v) and 1 <= v <= 720),
    "opportunity.career_profile": ("konum, ülke listesi ve relokasyon alanları eksik", _is_career_profile),
    "finance.monthly_budget": ("para birimi -> pozitif tutar eşlemesi olmalı", _is_budget),
    "backup.drive_folder_id": ("klasör kimliği metin olmalı", lambda v: isinstance(v, str)),
}


def validate_setting(key: str, value: Any) -> str | None:
    """Gecerliyse None, degilse Turkce hata mesaji."""
    rule = SETTING_VALIDATORS.get(key)
    if rule is None:
        return None
    message, is_valid = rule
    return None if is_valid(value) else message
