"""A3: epizodik oturum devri uçları.

Üç uç da DAR ve metadata-only'dir: hiçbiri ham transkript döndürmez ve hiçbiri
kanonik durumu değiştirmez.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.agent_episode import service
from app.modules.agent_episode.schemas import (
    EpisodeFinalizeIn,
    EpisodeFinalizeOut,
    EpisodeStatusOut,
    EpisodeTurnIn,
    EpisodeTurnOut,
)

LOGGER = logging.getLogger("forkos.agent_episode")

router = APIRouter(prefix="/agent/episode", tags=["agent-episode"])


@router.post("/turn", response_model=EpisodeTurnOut)
async def episode_turn(body: EpisodeTurnIn, session: AsyncSession = Depends(get_session)):
    """`post_llm_call` gözlemi: turu damıtır ve yalnız türetilmiş ifadeleri yazar.

    Ham `user_message`/`assistant_response` yanıtta DÖNMEZ; yalnız sayaç ve
    sınırlı gerekçe kodları döner.
    """
    try:
        return await service.ingest_turn(session, body)
    except service.EpisodeSessionNotFound as exc:
        await session.rollback()
        raise HTTPException(404, detail={"code": "EPISODE_SESSION_NOT_FOUND"}) from exc
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(503, detail={"code": "EPISODE_STORAGE_UNAVAILABLE"}) from exc


@router.post("/finalize", response_model=EpisodeFinalizeOut)
async def episode_finalize(body: EpisodeFinalizeIn, session: AsyncSession = Depends(get_session)):
    """Oturumu mühürler. İdempotenttir: ikinci çağrı aynı mühürlü kaydı döndürür."""
    try:
        return await service.finalize(session, body)
    except service.EpisodeSessionNotFound as exc:
        await session.rollback()
        raise HTTPException(404, detail={"code": "EPISODE_SESSION_NOT_FOUND"}) from exc
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(503, detail={"code": "EPISODE_STORAGE_UNAVAILABLE"}) from exc


@router.get("/status", response_model=EpisodeStatusOut)
async def episode_status(session: AsyncSession = Depends(get_session)):
    """Metadata-only tanılama: son mühürleme, ifade sayısı, taslak sayısı."""
    try:
        return await service.status(session)
    except SQLAlchemyError as exc:
        raise HTTPException(503, detail={"code": "EPISODE_STORAGE_UNAVAILABLE"}) from exc
