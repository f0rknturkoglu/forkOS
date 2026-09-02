from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.statistics import service
from app.modules.statistics.schemas import MonthlyPoint, StatisticsSummary

router = APIRouter(tags=["statistics"])


@router.get("/statistics/summary", response_model=StatisticsSummary)
async def statistics_summary(session: AsyncSession = Depends(get_session)) -> StatisticsSummary:
    return await service.summary(session)


@router.get("/statistics/monthly", response_model=list[MonthlyPoint])
async def statistics_monthly(
    months: int = Query(default=6, ge=1, le=24),
    session: AsyncSession = Depends(get_session),
) -> list[MonthlyPoint]:
    return await service.monthly(session, months)
