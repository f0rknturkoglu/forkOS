"""A5.1 jevmlx adapter tests; every HTTP exchange is mocked."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest

from app.integrations.judgment.jevmlx import ContextProviderError, JevMlxProvider
from app.integrations.judgment.models import (
    ContextCandidate,
    ContextJudgmentRequest,
    SourceSnapshot,
)

pytestmark = pytest.mark.no_database


def request(count: int = 2) -> ContextJudgmentRequest:
    snapshot = SourceSnapshot(source_id="entity:1", source_type="entity", source_revision="r1", captured_at=datetime.now(UTC))
    return ContextJudgmentRequest(
        request_id="test", query="Which source helps?",
        candidates=tuple(ContextCandidate(
            evidence_id=f"entity:{i}", source_type="entity", title=f"Source {i}",
            excerpt="A bounded excerpt.", retrieval_position=i, snapshot=snapshot,
        ) for i in range(count)),
    )


def valid_response(count: int = 2) -> dict:
    parsed = {}
    telemetry = {}
    for i in range(count):
        for kind, value in (("usefulness", "essential" if i else "weak"), ("redundancy", "unique")):
            key = f"candidate_{i}_{kind}"
            parsed[key] = {"value": value}
            telemetry[key] = {"value": value, "probability": 0.8, "probability_margin": 0.4}
    return {"model": "mlx-community/Qwen2.5-3B-Instruct-4bit", "parsed_json": parsed, "field_telemetry": telemetry}


@pytest.mark.parametrize("url", [
    "https://example.com", "http://192.168.1.50:8000", "http://10.0.0.4:8000",
    "http://8.8.8.8:8000", "http://user:pass@127.0.0.1:8000", "http://127.0.0.1:8000/redirect",
    "http://host.docker.internal:8000", "http://evil@host.docker.internal:8000",
    "http://host.docker.internal:8000/path", "http://host.docker.internal:8000?next=remote",
])
def test_non_loopback_or_unsafe_endpoint_rejected(url):
    with pytest.raises(ContextProviderError) as exc:
        JevMlxProvider(url)
    assert exc.value.code == "CONTEXT_JUDGE_INVALID_ENDPOINT"


@pytest.mark.parametrize("url", ["http://127.0.0.1:8000", "http://localhost:8000", "http://[::1]:8000"])
def test_loopback_forms_allowed(url):
    assert JevMlxProvider(url).base_url == url


def test_docker_host_bridge_requires_explicit_opt_in():
    assert JevMlxProvider("http://host.docker.internal:8000", allow_host_bridge=True).base_url == "http://host.docker.internal:8000"
    with pytest.raises(ContextProviderError):
        JevMlxProvider("https://host.docker.internal:8000", allow_host_bridge=True)


@pytest.mark.parametrize("url", [
    "http://192.168.1.50:8000", "http://10.0.0.4:8000", "http://example.com:8000",
])
def test_remote_rejected_even_when_bridge_enabled(url):
    with pytest.raises(ContextProviderError):
        JevMlxProvider(url, allow_host_bridge=True)


async def test_ready_and_one_batched_decision():
    calls = []

    def handler(req: httpx.Request):
        calls.append(req)
        if req.url.path == "/ready":
            return httpx.Response(200, json={"ready": True})
        body = json.loads(req.content)
        assert len(body["schema"]) == 4
        assert "candidate_1_usefulness" in body["schema"]
        assert "untrusted" in body["context"]
        assert "/Users/" not in body["context"]
        return httpx.Response(200, json=valid_response())

    provider = JevMlxProvider("http://127.0.0.1:8000", transport=httpx.MockTransport(handler))
    assert provider._client().follow_redirects is False
    assert await provider.health()
    result = await provider.judge_context(request())
    assert len(result) == 2 and result[1].usefulness == "essential"
    assert result[1].metadata.provider_confidence == 0.8
    assert result[1].metadata.calibrated is False
    assert [call.url.path for call in calls] == ["/ready", "/decide"]


async def test_health_uses_ready_not_health():
    provider = JevMlxProvider("http://127.0.0.1:8000", transport=httpx.MockTransport(lambda req: httpx.Response(503, json={"ready": False})))
    assert not await provider.health()


@pytest.mark.parametrize(("status", "expected"), [(429, "CONTEXT_JUDGE_BUSY"), (413, "CONTEXT_JUDGE_INVALID_RESPONSE"), (500, "CONTEXT_JUDGE_UNAVAILABLE"), (503, "CONTEXT_JUDGE_UNAVAILABLE"), (302, "CONTEXT_JUDGE_UNAVAILABLE")])
async def test_http_failures(status, expected):
    provider = JevMlxProvider("http://127.0.0.1:8000", transport=httpx.MockTransport(lambda req: httpx.Response(status)))
    with pytest.raises(ContextProviderError) as exc:
        await provider.judge_context(request())
    assert exc.value.code == expected


@pytest.mark.parametrize("failure", ["partial", "unknown", "invalid_json", "duplicate_json", "extra"])
async def test_invalid_response_fail_closed(failure):
    body = valid_response()
    if failure == "partial":
        body["parsed_json"].pop("candidate_1_usefulness")
    elif failure == "unknown":
        body["parsed_json"]["candidate_1_usefulness"]["value"] = "awesome"
    elif failure == "extra":
        body["parsed_json"]["invented"] = {"value": "essential"}
    content = json.dumps(body).encode()
    if failure == "invalid_json":
        content = b"not json"
    elif failure == "duplicate_json":
        content = b'{"parsed_json":{},"parsed_json":{}}'
    transport = httpx.MockTransport(lambda req: httpx.Response(200, content=content))
    provider = JevMlxProvider("http://127.0.0.1:8000", transport=transport)
    with pytest.raises(ContextProviderError) as exc:
        await provider.judge_context(request())
    assert exc.value.code == "CONTEXT_JUDGE_INVALID_RESPONSE"


@pytest.mark.parametrize("kind", ["connection", "timeout"])
async def test_network_failures(kind):
    def handler(req):
        if kind == "timeout":
            raise httpx.ReadTimeout("slow")
        raise httpx.ConnectError("offline")

    provider = JevMlxProvider("http://127.0.0.1:8000", transport=httpx.MockTransport(handler))
    with pytest.raises(ContextProviderError) as exc:
        await provider.judge_context(request())
    assert exc.value.code == ("CONTEXT_JUDGE_TIMEOUT" if kind == "timeout" else "CONTEXT_JUDGE_UNAVAILABLE")


async def test_ready_model_populates_metadata_and_refreshes_without_stale_cache():
    ready_models = iter(["fast", "other", None])

    def handler(req):
        if req.url.path == "/ready":
            return httpx.Response(200, json={"ready": True, "model": next(ready_models)})
        body = valid_response()
        body.pop("model")
        return httpx.Response(200, json=body)

    provider = JevMlxProvider("http://127.0.0.1:8000", transport=httpx.MockTransport(handler))
    for expected in ("fast", "other", None):
        assert await provider.health()
        verdicts = await provider.judge_context(request())
        assert all(verdict.metadata.model_id == expected for verdict in verdicts)


async def test_not_ready_clears_model_identity():
    ready = iter([{"ready": True, "model": "fast"}, {"ready": False, "model": "fast"}])

    def handler(req):
        if req.url.path == "/ready":
            return httpx.Response(200, json=next(ready))
        body = valid_response()
        body.pop("model")
        return httpx.Response(200, json=body)

    provider = JevMlxProvider("http://127.0.0.1:8000", transport=httpx.MockTransport(handler))
    assert await provider.health()
    assert not await provider.health()
    assert all(verdict.metadata.model_id is None for verdict in await provider.judge_context(request()))


async def test_redirect_is_not_followed():
    destinations = []

    def handler(req):
        destinations.append(str(req.url))
        return httpx.Response(302, headers={"location": "https://example.com/collect"})

    provider = JevMlxProvider("http://127.0.0.1:8000", transport=httpx.MockTransport(handler))
    with pytest.raises(ContextProviderError):
        await provider.judge_context(request())
    assert destinations == ["http://127.0.0.1:8000/decide"]
