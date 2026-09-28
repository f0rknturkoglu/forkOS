"""Ajan yetenek metadatası + `/api/agent/status` teşhis sözleşmesi.

Kanıtlanan üç şey: (1) `capabilities` ile GERÇEK kayıtlı MCP yüzeyi iki yönlü
aynıdır, (2) yerel biliş durumu makinesi doğru ve dış ağa çıkmadan çalışır,
(3) teşhis yükü sır, mutlak yol ve ham istisna metni SIZDIRMAZ.

Gerçek ağ YOKTUR: Ollama probu `httpx.MockTransport` ile stub'lanır. Testler
veritabanı da gerektirmez (`no_database`).
"""

from __future__ import annotations

import json
import re
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.integrations.agent import capabilities, mcp, status
from app.integrations.agent.mcp import mcp_server
from app.integrations.local_cognition.ollama import OllamaProvider
from tests.agent_test_utils import forbid_outbound_network  # noqa: F401  (autouse: dış ağ yok)

pytestmark = pytest.mark.no_database

#: Yerel biliş durumunun TAM kümesi (sözleşme).
STATES = {"disabled", "not_configured", "provider_unreachable", "model_missing", "ready"}

#: Teşhis yükünde BULUNMAMASI gereken anahtar desenleri.
FORBIDDEN_KEY_PATTERN = re.compile(
    r"secret|token|password|credential|api[_-]?key|authorization|cookie|passphrase",
    re.IGNORECASE,
)

#: `detail` alanına sızamayacak ham veri parçaları.
FORBIDDEN_DETAIL_TEXT = ("http", "11434", "Traceback", "ConnectError", "ProviderError")


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------


def _settings(**overrides: Any) -> SimpleNamespace:
    """H4 ayarlarının test kopyası. Yapılandırılmış adres varsayılan loopback'tir."""
    values: dict[str, Any] = {
        "h4_enabled": True,
        "h4_ollama_base_url": "http://127.0.0.1:11434",
        "h4_small_model": "small-model",
        "h4_medium_model": "medium-model",
        "h4_small_input_chars": 12000,
        "h4_medium_input_chars": 24000,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class _Recorder:
    """MockTransport'a gelen istekleri kaydeder (gerçek soket açılmaz)."""

    def __init__(self, handler) -> None:  # type: ignore[no-untyped-def]
        self._handler = handler
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        def handle(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return self._handler(request)

        return httpx.MockTransport(handle)

    @property
    def paths(self) -> list[str]:
        return [request.url.path for request in self.requests]


def _tags_recorder(names: list[str]) -> _Recorder:
    """`/api/tags` yanıtı: verilen model adları KURULU."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags", "teşhis probu yalnızca /api/tags çağırabilir"
        return httpx.Response(200, json={"models": [{"name": name} for name in names]})

    return _Recorder(handler)


def _unreachable_recorder() -> _Recorder:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    return _Recorder(handler)


def _factory(recorder: _Recorder):  # type: ignore[no-untyped-def]
    """Ayarlardaki loopback adrese bağlı, stub taşımalı sağlayıcı."""
    return lambda: OllamaProvider(
        "http://127.0.0.1:11434",
        timeout_seconds=status.DIAGNOSTIC_TIMEOUT_SECONDS,
        transport=recorder.transport(),
    )


def _forbidden_factory():  # type: ignore[no-untyped-def]
    def build():  # type: ignore[no-untyped-def]
        raise AssertionError("bu durumda sağlayıcı HİÇ oluşturulmamalı")

    return build


def _all_keys(node: object) -> list[str]:
    if isinstance(node, dict):
        return [key for key, value in node.items() for key in [str(key), *_all_keys(value)]]
    if isinstance(node, list):
        return [key for item in node for key in _all_keys(item)]
    return []


def _assert_no_leaks(payload: dict[str, Any]) -> None:
    """Sır, mutlak host yolu ve ham istisna metni yükte BULUNMAZ."""
    keys = _all_keys(payload)
    assert not [key for key in keys if FORBIDDEN_KEY_PATTERN.search(key)], keys
    text = json.dumps(payload, ensure_ascii=False)
    assert "/Users" not in text, text
    assert "Traceback" not in text, text


def _assert_detail_is_bounded(detail: str | None) -> None:
    assert detail, "bu durumda detail açıklaması beklenir"
    assert not [token for token in FORBIDDEN_DETAIL_TEXT if token in detail], detail


# ---------------------------------------------------------------------------
# 1) Metadata ↔ gerçek kayıt
# ---------------------------------------------------------------------------


async def test_capability_metadata_matches_registered_tool_surface() -> None:
    registered = {tool.name for tool in await mcp_server.list_tools()}

    # İki yön: kayıtlı olup metadatada olmayan ve metadatada olup kayıtlı olmayan araç yok.
    assert registered - capabilities.all_tools() == set()
    assert capabilities.all_tools() - registered == set()
    assert capabilities.tool_count() == len(registered) == 36
    assert capabilities.family_counts() == {
        "H0": 8,
        "H1": 11,
        "H2": 5,
        "H3": 1,
        "H4": 1,
        "H5": 3,
        "H6": 1,
        "H7": 1,
        "A5": 3,
        "Career": 2,
    }
    assert [family.id for family in capabilities.FAMILIES] == [
        "H0",
        "H1",
        "H2",
        "H3",
        "H4",
        "H5",
        "H6",
        "H7",
        "A5",
        "Career",
    ]


async def test_every_tool_belongs_to_exactly_one_family() -> None:
    declared = [name for family in capabilities.FAMILIES for name in family.tools]
    assert len(declared) == len(set(declared)) == capabilities.tool_count()

    for tool_name in await mcp_server.list_tools():
        family_id = capabilities.tool_to_family(tool_name.name)
        assert tool_name.name in capabilities.family_tools(family_id)

    for family in capabilities.FAMILIES:
        assert capabilities.family_tools(family.id) == set(family.tools)


def test_unknown_family_and_tool_do_not_match_silently() -> None:
    with pytest.raises(KeyError):
        capabilities.family_tools("H9")
    with pytest.raises(KeyError):
        capabilities.tool_to_family("forkos_not_a_tool")


# ---------------------------------------------------------------------------
# 2) Loopback invaryantı taşıma güvenliğiyle tutarlı mı
# ---------------------------------------------------------------------------


def test_loopback_only_matches_transport_security() -> None:
    # GERÇEK değerler okunur (uygulama yeniden kurulmaz: oturum yöneticisini
    # değiştirmek taşıma testlerini bozardı).
    transport_security = mcp.TRANSPORT_SECURITY
    assert transport_security.enable_dns_rebinding_protection is True

    loopback_names = {"127.0.0.1", "localhost", "[::1]"}

    def bare_host(host: str) -> str:
        """`[::1]:*` → `[::1]`, `127.0.0.1:*` → `127.0.0.1`."""
        if host.startswith("["):
            return host.split("]")[0] + "]"
        return host.split(":")[0]

    hosts = list(transport_security.allowed_hosts)
    assert hosts, "izinli host listesi boş olamaz"
    for host in hosts:
        assert bare_host(host) in loopback_names, host
    # Her loopback adı GERÇEKTEN kapsanmış olmalı (yalnızca "hepsi loopback" yetmez).
    assert {bare_host(host) for host in hosts} == loopback_names

    origins = list(transport_security.allowed_origins)
    assert origins
    for origin in origins:
        assert origin.startswith("http://127.0.0.1") or origin.startswith(
            "http://localhost"
        ) or origin.startswith("http://[::1]"), origin

    assert capabilities.LOOPBACK_ONLY is True
    assert capabilities.TRANSPORT == "streamable_http"
    assert capabilities.MCP_PATH == "/mcp"


# ---------------------------------------------------------------------------
# 3) Yerel biliş durum makinesi
# ---------------------------------------------------------------------------


async def test_disabled_state_never_probes() -> None:
    payload = await status.local_cognition_block(
        _settings(h4_enabled=False), provider_factory=_forbidden_factory()
    )

    assert payload["state"] == "disabled"
    assert payload["enabled"] is False
    assert payload["endpoint_class"] == "loopback"
    assert payload["reachable"] is None
    assert payload["detail"] is None
    assert payload["configured"] is True
    assert payload["small"] == {"configured": True, "available": False}
    assert payload["medium"] == {"configured": True, "available": False}
    _assert_no_leaks(payload)


async def test_not_configured_state_never_probes() -> None:
    payload = await status.local_cognition_block(
        _settings(h4_small_model="", h4_medium_model=""),
        provider_factory=_forbidden_factory(),
    )

    assert payload["state"] == "not_configured"
    assert payload["enabled"] is True
    assert payload["configured"] is False
    assert payload["reachable"] is None
    _assert_detail_is_bounded(payload["detail"])
    assert payload["small"] == {"configured": False, "available": False}
    assert payload["medium"] == {"configured": False, "available": False}
    _assert_no_leaks(payload)


async def test_provider_unreachable_when_transport_fails() -> None:
    recorder = _unreachable_recorder()
    payload = await status.local_cognition_block(
        _settings(), provider_factory=_factory(recorder)
    )

    assert payload["state"] == "provider_unreachable"
    assert payload["reachable"] is False
    assert payload["configured"] is True
    assert payload["small"]["available"] is False
    assert payload["medium"]["available"] is False
    assert recorder.paths == ["/api/tags"]
    _assert_detail_is_bounded(payload["detail"])
    _assert_no_leaks(payload)


async def test_model_missing_when_only_one_model_is_installed() -> None:
    recorder = _tags_recorder(["small-model:latest"])
    payload = await status.local_cognition_block(
        _settings(), provider_factory=_factory(recorder)
    )

    assert payload["state"] == "model_missing"
    assert payload["reachable"] is True
    assert payload["small"] == {"configured": True, "available": True}
    assert payload["medium"] == {"configured": True, "available": False}
    assert recorder.paths == ["/api/tags", "/api/tags"]
    _assert_no_leaks(payload)


async def test_ready_when_every_configured_model_is_installed() -> None:
    recorder = _tags_recorder(["small-model", "medium-model:latest"])
    payload = await status.local_cognition_block(
        _settings(), provider_factory=_factory(recorder)
    )

    assert payload["state"] == "ready"
    assert payload["reachable"] is True
    assert payload["small"] == {"configured": True, "available": True}
    assert payload["medium"] == {"configured": True, "available": True}
    assert payload["detail"] is None
    _assert_no_leaks(payload)


async def test_unconfigured_slot_is_not_probed() -> None:
    recorder = _tags_recorder(["small-model"])
    payload = await status.local_cognition_block(
        _settings(h4_medium_model=""), provider_factory=_factory(recorder)
    )

    assert payload["state"] == "ready"
    assert payload["medium"] == {"configured": False, "available": False}
    assert recorder.paths == ["/api/tags"]


async def test_non_loopback_endpoint_is_rejected_without_probing() -> None:
    payload = await status.local_cognition_block(
        _settings(h4_ollama_base_url="http://ollama.example.com:11434"),
        provider_factory=_forbidden_factory(),
    )

    assert payload["state"] == "provider_unreachable"
    assert payload["reachable"] is False
    # Güvenlik invaryantı yapılandırmada GÖRÜNÜR olmalı: uzak adres "loopback"
    # diye raporlanamaz.
    assert payload["endpoint_class"] == "invalid"
    assert "example.com" not in json.dumps(payload, ensure_ascii=False)
    _assert_no_leaks(payload)


async def test_endpoint_class_is_reported_even_when_disabled() -> None:
    """Sınıflandırma SAF'tır: H4 kapalıyken de doğru söylenir, prob atılmaz."""
    payload = await status.local_cognition_block(
        _settings(h4_enabled=False, h4_ollama_base_url="https://api.somecloud.com"),
        provider_factory=_forbidden_factory(),
    )

    assert payload["state"] == "disabled"
    assert payload["endpoint_class"] == "invalid"
    assert payload["reachable"] is None
    _assert_no_leaks(payload)


# ---------------------------------------------------------------------------
# 4) Yük şekli ve sızıntı yasağı
# ---------------------------------------------------------------------------


async def test_brain_block_shape_and_endpoint_host() -> None:
    payload = await status.agent_status_payload(
        server=("0.0.0.0", 9123), settings_obj=_settings(h4_enabled=False)
    )
    brain = payload["brain"]

    assert set(brain) == {
        "server_name",
        "endpoint",
        "transport",
        "loopback_only",
        "tool_count",
        "families",
    }
    assert brain["server_name"] == "forkos-brain"
    # Gerçek bağlanma portu kullanılır; host Host başlığından DEĞİL, sabittir.
    assert brain["endpoint"] == "http://127.0.0.1:9123/mcp"
    assert brain["transport"] == "streamable_http"
    assert brain["loopback_only"] is True
    assert brain["tool_count"] == 36

    families = brain["families"]
    assert [row["id"] for row in families] == [*[f"H{index}" for index in range(8)], "A5", "Career"]
    for row in families:
        assert set(row) == {"id", "label", "summary", "tool_count"}
        assert row["label"] and row["summary"]
    assert sum(row["tool_count"] for row in families) == 36

    assert set(payload["local_cognition"]) == {
        "enabled",
        "provider",
        "endpoint_class",
        "configured",
        "reachable",
        "state",
        "small",
        "medium",
        "detail",
    }
    assert payload["local_cognition"]["state"] in STATES
    assert payload["local_cognition"]["endpoint_class"] == "loopback"
    _assert_no_leaks(payload)


def test_endpoint_url_falls_back_to_default_port() -> None:
    assert status.endpoint_url(None) == "http://127.0.0.1:8787/mcp"
    assert status.endpoint_url(("127.0.0.1",)) == "http://127.0.0.1:8787/mcp"
    assert status.endpoint_url(("127.0.0.1", "abc")) == "http://127.0.0.1:8787/mcp"
    assert status.endpoint_url(("::1", 9999)) == "http://127.0.0.1:9999/mcp"


async def test_agent_status_route_serves_the_typed_payload() -> None:
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:9123") as client:
        response = await client.get("/api/agent/status")

    assert response.status_code == 200
    body = response.json()
    assert body["brain"]["endpoint"] == "http://127.0.0.1:9123/mcp"
    assert body["brain"]["tool_count"] == 36
    assert body["local_cognition"]["state"] in STATES
    # Varsayılan ayarlarda H4 kapalıdır: prob atılmaz, dış çağrı olmaz.
    assert body["local_cognition"]["state"] == "disabled"
    assert body["local_cognition"]["endpoint_class"] == "loopback"
    assert body["local_cognition"]["reachable"] is None


# ---------------------------------------------------------------------------
# 5) Talimat metni arayüzü doğru anlatıyor mu
# ---------------------------------------------------------------------------


def test_instructions_do_not_claim_a_read_only_interface() -> None:
    text = capabilities.instructions()
    lowered = text.lower()

    assert "read-only" not in lowered
    assert "read only" not in lowered
    assert "observer" not in lowered
    assert "salt okunur" not in lowered
    for family in capabilities.FAMILIES:
        assert family.id in text
    assert "approval" in lowered
    assert mcp_server.instructions == text
