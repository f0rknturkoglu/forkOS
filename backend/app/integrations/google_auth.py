from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.models import OAuthToken

SCOPES = " ".join(
    [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/calendar.events",
    ]
)


def authorization_url() -> str:
    if not settings.google_client_id:
        raise RuntimeError("GOOGLE_CLIENT_ID yapılandırılmadı")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


async def exchange(session: AsyncSession, code: str) -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data = response.json()
    token = await session.get(OAuthToken, "google")
    if token is None:
        token = OAuthToken(provider="google", access_token=data["access_token"])
        session.add(token)
    token.access_token = data["access_token"]
    token.refresh_token = data.get("refresh_token") or token.refresh_token
    token.expires_at = datetime.now(UTC) + timedelta(seconds=data.get("expires_in", 3600))
    token.scopes = data.get("scope", SCOPES)
    await session.commit()


async def access_token(session: AsyncSession) -> str:
    token = await session.get(OAuthToken, "google")
    if token is None:
        raise RuntimeError("Google bağlı değil")
    if token.expires_at and token.expires_at > datetime.now(UTC) + timedelta(minutes=2):
        return token.access_token
    if not token.refresh_token:
        raise RuntimeError("Google refresh token yok; yeniden bağlan")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": token.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        data = response.json()
    token.access_token = data["access_token"]
    token.expires_at = datetime.now(UTC) + timedelta(seconds=data.get("expires_in", 3600))
    await session.commit()
    return token.access_token
