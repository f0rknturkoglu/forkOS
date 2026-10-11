"""DNS pinning, redirect and payload limits; never opens a real socket."""

import gzip
import socket

import httpx
import pytest

from app.sources import public_http
from app.sources.opml import parse_opml
from app.sources.rss_source import parse_entries

pytestmark = pytest.mark.no_database


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/rss",
        "http://[::1]/rss",
        "http://169.254.169.254/",
        "http://192.168.1.1/",
        "http://localhost/",
        "https://host.local/",
        "file:///etc/passwd",
        "https://u:p@example.com/",
        "https://example.com:8787/",
    ],
)
def test_private_urls_rejected(url):
    with pytest.raises(ValueError):
        public_http.validate_public_url(url)


async def test_private_redirect_rejected_before_second_request():
    calls = []

    def upstream(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/secrets"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
        with pytest.raises(ValueError):
            await public_http.get_public(client, "https://example.com/rss")
    assert calls == ["https://example.com/rss"]


async def test_private_dns_and_mixed_answers_rejected(monkeypatch):
    async def answers(*args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 443)),
        ]

    monkeypatch.setattr(public_http.asyncio.get_running_loop(), "getaddrinfo", answers)
    with pytest.raises(ValueError):
        await public_http.public_address("public.example", 443)


async def test_pinned_address_keeps_original_host_and_tls_sni(monkeypatch):
    calls = []

    class Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            calls.append(request)
            return httpx.Response(200, content=b"RSS")

    resolves = []

    async def resolve(host, port):
        resolves.append((host, port))
        return "8.8.8.8"

    monkeypatch.setattr(public_http, "public_address", resolve)
    async with httpx.AsyncClient(transport=Transport(), trust_env=False) as client:
        response = await public_http.get_public(client, "https://example.com/rss")
    assert response.content == b"RSS" and len(resolves) == 1
    assert calls[0].url.host == "8.8.8.8"
    assert calls[0].headers["host"] == "example.com"
    assert calls[0].extensions["sni_hostname"] == "example.com"


async def test_response_limit_and_redirect_loop():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, content=b"x" * (public_http.MAX_BYTES + 1))
        )
    ) as client:
        with pytest.raises(ValueError, match="boyut"):
            await public_http.get_public(client, "https://example.com/rss")
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(302, headers={"location": "/again"}))
    ) as client:
        with pytest.raises(ValueError, match="yönlendirme"):
            await public_http.get_public(client, "https://example.com/rss")


@pytest.mark.parametrize("parse", [parse_entries, parse_opml])
def test_entity_declarations_rejected(parse):
    with pytest.raises(ValueError):
        parse(b'<!DOCTYPE rss [<!ENTITY x "expanded">]><rss/>')


async def test_compressed_feed_is_decoded_once_and_keeps_conditional_metadata():
    raw = b'<rss version="2.0"><channel><title>Feed</title><item><title>Entry</title><guid>one</guid></item></channel></rss>'
    compressed = gzip.compress(raw)

    def upstream(request):
        return httpx.Response(
            200,
            stream=httpx.ByteStream(compressed),
            headers={
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
                "ETag": '"rss-v1"',
                "Content-Type": "application/rss+xml",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
        response = await public_http.get_public(client, "https://example.com/rss")
    assert response.content == raw
    assert "content-encoding" not in response.headers
    assert int(response.headers["content-length"]) == len(raw)
    assert response.headers["etag"] == '"rss-v1"'
    assert parse_entries(response.content)[0].title == "Entry"


async def test_compressed_feed_size_limit_applies_after_decoding():
    compressed = gzip.compress(b"x" * (public_http.MAX_BYTES + 1))
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, stream=httpx.ByteStream(compressed), headers={"Content-Encoding": "gzip"}
            )
        )
    ) as client:
        with pytest.raises(ValueError, match="boyut"):
            await public_http.get_public(client, "https://example.com/rss")
