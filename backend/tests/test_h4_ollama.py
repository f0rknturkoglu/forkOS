"""Ollama sağlayıcısı: loopback sınırı, HTTP güvenliği, yapılandırılmış çıktı.

Gerçek ağ YOKTUR: `httpx.MockTransport` kullanılır. Loopback dışı bir host'a
bağlanılmadığı ve yönlendirme izlenmediği davranışsal olarak kanıtlanır.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.integrations.local_cognition.models import MAX_PROVIDER_RESPONSE_BYTES
from app.integrations.local_cognition.ollama import (
    LOOPBACK_HOSTS,
    OllamaProvider,
    validate_loopback_base_url,
)
from app.integrations.local_cognition.provider import GenerationRequest, ProviderError
from tests.agent_test_utils import forbid_outbound_network  # noqa: F401  (autouse)

SCHEMA = {"type": "object", "properties": {"label": {"type": "string"}}, "required": ["label"]}


class Recorder:
    """MockTransport'a gelen istekleri kaydeder."""

    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = responses
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        index = min(len(self.requests) - 1, len(self.responses) - 1)
        return self.responses[index]

    @property
    def paths(self) -> list[str]:
        return [request.url.path for request in self.requests]


def _provider(recorder: Recorder, *, base_url: str = "http://127.0.0.1:11434") -> OllamaProvider:
    return OllamaProvider(base_url, timeout_seconds=7.0, transport=httpx.MockTransport(recorder.handler))


def _chat_response(content: str) -> httpx.Response:
    return httpx.Response(200, json={"message": {"role": "assistant", "content": content}})


# ---------------------------------------------------------------------------
# Loopback sınırı (§46/§47/§165)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:11434",
        "http://localhost:11434",
        "http://[::1]:11434",
        "https://127.0.0.1:11434/",
    ],
)
def test_loopback_endpoints_are_accepted(url: str) -> None:
    assert validate_loopback_base_url(url).startswith("http")


@pytest.mark.parametrize(
    "url",
    [
        "https://api.somecloud.com",
        "http://192.168.1.50:11434",
        "http://10.0.0.7:11434",
        "http://model.example.invalid:11434",
        "ftp://127.0.0.1:11434",
        "",
        "   ",
    ],
)
def test_non_loopback_endpoints_are_rejected(url: str) -> None:
    """§165: bulut/LAN adresi REDDEDİLİR; hiçbir bağlantı denenmez."""
    with pytest.raises(ProviderError, match="INVALID_LOCAL_MODEL_ENDPOINT"):
        validate_loopback_base_url(url)


def test_provider_constructor_fails_closed_on_cloud_endpoint() -> None:
    recorder = Recorder([_chat_response("{}")])
    with pytest.raises(ProviderError, match="INVALID_LOCAL_MODEL_ENDPOINT"):
        OllamaProvider("https://api.somecloud.com", transport=httpx.MockTransport(recorder.handler))
    assert recorder.requests == []


def test_loopback_host_set_is_exactly_local() -> None:
    assert frozenset({"localhost", "127.0.0.1", "::1"}) == LOOPBACK_HOSTS


# ---------------------------------------------------------------------------
# Sağlık ve model varlığı (§57/§59/§60)
# ---------------------------------------------------------------------------


async def test_health_reports_model_presence() -> None:
    present = Recorder([httpx.Response(200, json={"models": [{"name": "qwen2.5:3b"}]})])
    health = await _provider(present).health("qwen2.5")
    assert health.healthy is True and health.model_available is True
    assert present.paths == ["/api/tags"]

    absent = Recorder([httpx.Response(200, json={"models": [{"name": "other:1b"}]})])
    missing = await _provider(absent).health("qwen2.5")
    assert missing.healthy is False and missing.model_available is False


async def test_health_never_pulls_a_missing_model() -> None:
    """§60: çalışma zamanında model İNDİRİLMEZ."""
    recorder = Recorder([httpx.Response(200, json={"models": []})])
    await _provider(recorder).health("missing-model")
    assert recorder.paths == ["/api/tags"]
    assert all("pull" not in path for path in recorder.paths)


async def test_health_requires_a_configured_model() -> None:
    recorder = Recorder([httpx.Response(200, json={"models": []})])
    health = await _provider(recorder).health("")
    assert health.configured is False
    assert recorder.requests == []


async def test_health_provider_errors_are_bounded() -> None:
    failing = Recorder([httpx.Response(500, json={"error": "boom"})])
    with pytest.raises(ProviderError, match="MODEL_PROVIDER_UNAVAILABLE"):
        await _provider(failing).health("qwen2.5")

    broken = Recorder([httpx.Response(200, content=b"not json")])
    with pytest.raises(ProviderError, match="MODEL_PROVIDER_UNAVAILABLE"):
        await _provider(broken).health("qwen2.5")


async def test_health_transport_error_is_bounded() -> None:
    def _boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = OllamaProvider("http://127.0.0.1:11434", transport=httpx.MockTransport(_boom))
    with pytest.raises(ProviderError, match="MODEL_PROVIDER_UNAVAILABLE"):
        await provider.health("qwen2.5")


# ---------------------------------------------------------------------------
# Yapılandırılmış üretim (§49/§50/§99)
# ---------------------------------------------------------------------------


async def test_structured_generation_sends_a_deterministic_bounded_request() -> None:
    recorder = Recorder([_chat_response('{"label": "task"}')])
    provider = _provider(recorder)

    result = await provider.generate_structured(
        GenerationRequest(
            model_id="qwen2.5",
            system_prompt="system",
            user_prompt="user",
            json_schema=SCHEMA,
            temperature=0.0,
            timeout_seconds=7.0,
        )
    )

    assert result.content == '{"label": "task"}'
    assert recorder.paths == ["/api/chat"]

    body = json.loads(recorder.requests[0].content)
    assert body["stream"] is False
    assert body["format"] == SCHEMA
    assert body["options"]["temperature"] == 0
    assert body["model"] == "qwen2.5"
    assert [message["role"] for message in body["messages"]] == ["system", "user"]
    # Araç/fonksiyon verilmez: model kendi başına iş kurmaz (§49).
    assert "tools" not in body
    assert "functions" not in body


async def test_http_client_disables_redirects_and_proxy_inheritance() -> None:
    """§48: yönlendirme izlenmez, ortam proxy'si devralınmaz."""
    provider = _provider(Recorder([_chat_response("{}")]))
    client = provider._client()
    try:
        assert client.follow_redirects is False
        assert client.trust_env is False
        assert client.timeout.connect == 7.0
    finally:
        await client.aclose()


async def test_redirect_response_is_not_followed() -> None:
    recorder = Recorder(
        [httpx.Response(302, headers={"location": "https://api.somecloud.com/v1/chat"})]
    )
    provider = _provider(recorder)

    with pytest.raises(ProviderError, match="MODEL_PROVIDER_UNAVAILABLE"):
        await provider.generate_structured(
            GenerationRequest(
                model_id="qwen2.5",
                system_prompt="s",
                user_prompt="u",
                json_schema=SCHEMA,
            )
        )
    # Yönlendirme İZLENMEDİ: tek istek, yalnızca loopback host'a.
    assert len(recorder.requests) == 1
    assert recorder.requests[0].url.host == "127.0.0.1"


async def test_timeout_is_reported_as_provider_unavailable() -> None:
    def _timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    provider = OllamaProvider("http://127.0.0.1:11434", transport=httpx.MockTransport(_timeout))
    with pytest.raises(ProviderError, match="MODEL_PROVIDER_UNAVAILABLE"):
        await provider.generate_structured(
            GenerationRequest(model_id="m", system_prompt="s", user_prompt="u", json_schema=SCHEMA)
        )


async def test_missing_model_on_generation_reports_model_unavailable() -> None:
    recorder = Recorder([httpx.Response(404, json={"error": "model not found"})])
    with pytest.raises(ProviderError, match="MODEL_UNAVAILABLE"):
        await _provider(recorder).generate_structured(
            GenerationRequest(model_id="ghost", system_prompt="s", user_prompt="u", json_schema=SCHEMA)
        )


async def test_oversized_response_is_rejected() -> None:
    oversized = httpx.Response(200, content=b"x" * (MAX_PROVIDER_RESPONSE_BYTES + 1))
    with pytest.raises(ProviderError, match="OUTPUT_TOO_LARGE"):
        await _provider(Recorder([oversized])).generate_structured(
            GenerationRequest(model_id="m", system_prompt="s", user_prompt="u", json_schema=SCHEMA)
        )


async def test_provider_error_text_carries_no_raw_payload() -> None:
    """Hata mesajı sınırlıdır: ham gövde, URL veya istisna metni taşımaz."""
    recorder = Recorder([httpx.Response(500, text="SECRET-INTERNAL-DETAIL")])
    with pytest.raises(ProviderError) as excinfo:
        await _provider(recorder).generate_structured(
            GenerationRequest(model_id="m", system_prompt="s", user_prompt="u", json_schema=SCHEMA)
        )
    assert "SECRET-INTERNAL-DETAIL" not in str(excinfo.value)
    assert "127.0.0.1" not in str(excinfo.value)
