"""Ajan (MCP) durumu yükü — DB'siz, doğrudan test edilebilir yük üreticileri.

Rota katmanı bilerek İNCE tutulur: `/api/agent/status` yalnızca buradaki
fonksiyonları çağırır. Hiçbir şey yazılmaz, veritabanına dokunulmaz; dış ağ
çağrısı YOKTUR. Tek olası ağ trafiği, H4 açıkken atılan SINIRLI loopback
Ollama sağlık probudur (GET /api/tags — çıkarım DEĞİL) ve en fazla
`DIAGNOSTIC_TIMEOUT_SECONDS` kadar sürer.

Sızıntı kuralları: yanıt gövdesine sır, mutlak dosya yolu, ham istisna metni,
sağlayıcı URL'si veya model çıktısı KONMAZ. `detail` yalnızca sabit, sınırlı
Türkçe metinlerden gelir.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.config import settings as app_settings
from app.integrations.agent import capabilities
from app.integrations.local_cognition.models import SLOT_PRIORITY
from app.integrations.local_cognition.ollama import OllamaProvider, validate_loopback_base_url
from app.integrations.local_cognition.policy import ModelHealth, ModelProfile, build_profiles
from app.integrations.local_cognition.provider import LocalModelProvider, ProviderError

#: Teşhis probu kısa tutulur: ayar ekranı asla bloklanmamalı.
DIAGNOSTIC_TIMEOUT_SECONDS = 2.5

#: Arayüz her zaman loopback host'una yazılır; Host başlığına GÜVENİLMEZ.
LOOPBACK_HOST = "127.0.0.1"

#: `request.scope["server"]` yoksa varsayılan port (tek kullanıcılı local kurulum).
DEFAULT_PORT = 8787

ProviderFactory = Callable[[], LocalModelProvider]

#: `detail` metinleri: sabit, sınırlı, sırsız.
_DETAIL_NOT_CONFIGURED = "Yerel model kimliği yapılandırılmadı (H4_SMALL_MODEL / H4_MEDIUM_MODEL boş)."
_DETAIL_NOT_LOOPBACK = "Yerel model adresi loopback değil; H4 yalnızca loopback kabul eder."
_DETAIL_UNREACHABLE = "Yerel model sağlayıcısına ulaşılamadı."
_DETAIL_MODEL_MISSING = "Yapılandırılmış model kurulu değil: {slots}."


def endpoint_url(server: object = None) -> str:
    """Gerçek bağlanma portundan loopback MCP adresi.

    `server`, ASGI `scope["server"]` demetidir (`(host, port)`). Host başlığı
    KULLANILMAZ; host her zaman 127.0.0.1'e sabitlenir.
    """
    port = DEFAULT_PORT
    if isinstance(server, (tuple, list)) and len(server) >= 2:
        try:
            port = int(server[1])
        except (TypeError, ValueError):
            port = DEFAULT_PORT
    return f"http://{LOOPBACK_HOST}:{port}{capabilities.MCP_PATH}"


def brain_block(server: object = None) -> dict[str, Any]:
    """H0–H7 yetenek haritası: sunucu kimliği, adres, taşıma ve aile sayıları."""
    return {
        "server_name": capabilities.SERVER_NAME,
        "endpoint": endpoint_url(server),
        "transport": capabilities.TRANSPORT,
        "loopback_only": capabilities.LOOPBACK_ONLY,
        "tool_count": capabilities.tool_count(),
        "families": [
            {
                "id": family.id,
                "label": family.label,
                "summary": family.summary,
                "tool_count": len(family.tools),
            }
            for family in capabilities.FAMILIES
        ],
    }


def endpoint_class(base_url: str) -> str:
    """Yapılandırılmış sağlayıcı adresinin sınıfı: `loopback` ya da `invalid`.

    Sınıflandırma SAF'tır (yalnızca dize doğrulaması): prob atmaz, ağa çıkmaz.
    `invalid` hâli yapılandırmadaki güvenlik ihlalini arayüzde GÖRÜNÜR kılar;
    aksi hâlde uzak bir adres "loopback" gibi okunurdu.
    """
    try:
        validate_loopback_base_url(base_url)
    except ProviderError:
        return "invalid"
    return "loopback"


def _slot_payload(profile: ModelProfile, health: ModelHealth | None) -> dict[str, bool]:
    return {
        "configured": profile.configured,
        "available": bool(health.model_available) if health is not None else False,
    }


async def _probe_slots(
    provider: LocalModelProvider, profiles: dict[str, ModelProfile]
) -> dict[str, ModelHealth]:
    """Yapılandırılmış slotlar için sağlık anlık görüntüsü. Model İNDİRİLMEZ."""
    snapshot: dict[str, ModelHealth] = {}
    for slot in SLOT_PRIORITY:
        profile = profiles[slot]
        if not profile.configured:
            continue
        snapshot[slot] = await provider.health(profile.model_id)
    return snapshot


def _slot_display_name(slot: str) -> str:
    return "small" if slot == "local-small" else "medium"


async def local_cognition_block(
    settings_obj: object | None = None,
    *,
    provider_factory: ProviderFactory | None = None,
) -> dict[str, Any]:
    """H4 yerel biliş durumu.

    Durum kümesi: disabled / not_configured / provider_unreachable /
    model_missing / ready. H4 KAPALIYKEN prob atılmaz ve `reachable` null kalır.
    """
    resolved = app_settings if settings_obj is None else settings_obj
    profiles = build_profiles(resolved)
    enabled = bool(getattr(resolved, "h4_enabled", False))
    base_url = str(getattr(resolved, "h4_ollama_base_url", "") or "")

    payload: dict[str, Any] = {
        "enabled": enabled,
        "provider": "ollama",
        "endpoint_class": endpoint_class(base_url),
        "configured": any(profile.configured for profile in profiles.values()),
        "reachable": None,
        "state": "disabled",
        "small": _slot_payload(profiles["local-small"], None),
        "medium": _slot_payload(profiles["local-medium"], None),
        "detail": None,
    }

    if not enabled:
        return payload

    if not payload["configured"]:
        payload["state"] = "not_configured"
        payload["detail"] = _DETAIL_NOT_CONFIGURED
        return payload

    # Loopback kuralı SAĞLAYICIDAN BAĞIMSIZ dayatılır: enjekte edilmiş bir
    # sağlayıcı bile yapılandırılmış adres loopback değilse çağrılmaz (§47).
    if payload["endpoint_class"] == "invalid":
        payload["reachable"] = False
        payload["state"] = "provider_unreachable"
        payload["detail"] = _DETAIL_NOT_LOOPBACK
        return payload

    try:
        if provider_factory is not None:
            provider = provider_factory()
        else:
            provider = OllamaProvider(base_url, timeout_seconds=DIAGNOSTIC_TIMEOUT_SECONDS)
        health = await _probe_slots(provider, profiles)
    except ProviderError:
        payload["reachable"] = False
        payload["state"] = "provider_unreachable"
        payload["detail"] = _DETAIL_UNREACHABLE
        return payload

    payload["small"] = _slot_payload(profiles["local-small"], health.get("local-small"))
    payload["medium"] = _slot_payload(profiles["local-medium"], health.get("local-medium"))

    if any(not entry.provider_reachable for entry in health.values()):
        payload["reachable"] = False
        payload["state"] = "provider_unreachable"
        payload["detail"] = _DETAIL_UNREACHABLE
        return payload

    payload["reachable"] = True
    missing = [
        _slot_display_name(slot)
        for slot, entry in health.items()
        if not entry.model_available
    ]
    if missing:
        payload["state"] = "model_missing"
        payload["detail"] = _DETAIL_MODEL_MISSING.format(slots=", ".join(sorted(missing)))
        return payload

    payload["state"] = "ready"
    return payload


async def agent_status_payload(
    server: object = None,
    settings_obj: object | None = None,
    *,
    provider_factory: ProviderFactory | None = None,
) -> dict[str, Any]:
    """`GET /api/agent/status` gövdesi: yetenek haritası + yerel biliş durumu."""
    return {
        "brain": brain_block(server),
        "local_cognition": await local_cognition_block(
            settings_obj, provider_factory=provider_factory
        ),
    }


__all__ = [
    "DEFAULT_PORT",
    "DIAGNOSTIC_TIMEOUT_SECONDS",
    "LOOPBACK_HOST",
    "ProviderFactory",
    "agent_status_payload",
    "brain_block",
    "endpoint_class",
    "endpoint_url",
    "local_cognition_block",
]
