"""Official Hermes runs API; no proxy, model overrides, tools or browser credentials."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import yaml
from fastapi import HTTPException

from app.config import settings
from app.modules.goal.studio_schemas import StudioStatus

MAX_RESPONSE = 128_000
LIMIT = asyncio.Semaphore(2)


def loopback(value, *, profile=False):
    url = urlsplit(value)
    if (
        url.scheme != "http"
        or url.hostname not in {"127.0.0.1", "::1"}
        or url.username
        or url.password
        or url.query
        or url.fragment
        or not url.port
        or (profile and url.path != "/p/forkos-goal-studio")
    ):
        raise ValueError("Hermes adresi sabit, loopback HTTP Goal Studio profiline ait olmalı")
    return value.rstrip("/")


def verified_profile():
    path = Path(settings.hermes_goal_profile_config)
    if not path.is_file() or path.stat().st_size > 32_000:
        raise ValueError("Ayrı Goal Studio profilinin salt okunur config.yaml dosyası gerekli")
    hooks = path.parent / "hooks"
    if hooks.exists() and any(item.is_file() for item in hooks.rglob("*")):
        raise ValueError("Goal Studio profili hook dosyası içeremez")
    jobs = path.parent / "cron" / "jobs.json"
    if jobs.exists():
        if jobs.stat().st_size > 32_000:
            raise ValueError("Goal Studio zamanlanmış görev dosyası geçersiz")
        content = json.loads(jobs.read_text())
        if not isinstance(content, dict) or content.get("jobs") != []:
            raise ValueError("Goal Studio profili zamanlanmış görev içeremez")
    config = yaml.safe_load(path.read_text())
    if not isinstance(config, dict) or config.get("platform_toolsets", {}).get("api_server") != []:
        raise ValueError("Goal Studio api_server araç listesi açıkça boş olmalı")
    if (
        config.get("mcp_servers")
        or config.get("plugins")
        or config.get("fallback_model")
        or config.get("custom_providers")
    ):
        raise ValueError("Goal Studio MCP/plugin/fallback sağlayıcı kabul etmez")
    if any(
        config.get("memory", {}).get(key) is not False
        for key in ("memory_enabled", "user_profile_enabled")
    ):
        raise ValueError("Goal Studio otomatik hafıza kapalı olmalı")
    if config.get("curator", {}).get("enabled") is not False:
        raise ValueError("Goal Studio otomatik skill curator kapalı olmalı")
    gateway = config.get("gateway", {})
    if gateway.get("multiplex_profiles"):
        raise ValueError("Goal Studio ayrı, tek profilli daemon gerektirir")
    api = config.get("platforms", {}).get("api_server", {})
    if api.get("extra", {}).get("host") != "127.0.0.1" or api.get("enabled") is not True:
        raise ValueError("Hermes API yalnız 127.0.0.1 üzerinde etkin olmalı")
    if config.get("auxiliary", {}).get("background_review", {}).get("enabled") is not False:
        raise ValueError("Goal Studio arka plan gözden geçirmesi kapalı olmalı")
    if config.get("context_engine", "default") != "default" or api.get("extra", {}).get(
        "model_routes"
    ):
        raise ValueError("Özel bağlam motoru veya model yönlendirmesi kabul edilmez")
    if api.get("extra", {}).get("cors_origins"):
        raise ValueError("Hermes tarayıcı CORS erişimi kapalı olmalı")
    model = config.get("model", {})
    if model.get("provider") != "custom" or not model.get("default"):
        raise ValueError("Goal Studio açık bir yerel custom model gerektirir")
    loopback(model.get("base_url", ""))
    return config


async def request(method, path, *, body=None, identity=None):
    base = loopback(settings.hermes_goal_base_url, profile=True)
    headers = {"Authorization": f"Bearer {settings.hermes_goal_api_key}"}
    if identity:
        headers["Idempotency-Key"] = identity
    try:
        async with (
            asyncio.timeout(8),
            LIMIT,
            httpx.AsyncClient(timeout=6, trust_env=False, follow_redirects=False) as client,
            client.stream(method, base + path, headers=headers, json=body) as response,
        ):
            if response.status_code == 401:
                raise HTTPException(503, "Hermes profil anahtarı doğrulanamadı")
            if response.status_code >= 300:
                raise HTTPException(
                    503, "Hermes isteği tamamlanamadı; mevcut koşuyu yeniden kontrol et"
                )
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > MAX_RESPONSE:
                    raise HTTPException(502, "Hermes yanıt sınırı aşıldı")
            return json.loads(content)
    except (httpx.HTTPError, TimeoutError, ValueError) as exc:
        raise HTTPException(503, "Hermes erişilemiyor veya yanıtı geçersiz") from exc


async def status():
    if not settings.hermes_goal_api_key or not settings.hermes_goal_profile_config:
        return StudioStatus(
            state="not_configured",
            message="Hermes Goal Studio profili yapılandırılmamış; manuel hedefler kullanılabilir.",
        )
    try:
        verified_profile()
        await request("GET", "/health")
        caps = await request("GET", "/v1/capabilities")
        features = caps.get("features", {})
        idem = features.get("runs_idempotency", {})
        if (
            caps.get("model") != "forkos-goal-studio"
            or not caps.get("auth", {}).get("required")
            or not all(
                features.get(k)
                for k in ("run_submission", "run_status", "run_events_sse", "run_stop")
            )
            or not idem.get("supported")
        ):
            raise ValueError(
                "Hermes sürümü profil kimliği/kimlik doğrulama/runs/idempotency sözleşmesini sağlamıyor"
            )
        tools = await request("GET", "/v1/toolsets")
        if not isinstance(tools.get("data"), list) or any(
            row.get("enabled") for row in tools["data"]
        ):
            raise ValueError("Çalışan Hermes API profili araçları kapatmamış")
        return StudioStatus(state="ready", message="Hermes hazır · araçsız yerel profil")
    except ValueError as exc:
        return StudioStatus(state="unsupported", message=str(exc))
    except (OSError, AttributeError, TypeError, yaml.YAMLError):
        return StudioStatus(
            state="unsupported", message="Hermes profil veya yetenek sözleşmesi geçersiz"
        )
    except HTTPException as exc:
        return StudioStatus(state="unavailable", message=str(exc.detail))


async def require_ready():
    result = await status()
    if result.state != "ready":
        raise HTTPException(503, result.message)


async def public_events(run_id):
    """Only final/public text and lifecycle states; never reasoning or raw tool arguments."""
    await require_ready()
    base = loopback(settings.hermes_goal_base_url, profile=True)
    try:
        async with (
            asyncio.timeout(25),
            LIMIT,
            httpx.AsyncClient(timeout=25, trust_env=False, follow_redirects=False) as client,
            client.stream(
                "GET",
                f"{base}/v1/runs/{run_id}/events",
                headers={"Authorization": f"Bearer {settings.hermes_goal_api_key}"},
            ) as response,
        ):
            if response.status_code != 200:
                return
            size = 0
            event = ""
            async for line in response.aiter_lines():
                size += len(line)
                if size > MAX_RESPONSE:
                    return
                if line.startswith("event:"):
                    event = line[6:].strip()
                if not line.startswith("data:"):
                    continue
                try:
                    data = json.loads(line[5:])
                except ValueError:
                    continue
                name = data.get("type") or event
                if name == "message.delta":
                    delta = data.get("delta", "")
                    if isinstance(delta, str):
                        yield "data: " + json.dumps({"text": delta[:4000]}) + "\n\n"
                elif name in {
                    "run.completed",
                    "run.failed",
                    "run.cancelled",
                    "run.interrupted",
                }:
                    yield 'data: {"reconcile": true}\n\n'
                    return
                elif name and name.startswith("tool."):
                    yield 'data: {"blocked_tool_event": true}\n\n'
                    return
    except (httpx.HTTPError, TimeoutError):
        yield 'data: {"reconcile": true}\n\n'
