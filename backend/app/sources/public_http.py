"""Bounded RSS fetching with validated DNS, IP-pinned connections and redirect checks."""

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx

MAX_BYTES = 4_000_000


def validate_public_url(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Kimlik bilgisi içermeyen bir HTTP(S) adresi kullan")
    if parsed.port not in {None, 80, 443}:
        raise ValueError("RSS yalnız standart HTTP(S) portlarını kullanabilir")
    host = parsed.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Yerel veya özel ağ adresleri RSS kaynağı olamaz")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("Yerel veya özel ağ adresleri RSS kaynağı olamaz")
    return parsed


async def public_address(host, port):
    addresses = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    ips = list(dict.fromkeys(item[4][0] for item in addresses))
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError("RSS adresi özel bir ağa çözümleniyor")
    return ips[0]


async def get_public(client, url, *, headers=None):
    original = url
    for _ in range(4):
        parsed = validate_public_url(url)
        # Explicit injected MockTransport never opens sockets, allowing deterministic DNS-free fixtures.
        mocked = isinstance(getattr(client, "_transport", None), httpx.MockTransport)
        address = (
            parsed.hostname
            if mocked
            else await public_address(
                parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
            )
        )
        pinned = httpx.URL(url).copy_with(host=address)
        async with client.stream(
            "GET",
            pinned,
            headers={**(headers or {}), "Host": parsed.netloc},
            extensions={"sni_hostname": parsed.hostname},
            follow_redirects=False,
        ) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                destination = response.headers.get("location")
                if not destination:
                    raise ValueError("RSS yönlendirme adresi eksik")
                url = urljoin(url, destination)
                continue
            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    raise ValueError("RSS yanıtı boyut sınırını aştı")
            # aiter_bytes() already decoded the transfer. Reusing Content-Encoding
            # would make httpx decode the plain XML a second time.
            decoded_headers = dict(response.headers)
            decoded_headers.pop("content-encoding", None)
            decoded_headers.pop("content-length", None)
            return httpx.Response(
                response.status_code,
                headers=decoded_headers,
                content=bytes(data),
                request=httpx.Request("GET", original),
            )
    raise ValueError("RSS çok fazla yönlendirme içeriyor")
