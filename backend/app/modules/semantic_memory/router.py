"""A4: Semantic Memory HTTP yönlendiricisi."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.semantic_memory import service
from app.modules.semantic_memory.schemas import (
    SemanticCandidateConfirmIn,
    SemanticCandidateListResponse,
    SemanticCandidatePromoteIn,
    SemanticCandidatePromoteOut,
    SemanticCandidateRead,
    SemanticCandidateRefreshIn,
    SemanticCandidateRefreshOut,
    SemanticCandidateRejectIn,
    SemanticStatusOut,
)

router = APIRouter(prefix="/agent/semantic", tags=["agent-semantic"])


@router.get("/candidates", response_model=SemanticCandidateListResponse)
async def list_candidates(
    status: str | None = Query(None),
    kind: str | None = Query(None),
    destination: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """Kayıtlı semantik hafıza adaylarını listeler."""
    return await service.list_candidates(
        session, status=status, kind=kind, destination=destination, limit=limit, offset=offset
    )


@router.get("/candidates/{candidate_id}", response_model=SemanticCandidateRead)
async def get_candidate(candidate_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Belirli bir adayın detayını döner."""
    cand = await service.get_candidate(session, candidate_id)
    return SemanticCandidateRead.model_validate(cand)


@router.post("/refresh", response_model=SemanticCandidateRefreshOut)
async def refresh_candidates(
    payload: SemanticCandidateRefreshIn = SemanticCandidateRefreshIn(),
    session: AsyncSession = Depends(get_session),
):
    """Mühürlenmiş epizotlardan ve kanonik kaynaklardan adayları tazeler."""
    return await service.refresh_candidates(session, payload)


@router.post("/candidates/{candidate_id}/confirm", response_model=SemanticCandidateRead)
async def confirm_candidate(
    candidate_id: uuid.UUID,
    payload: SemanticCandidateConfirmIn,
    session: AsyncSession = Depends(get_session),
):
    """Adayı kullanıcı tarafından onaylanmış ('ready') olarak işaretler."""
    return await service.confirm_candidate(session, candidate_id, payload)


@router.post("/candidates/{candidate_id}/reject", response_model=SemanticCandidateRead)
async def reject_candidate(
    candidate_id: uuid.UUID,
    payload: SemanticCandidateRejectIn,
    session: AsyncSession = Depends(get_session),
):
    """Adayı reddeder ('rejected')."""
    return await service.reject_candidate(session, candidate_id, payload)


@router.post("/candidates/{candidate_id}/promote", response_model=SemanticCandidatePromoteOut)
async def promote_candidate(
    candidate_id: uuid.UUID,
    payload: SemanticCandidatePromoteIn,
    session: AsyncSession = Depends(get_session),
):
    """Adayı kalıcı bilgiye terfi ettirir."""
    return await service.promote_candidate(session, candidate_id, payload)


@router.get("/status", response_model=SemanticStatusOut)
async def get_status(session: AsyncSession = Depends(get_session)):
    """Semantik hafıza durumu ve özet istatistikleri döner."""
    return await service.get_status(session)
