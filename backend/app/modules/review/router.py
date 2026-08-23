from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import local_today
from app.db import get_session
from app.modules.review import service
from app.modules.review.schemas import ReviewIn, ReviewOut, ReviewPreview

router = APIRouter(tags=["review"])


@router.get("/reviews/preview", response_model=ReviewPreview)
async def preview(kind: str = "weekly", period_start: date = Query(default_factory=local_today),
                  session: AsyncSession = Depends(get_session)):
    try:
        return await service.preview(session, kind, period_start)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/reviews", response_model=ReviewOut, status_code=201)
async def create_review(body: ReviewIn, session: AsyncSession = Depends(get_session)):
    try:
        return await service.create(session, body)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/reviews", response_model=list[ReviewOut])
async def list_reviews(kind: str | None = None, limit: int = Query(20, ge=1, le=100),
                       session: AsyncSession = Depends(get_session)):
    return await service.list_reviews(session, kind, limit)
