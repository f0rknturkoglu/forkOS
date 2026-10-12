"""Validated Hermes 0.21.6 single-profile runs API; OAuth remains owned by Hermes."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx
import yaml
from fastapi import HTTPException

from app.config import settings
from app.modules.goal import studio_policy
from app.modules.goal.studio_schemas import StudioStatus

MAX_RESPONSE = 128_000
MAX_REQUEST = 128_000
LIMIT = asyncio.Semaphore(2)
SUPPORTED_VERSIONS = {"0.21.6"}
MODEL_PORTS = {11434, 18434, 18435}


def loopback(value, *, profile=False):
    url = urlsplit(value)
    allowed = {"127.0.0.1", "::1"}
    if profile and settings.hermes_goal_topology == "host_bridge":
        allowed = {"host.docker.internal"}
    if (
        url.scheme != "http"
        or url.hostname not in allowed
        or url.username
        or url.password
        or url.query
        or url.fragment
        or not url.port
        or (profile and (url.path not in {"", "/"} or url.port != 8643))
    ):
        raise ValueError(
            "Hermes adresi doğrulanmış tek-profilli loopback/host köprüsü adresi olmalı; /p/ prefix desteklenmez"
        )
    return value.rstrip("/")


def verified_profile():
    path = Path(settings.hermes_goal_profile_config)
    if (
        not path.is_file()
        or path.stat().st_size > 32_000
        or path.resolve() == Path.home() / ".hermes/config.yaml"
    ):
        raise ValueError("Ayrı Goal Studio profilinin salt okunur config.yaml dosyası gerekli")
    # Hermes 0.21.6 seeds its essential reference skill even with --no-skills.
    # agent/system_prompt.py omits the skill index when skills tools are absent;
    # the live effective-toolset check below enforces zero skill execution as well.
    for dirname in ("hooks", "plugins"):
        folder = path.parent / dirname
        if folder.is_symlink() or (
            folder.exists() and any(p.is_file() or p.is_symlink() for p in folder.rglob("*"))
        ):
            raise ValueError(f"Goal Studio profili {dirname} dosyası içeremez")
    jobs = path.parent / "cron/jobs.json"
    if jobs.exists():
        if jobs.stat().st_size > 32_000:
            raise ValueError("Goal Studio zamanlanmış görev dosyası geçersiz")
        content = json.loads(jobs.read_text())
        if not isinstance(content, dict) or content.get("jobs") != []:
            raise ValueError("Goal Studio profili zamanlanmış görev içeremez")
    config = yaml.safe_load(path.read_text())
    if not isinstance(config, dict) or config.get("platform_toolsets", {}).get("api_server") != []:
        raise ValueError("Goal Studio api_server araç listesi açıkça boş olmalı")
    if set(config) - {
        "model",
        "auth",
        "platform_toolsets",
        "mcp_servers",
        "plugins",
        "fallback_model",
        "memory",
        "auxiliary",
        "curator",
        "context_engine",
        "agent",
        "platforms",
        "gateway",
    }:
        raise ValueError("Goal Studio profilinde doğrulanmamış ayar alanları var")
    if set(config.get("auth", {})) != {"adopt_external_logins"}:
        raise ValueError("Goal Studio auth politikası yalnız dış login devralma ayarı içerir")
    if config.get("agent") != {"max_iterations": 3}:
        raise ValueError("Goal Studio agent ayarı üç araçsız iterasyonla sınırlı")
    if any(
        config.get(key)
        for key in (
            "mcp_servers",
            "plugins",
            "providers",
            "custom_providers",
            "fallback_model",
            "fallback_models",
            "fallback_providers",
            "hooks",
            "toolsets",
        )
    ):
        raise ValueError("Goal Studio MCP/plugin/hook/fallback veya özel sağlayıcı kabul etmez")
    if any(
        config.get("memory", {}).get(key) is not False
        for key in ("memory_enabled", "user_profile_enabled")
    ):
        raise ValueError("Goal Studio otomatik hafıza kapalı olmalı")
    if config.get("auth", {}).get("adopt_external_logins") is not False:
        raise ValueError("Goal Studio başka profil/Codex credential'larını devralamaz")
    if config.get("curator", {}).get("enabled") is not False:
        raise ValueError("Goal Studio otomatik skill curator kapalı olmalı")
    if (
        config.get("gateway", {}).get("multiplex_profiles")
        or config.get("gateway", {}).get("standalone") is not True
    ):
        raise ValueError("Goal Studio ayrı, tek profilli daemon gerektirir")
    platforms = config.get("platforms", {})
    api = platforms.get("api_server", {})
    extra = api.get("extra", {})
    if set(extra) - {"host", "port", "model_name", "cors_origins", "browser_control"}:
        raise ValueError("Goal Studio API özel route/key/runtime ayarı kabul etmez")
    if (
        api.get("enabled") is not True
        or extra.get("host") != "127.0.0.1"
        or extra.get("port") != 8643
        or extra.get("model_name") != "forkos-goal-studio"
    ):
        raise ValueError(
            "Hermes API yalnız 127.0.0.1:8643 üzerinde Goal Studio olarak etkin olmalı"
        )
    if any(value.get("enabled") for name, value in platforms.items() if name != "api_server"):
        raise ValueError("Goal Studio başka platform çalıştıramaz")
    if config.get("auxiliary", {}).get("background_review", {}).get("enabled") is not False:
        raise ValueError("Goal Studio arka plan gözden geçirmesi kapalı olmalı")
    if config.get("context_engine", "default") != "default" or extra.get("model_routes"):
        raise ValueError("Özel bağlam motoru veya model yönlendirmesi kabul edilmez")
    if extra.get("cors_origins") or extra.get("browser_control", {}).get("enabled") is not False:
        raise ValueError("Hermes browser/CORS erişimi kapalı olmalı")
    model = config.get("model", {})
    if set(model) - {"provider", "default", "base_url"}:
        raise ValueError("Goal Studio model ayarları sağlayıcı/model/yerel adres ile sınırlı")
    if any(config.get(key) for key in ("api", "openai_runtime", "model_routes", "extra_headers")):
        raise ValueError("Goal Studio özel inference runtime veya model yönlendirmesi kabul etmez")
    if (
        model.get("provider") not in studio_policy.PROVIDERS
        or not isinstance(model.get("default"), str)
        or not re.fullmatch(r"[A-Za-z0-9_.:/+-]{1,200}", model["default"])
    ):
        raise ValueError("Goal Studio açık, izin listesindeki bir sağlayıcı ve model gerektirir")
    if model.get("provider") == "custom":
        loopback(model.get("base_url", ""))
    elif model.get("base_url"):
        raise ValueError("OAuth sağlayıcı URL'sini yalnız Hermes belirler")
    return config


async def _json(method, url, *, headers, body=None):
    if body is not None and len(json.dumps(body).encode()) > MAX_REQUEST:
        raise HTTPException(422, "Hermes istek bağlamı sınırı aşıldı")
    try:
        async with (
            asyncio.timeout(8),
            LIMIT,
            httpx.AsyncClient(timeout=6, trust_env=False, follow_redirects=False) as client,
            client.stream(method, url, headers=headers, json=body) as response,
        ):
            if response.status_code in {401, 403}:
                raise HTTPException(
                    503, "Hermes/profil/model kimlik doğrulaması geçersiz veya süresi dolmuş"
                )
            if response.status_code >= 300:
                raise HTTPException(
                    503, "Hermes/model isteği tamamlanamadı; mevcut koşuyu yeniden kontrol et"
                )
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > MAX_RESPONSE:
                    raise HTTPException(502, "Hermes yanıt sınırı aşıldı")
            return json.loads(content)
    except (httpx.HTTPError, TimeoutError, ValueError) as exc:
        raise HTTPException(503, "Hermes/model erişilemiyor veya yanıtı geçersiz") from exc


async def request(method, path, *, body=None, identity=None):
    base = loopback(settings.hermes_goal_base_url, profile=True)
    headers = {"Authorization": f"Bearer {settings.hermes_goal_api_key}"}
    if identity:
        headers["Idempotency-Key"] = identity
    return await _json(method, base + path, headers=headers, body=body)


async def local_model_ready(config):
    url = urlsplit(loopback(config["model"]["base_url"]))
    if url.path.rstrip("/") != "/v1":
        raise ValueError("Yerel model OpenAI uyumlu /v1 adresi gerekli")
    if settings.hermes_goal_topology == "host_bridge":
        if url.port not in MODEL_PORTS:
            raise ValueError("Yerel model host köprüsü portu izin listesinde değil")
        url = url._replace(netloc=f"host.docker.internal:{url.port}")
    headers = (
        {"Authorization": f"Bearer {settings.hermes_goal_model_api_key}"}
        if settings.hermes_goal_model_api_key
        else {}
    )
    models = await _json("GET", urlunsplit(url).rstrip("/") + "/models", headers=headers)
    if (
        not isinstance(models, dict)
        or not isinstance(models.get("data"), list)
        or config["model"]["default"]
        not in {row.get("id") for row in models["data"] if isinstance(row, dict)}
    ):
        raise HTTPException(503, "Yapılandırılmış yerel model çalışmıyor veya model bulunamadı")


def verify_toolsets(value, version):
    if version not in SUPPORTED_VERSIONS:
        raise ValueError("Hermes API sürümü doğrulanmış sözleşme dışında")
    rows = (
        value
        if isinstance(value, list)
        else value.get("data")
        if isinstance(value, dict)
        and (
            set(value) == {"data"}
            or (
                set(value) == {"object", "platform", "data"}
                and value["object"] == "list"
                and value["platform"] == "api_server"
            )
        )
        else None
    )
    if not isinstance(rows, list) or any(
        not isinstance(row, dict)
        or not isinstance(row.get("enabled"), bool)
        or not isinstance(row.get("tools"), list)
        or not all(isinstance(name, str) for name in row["tools"])
        for row in rows
    ):
        raise ValueError("Hermes etkin araç yanıtı bilinmeyen şemada")
    if any(row["enabled"] for row in rows):
        raise ValueError("Çalışan Hermes API profili araçları kapatmamış")


async def status(db=None):
    details = {"topology": settings.hermes_goal_topology}
    if not settings.hermes_goal_profile_config or not settings.hermes_goal_api_key:
        return StudioStatus(
            state="not_configured",
            message="Ayrı Hermes Goal Studio profili yapılandırılmamış; manuel Goals kullanılabilir.",
            **details,
        )
    try:
        config = verified_profile()
        policy = studio_policy.binding(config)
        details.update(
            provider=policy["mode"],
            provider_label=policy["label"],
            configured_model=policy["model"],
            local=policy["local"],
        )
        if db is not None:
            details["consent"] = await studio_policy.consent(db, policy)
        health = await request("GET", "/health")
        version = health.get("version")
        if version not in SUPPORTED_VERSIONS:
            raise ValueError("Hermes API sürümü doğrulanmış sözleşme dışında (0.21.6 gerekli)")
        details["hermes_version"] = version
        ready = await request("GET", "/health/detailed")
        if ready.get("status") != "ok" or ready.get("readiness", {}).get("status") != "ok":
            raise HTTPException(503, "Hermes kalıcı oturum/readiness kontrolü hazır değil")
        caps = await request("GET", "/v1/capabilities")
        features = caps.get("features", {})
        idem = features.get("runs_idempotency", {})
        if (
            caps.get("object") != "hermes.api_server.capabilities"
            or caps.get("model") != "forkos-goal-studio"
            or caps.get("auth", {}).get("required") is not True
            or not all(
                features.get(k) is True
                for k in ("run_submission", "run_status", "run_events_sse", "run_stop")
            )
            or idem.get("supported") is not True
            or idem.get("durable") is not True
            or not isinstance(idem.get("retention_seconds"), int)
            or idem["retention_seconds"] < 86400
        ):
            raise ValueError("Hermes profil/auth/runs/durable idempotency sözleşmesi sağlanmıyor")
        if features.get("browser_extension_control", {}).get("enabled") or features.get("cors"):
            raise ValueError("Hermes browser/CORS yeteneği etkin")
        endpoints = caps.get("endpoints", {})
        if endpoints.get("runs") != {"method": "POST", "path": "/v1/runs"}:
            raise ValueError("Hermes runs endpoint sözleşmesi geçersiz")
        verify_toolsets(await request("GET", "/v1/toolsets"), version)
        details["tools_verified"] = True
        # /v1/models on Hermes is an alias; never use it as underlying model attribution.
        if policy["local"]:
            await local_model_ready(config)
        if db is not None:
            permission = details["consent"]
            if not policy["local"] and not permission.allowed:
                return StudioStatus(
                    state="consent_required",
                    message="Seçili sağlayıcı için bulut çıkarımı izni gerekli.",
                    **details,
                )
        return StudioStatus(
            state="ready", message="Hermes bağlantısı hazır · etkin araç yok", **details
        )
    except ValueError as exc:
        return StudioStatus(state="unsupported", message=str(exc), **details)
    except (KeyError, TypeError, AttributeError, OSError, yaml.YAMLError):
        return StudioStatus(
            state="unsupported",
            message="Hermes profil, araç, sürüm veya API sözleşmesi desteklenmiyor; kurulum rehberini kontrol et.",
            **details,
        )
    except HTTPException as exc:
        return StudioStatus(state="unavailable", message=str(exc.detail), **details)


async def require_ready():
    result = await status()
    if result.state != "ready":
        raise HTTPException(503, result.message)


async def require_inference(db, *, expected_policy=None):
    await require_ready()
    policy = studio_policy.binding(verified_profile())
    await studio_policy.lock(db)
    if expected_policy is not None and policy["id"] != expected_policy:
        raise HTTPException(
            409, "Sağlayıcı/model/profil değişti; eski tur başka sağlayıcıya gönderilemez"
        )
    if not policy["local"] and not (await studio_policy.consent(db, policy)).allowed:
        raise HTTPException(
            403, "Bu sağlayıcı ve model için bulut çıkarımı izni yok veya geri alındı"
        )
    return policy


def verified_runtime(response, policy):
    runtime = response.get("runtime")
    if (
        not isinstance(runtime, dict)
        or runtime.get("provider") != policy["provider"]
        or runtime.get("model") != policy["model"]
    ):
        raise HTTPException(
            502, "Hermes gerçek sağlayıcı/model kökeni doğrulanamadı; taslak uygulanmadı"
        )
    return {"provider": runtime["provider"], "model": runtime["model"]}


async def public_events(run_id):
    """Stream lifecycle only. Final text is accepted after pollable runtime attribution/JSON validation."""
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
                yield 'data: {"reconcile": true}\n\n'
                return
            size, event, announced = 0, "", False
            async for line in response.aiter_lines():
                size += len(line.encode())
                if size > MAX_RESPONSE:
                    break
                if line.startswith("event:"):
                    event = line[6:].strip()
                if not line.startswith("data:"):
                    continue
                try:
                    data = json.loads(line[5:])
                except ValueError:
                    continue
                if not isinstance(data, dict):
                    continue
                name = data.get("type") or event
                if name == "message.delta" and not announced:
                    announced = True
                    yield 'data: {"text": "Hermes yanıt hazırlıyor…"}\n\n'
                elif name in {"run.completed", "run.failed", "run.cancelled", "run.interrupted"}:
                    break
                elif isinstance(name, str) and name.startswith("tool."):
                    yield 'data: {"blocked_tool_event": true}\n\n'
                    return
    except (httpx.HTTPError, TimeoutError):
        pass
    yield 'data: {"reconcile": true}\n\n'
