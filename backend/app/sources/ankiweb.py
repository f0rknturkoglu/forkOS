"""User-selected public AnkiWeb catalog; no accounts, cookies or personal data.

Wire fields match the official shared-decks frontend GET protocol observed
2026-10-12. Strict bounded decoder ignores unknown protobuf fields.
"""

import asyncio
import time
from urllib.parse import urlencode

import httpx

from app.sources.base import FetchOutcome, RawItem, ScrapeTelemetry, retry_after_seconds
from app.sources.public_http import get_public

MAX_PACKAGE_BYTES = 32_000_000
BASE = "https://ankiweb.net"
_NOT_BEFORE = 0.0


def varint(data, position):
    value = 0
    for shift in range(0, 70, 7):
        if position >= len(data):
            raise ValueError("Truncated varint")
        byte = data[position]
        position += 1
        value |= (byte & 127) << shift
        if not byte & 128:
            return value, position
    raise ValueError("Invalid varint")


def fields(data):
    position = 0
    result = {}
    while position < len(data):
        tag, position = varint(data, position)
        number, wire = tag >> 3, tag & 7
        if not number:
            raise ValueError("Invalid field")
        if wire == 0:
            value, position = varint(data, position)
        else:
            if wire == 2:
                size, position = varint(data, position)
            elif wire == 1:
                size = 8
            elif wire == 5:
                size = 4
            else:
                raise ValueError("Invalid wire type")
            if position + size > len(data):
                raise ValueError("Truncated field")
            value = data[position : position + size]
            position += size
        result.setdefault(number, []).append(value)
    return result


def scalar(data, key, default=0):
    return data.get(key, [default])[0]


def string(data, key):
    value = scalar(data, key, b"")
    if not isinstance(value, bytes):
        raise ValueError("AnkiWeb katalog biçimi değişti")
    return value.decode("utf-8")


async def public_get(path, *, max_bytes=4_000_000):
    global _NOT_BEFORE
    remaining = int(_NOT_BEFORE - time.monotonic()) + 1
    if remaining > 0:
        response = httpx.Response(
            429, headers={"Retry-After": str(remaining)}, request=httpx.Request("GET", BASE)
        )
        raise httpx.HTTPStatusError(
            "AnkiWeb istek sınırı", request=response.request, response=response
        )
    try:
        async with asyncio.timeout(45), httpx.AsyncClient(timeout=30, trust_env=False) as client:
            response = await get_public(client, BASE + path, max_bytes=max_bytes)
            if response.status_code in {429, 503}:
                delay = retry_after_seconds(response.headers.get("retry-after"))
                if response.status_code == 429 or delay is not None:
                    _NOT_BEFORE = time.monotonic() + (delay if delay is not None else 60)
            response.raise_for_status()
            return response.content
    except TimeoutError as exc:
        raise httpx.ReadTimeout("AnkiWeb isteği zaman aşımına uğradı") from exc


class AnkiWebSource:
    id = "ankiweb:shared-decks"
    interval_minutes = 60
    source_class = "slow_optin"
    timeout_seconds = 45

    def __init__(self, search="english"):
        self.search = search

    async def fetch(self):
        data = await public_get("/svc/shared/list-decks?" + urlencode({"search": self.search}))
        rows = [fields(row) for row in fields(data).get(1, [])]
        rows.sort(key=lambda row: scalar(row, 3) - scalar(row, 4), reverse=True)
        items = [
            RawItem(
                external_id=str(scalar(row, 1)),
                title=string(row, 2)[:300],
                url=f"{BASE}/shared/info/{scalar(row, 1)}",
                extra={
                    "notes": scalar(row, 6),
                    "likes": scalar(row, 3),
                    "has_media": bool(scalar(row, 7) or scalar(row, 8)),
                },
            )
            for row in rows[:12]
        ]
        return FetchOutcome(
            items=items,
            telemetry=ScrapeTelemetry(
                items_seen=len(rows),
                items_returned=len(items),
                result_limit=12,
                cap_hit=len(rows) > 12,
            ),
        )


async def deck_info(shared_id):
    data = fields(await public_get("/svc/shared/item-info?" + urlencode({"sharedId": shared_id})))
    if 1 not in data:
        raise ValueError("Deste bulunamadı veya erişime kapalı")
    available = fields(data[1][0])
    if scalar(available, 16) or 10 not in available:
        raise ValueError("Bu paylaşım bir kart destesi değil veya yayından kaldırılmış")
    deck = fields(available[10][0])
    key = string(deck, 5)
    if not key or len(key) > 2000:
        raise ValueError("AnkiWeb indirme bağlantısı alınamadı")
    size = scalar(available, 7)
    if size > MAX_PACKAGE_BYTES:
        raise ValueError("Deste 32 MB sınırını aşıyor; daha küçük bir deste seç")
    samples = []
    for sample in deck.get(4, [])[:3]:
        sample_fields = fields(sample)
        # Public sample content is never interpreted as HTML or script.
        samples.append(
            [
                string(fields(value), 2)[:500]
                for value in sample_fields.get(1, [])
                if isinstance(value, bytes)
            ]
        )
    return {
        "id": shared_id,
        "title": string(available, 5)[:300],
        "notes": scalar(deck, 1),
        "has_media": bool(scalar(deck, 2) or scalar(deck, 3)),
        "size_bytes": size,
        "url": f"{BASE}/shared/info/{shared_id}",
        "samples": samples,
        "download_key": key,
    }


async def download_deck(shared_id):
    info = await deck_info(shared_id)
    content = await public_get(
        f"/svc/shared/download-deck/{shared_id}?" + urlencode({"t": info["download_key"]}),
        max_bytes=MAX_PACKAGE_BYTES,
    )
    return info, content
