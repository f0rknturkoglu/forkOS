from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.integrations.google_auth import authorization_url, consume_state, exchange
from app.integrations.models import OAuthToken

router = APIRouter(tags=["google-calendar"])

#: OAuth donusu her zaman Ayarlar > Entegrasyonlar sekmesine iner: baglanti
#: orada baslatilir ve "bagli" durumu orada beklenir. Hedef SABITTIR; query'den
#: gelen `return`/`redirect`/`next` gibi bir parametre OKUNMAZ, boylece callback
#: acik yonlendirme (open redirect) yuzeyi olmaz. Origin frontend CORS
#: listesinin ilk elemanidir; prod'da da ayni listeden turetilir.
RETURN_PATH = "/#/settings?tab=integrations"


def _return_url() -> str:
    return f"{settings.cors_origins[0]}{RETURN_PATH}"


@router.get("/auth/google/start")
async def auth_start():
    try:
        return RedirectResponse(authorization_url())
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/auth/google/callback")
async def callback(
    code: str,
    state: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    # CSRF: `state` bizim urettigimiz tek kullanimlik deger olmali. Eslesmezse
    # token alisverisi HIC baslamaz; mevcut Google baglantisi oldugu gibi kalir.
    if not consume_state(state):
        raise HTTPException(400, "Google bağlantısı doğrulanamadı; bağlanmayı yeniden deneyin.")
    await exchange(session, code)
    return RedirectResponse(_return_url())


@router.get("/auth/google/status")
async def status(session: AsyncSession = Depends(get_session)):
    token = await session.get(OAuthToken, "google")
    return {
        "connected": token is not None,
        "expires_at": token.expires_at if token else None,
        "scopes": token.scopes if token else None,
    }


@router.delete("/auth/google", status_code=204)
async def disconnect(session: AsyncSession = Depends(get_session)):
    """Google Calendar token'ini siler; yeni senkron icin yeniden baglanmak gerekir."""
    token = await session.get(OAuthToken, "google")
    if token is not None:
        await session.delete(token)
        await session.commit()


