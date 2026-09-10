"""Ayarlar API'si: varsayilanlar, tip dogrulamasi, sifirlama, entegrasyon kesme.

Hava durumu proxy'si de burada test edilir: gercek aga CIKILMAZ, `httpx`
istemcisi monkeypatch ile sabitlenir. Sozlesme su: tarayici open-meteo'ya
dogrudan gitmez, istek backend'den cikar.
"""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.db import SessionLocal
from app.integrations.models import OAuthToken
from app.main import app
from app.modules.system.models import Setting

DEAD_KEYS = ("pomodoro.defaults", "notifications.thresholds", "sources.intervals")


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://upstream.test/")
            raise httpx.HTTPStatusError("upstream hata", request=request, response=httpx.Response(self.status_code))


class _FakeClient:
    """`httpx.AsyncClient` yerine gecer: cagrilari kaydeder, sabit govde doner."""

    calls: list[tuple[str, dict]] = []
    payload: dict = {}
    status_code = 200

    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *_exc) -> bool:
        return False

    async def get(self, url: str, params: dict | None = None) -> _FakeResponse:
        type(self).calls.append((url, params or {}))
        return _FakeResponse(self.payload, self.status_code)


@pytest.fixture
def fake_weather(monkeypatch: pytest.MonkeyPatch):
    _FakeClient.calls = []
    _FakeClient.payload = {}
    _FakeClient.status_code = 200
    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)
    return _FakeClient


# ── Varsayilanlar ───────────────────────────────────────────────────────


async def test_settings_defaults_skip_dead_json_keys(client: AsyncClient):
    response = await client.get("/api/settings")

    assert response.status_code == 200
    payload = response.json()
    for key in DEAD_KEYS:
        assert key not in payload, f"olu ayar geri gelmis: {key}"
    assert payload["today.auto_suggestions"] is True
    assert payload["rss.retention_days"] == 90
    assert payload["today.widget_hidden"] == []
    assert payload["opportunity.career_profile"]["authorized_countries"] == ["Türkiye"]
    assert payload["news.subreddits"]


# ── Tip dogrulamasi ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("rss.retention_days", "90"),
        ("rss.retention_days", 0),
        ("rss.retention_days", True),
        ("today.auto_suggestions", "yes"),
        ("modules.disabled", "notes"),
        ("news.subreddits", "programming"),
        ("media.links", [{"name": "Letterboxd"}]),
        ("opportunity.career_profile", {"authorized_countries": "Türkiye"}),
        ("finance.monthly_budget", {"TRY": -5}),
        ("finance.monthly_budget", {"TRY": "30000"}),
        ("finance.monthly_budget", {"TL": 5}),
    ],
)
async def test_put_setting_rejects_wrong_types(client: AsyncClient, key: str, value: object):
    response = await client.put(f"/api/settings/{key}", json={"value": value})

    assert response.status_code == 422
    async with SessionLocal() as session:
        assert await session.get(Setting, key) is None


async def test_put_setting_accepts_valid_values_and_persists(client: AsyncClient):
    career = {
        "current_location": "Berlin, Almanya",
        "authorized_countries": ["Türkiye", "Almanya"],
        "willing_to_relocate": True,
    }
    for key, value in (("rss.retention_days", 30), ("today.auto_suggestions", False), ("opportunity.career_profile", career)):
        assert (await client.put(f"/api/settings/{key}", json={"value": value})).status_code == 200

    payload = (await client.get("/api/settings")).json()
    assert payload["rss.retention_days"] == 30
    assert payload["today.auto_suggestions"] is False
    assert payload["opportunity.career_profile"] == career


async def test_unknown_setting_keys_stay_free_form(client: AsyncClient):
    """Beyaz liste degil: tanimsiz anahtar 422 vermez (ileri uyumluluk)."""
    response = await client.put("/api/settings/weather.lat", json={"value": 41.0})

    assert response.status_code == 200
    assert (await client.get("/api/settings")).json()["weather.lat"] == 41.0


# ── Sifirlama (Tehlikeli Bolge) ─────────────────────────────────────────


async def test_reset_clears_user_settings_and_keeps_runtime_state(client: AsyncClient):
    async with SessionLocal() as session:
        session.add(Setting(key="rss.retention_days", value=7))
        session.add(Setting(key="worker.heartbeat", value={"at": "2026-09-11T00:00:00+00:00"}))
        await session.commit()

    response = await client.post("/api/settings/reset")

    assert response.status_code == 200
    assert response.json()["removed"] == 1
    assert (await client.get("/api/settings")).json()["rss.retention_days"] == 90
    async with SessionLocal() as session:
        heartbeat = await session.get(Setting, "worker.heartbeat")
        assert heartbeat is not None, "worker kalp atisi sistem durumudur, silinmemeli"
        assert await session.get(Setting, "rss.retention_days") is None


# ── Entegrasyon kesme ───────────────────────────────────────────────────


async def test_github_connect_then_disconnect(client: AsyncClient):
    assert (await client.post("/api/auth/github", json={"login": "octocat", "token": "gh-token"})).status_code == 200
    assert (await client.get("/api/auth/github/status")).json() == {"connected": True, "login": "octocat"}

    response = await client.delete("/api/auth/github")

    assert response.status_code == 204
    assert (await client.get("/api/auth/github/status")).json() == {"connected": False, "login": None}
    async with SessionLocal() as session:
        assert await session.get(OAuthToken, "github") is None


async def test_github_disconnect_is_idempotent(client: AsyncClient):
    assert (await client.delete("/api/auth/github")).status_code == 204


async def test_google_disconnect_removes_token(client: AsyncClient):
    async with SessionLocal() as session:
        session.add(OAuthToken(provider="google", access_token="g-token"))
        await session.commit()

    assert (await client.get("/api/auth/google/status")).json()["connected"] is True
    assert (await client.delete("/api/auth/google")).status_code == 204

    assert (await client.get("/api/auth/google/status")).json()["connected"] is False
    async with SessionLocal() as session:
        assert await session.get(OAuthToken, "google") is None


# ── Hava durumu proxy'si ────────────────────────────────────────────────


async def test_geocode_proxies_city_lookup(client: AsyncClient, fake_weather):
    _FakeClient.payload = {
        "results": [{"name": "Ankara", "latitude": 39.92, "longitude": 32.85, "country": "Türkiye", "admin1": "Ankara"}]
    }

    response = await client.get("/api/weather/geocode", params={"query": "Ankara"})

    assert response.status_code == 200
    assert response.json() == {
        "name": "Ankara",
        "latitude": 39.92,
        "longitude": 32.85,
        "country": "Türkiye",
        "admin1": "Ankara",
    }
    url, params = _FakeClient.calls[0]
    assert url == "https://geocoding-api.open-meteo.com/v1/search"
    assert params["name"] == "Ankara"
    assert params["language"] == "tr"


async def test_geocode_reverse_lookup_uses_coordinates(client: AsyncClient, fake_weather):
    _FakeClient.payload = {"results": [{"name": "Kadıköy", "latitude": 40.99, "longitude": 29.03}]}

    response = await client.get("/api/weather/geocode", params={"lat": 40.99, "lon": 29.03})

    assert response.status_code == 200
    assert response.json()["name"] == "Kadıköy"
    _url, params = _FakeClient.calls[0]
    assert params == {"latitude": 40.99, "longitude": 29.03, "count": 1, "language": "tr"}


async def test_geocode_without_query_is_rejected(client: AsyncClient, fake_weather):
    assert (await client.get("/api/weather/geocode")).status_code == 422
    assert _FakeClient.calls == []


async def test_geocode_unknown_city_is_404(client: AsyncClient, fake_weather):
    _FakeClient.payload = {"results": []}

    assert (await client.get("/api/weather/geocode", params={"query": "Yokböyle"})).status_code == 404


async def test_geocode_upstream_failure_is_502(client: AsyncClient, fake_weather):
    _FakeClient.status_code = 503

    assert (await client.get("/api/weather/geocode", params={"query": "Ankara"})).status_code == 502


async def test_forecast_proxies_open_meteo_payload(client: AsyncClient, fake_weather):
    _FakeClient.payload = {
        "current": {"temperature_2m": 21.5, "weather_code": 1, "relative_humidity_2m": 40},
        "daily": {"weather_code": [1, 2, 3, 61]},
    }

    response = await client.get("/api/weather/forecast", params={"lat": 39.92, "lon": 32.85})

    assert response.status_code == 200
    assert response.json()["current"]["temperature_2m"] == 21.5
    url, params = _FakeClient.calls[0]
    assert url == "https://api.open-meteo.com/v1/forecast"
    assert params["latitude"] == 39.92
    assert params["longitude"] == 32.85
    assert params["timezone"] == "auto"
    assert params["forecast_days"] == 4


async def test_forecast_requires_coordinates(client: AsyncClient, fake_weather):
    assert (await client.get("/api/weather/forecast")).status_code == 422
