"""Google OAuth donusu: sabit Ayarlar hedefi + tek kullanimlik CSRF `state`.

Gercek aga CIKILMAZ: token alisverisi (`exchange`) monkeypatch'lenir. Donus
adresi SABIT olmali -- query'den gelen keyfi bir `return`/`redirect` degeri
kabul edilmemelidir; bu yuzden testler tam URL esitligi kurar.
"""

from __future__ import annotations

import importlib
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.db import SessionLocal
from app.integrations import google_auth
from app.integrations.models import OAuthToken
from app.main import app

# `app.integrations.google_router` paket niteligi APIRouter nesnesidir; modulu
# hedeflemek icin importlib sart (exchange'i orada monkeypatch'liyoruz).
document_router = importlib.import_module("app.integrations.google_router")

CALLBACK = "/api/auth/google/callback"
RETURN_URL = "http://127.0.0.1:5173/#/settings?tab=integrations"


@pytest.fixture
async def oauth(monkeypatch: pytest.MonkeyPatch):
    """ASGI istemcisi + yakalanan `exchange` cagrilari."""
    monkeypatch.setattr(settings, "google_client_id", "test-client")
    monkeypatch.setattr(google_auth, "_pending_states", {})  # testler arasi sizinti olmasin
    exchanged: list[str] = []

    async def fake_exchange(_session, code: str) -> None:
        exchanged.append(code)

    monkeypatch.setattr(document_router, "exchange", fake_exchange)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http, exchanged


async def _start_state(client: AsyncClient) -> str:
    response = await client.get("/api/auth/google/start")
    assert response.status_code in (302, 307)
    location = urlparse(response.headers["location"])
    assert location.netloc == "accounts.google.com"
    state = parse_qs(location.query).get("state")
    assert state and state[0]
    return state[0]


async def test_callback_returns_to_settings_integrations_tab(oauth):
    client, exchanged = oauth
    state = await _start_state(client)

    done = await client.get(CALLBACK, params={"code": "c1", "state": state})

    assert done.status_code in (302, 307)
    assert done.headers["location"] == RETURN_URL
    assert exchanged == ["c1"]


async def test_state_is_single_use(oauth):
    client, exchanged = oauth
    state = await _start_state(client)
    await client.get(CALLBACK, params={"code": "c1", "state": state})

    replay = await client.get(CALLBACK, params={"code": "c2", "state": state})

    assert replay.status_code == 400
    assert exchanged == ["c1"]


async def test_external_return_parameter_does_not_move_the_redirect(oauth):
    client, exchanged = oauth
    state = await _start_state(client)

    done = await client.get(
        CALLBACK,
        params={
            "code": "c1",
            "state": state,
            "return": "https://evil.example/",
            "redirect": "https://evil.example/",
            "next": "https://evil.example/",
        },
    )

    assert done.status_code in (302, 307)
    assert done.headers["location"] == RETURN_URL
    assert exchanged == ["c1"]


async def test_mismatched_state_is_rejected_and_existing_connection_survives(oauth):
    client, exchanged = oauth
    async with SessionLocal() as session:
        session.add(
            OAuthToken(
                provider="google",
                access_token="mevcut-erisim",
                refresh_token="mevcut-yenileme",
            )
        )
        await session.commit()
    await _start_state(client)

    response = await client.get(CALLBACK, params={"code": "saldirgan-kodu", "state": "tahmin-edilmis"})

    assert response.status_code == 400
    assert exchanged == []
    async with SessionLocal() as session:
        token = await session.get(OAuthToken, "google")
        assert token is not None
        assert token.access_token == "mevcut-erisim"
        assert token.refresh_token == "mevcut-yenileme"


async def test_pending_states_are_bounded_and_expire(oauth, monkeypatch: pytest.MonkeyPatch):
    client, _exchanged = oauth
    monkeypatch.setattr(google_auth, "STATE_TTL_SECONDS", -1.0)
    expired = await _start_state(client)
    assert (await client.get(CALLBACK, params={"code": "c1", "state": expired})).status_code == 400

    monkeypatch.setattr(google_auth, "STATE_TTL_SECONDS", 600.0)
    issued = [await _start_state(client) for _ in range(google_auth.MAX_PENDING_STATES + 2)]

    # En eski bekleyen deger dusurulur: bellek sinirli kalir, son deneme gecerli.
    assert (await client.get(CALLBACK, params={"code": "c1", "state": issued[0]})).status_code == 400
    assert (await client.get(CALLBACK, params={"code": "c2", "state": issued[-1]})).status_code in (302, 307)
