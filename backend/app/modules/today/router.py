from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import local_today
from app.db import get_session
from app.modules.today import service
from app.modules.today.schemas import TodayAgendaOut

router = APIRouter(tags=["today"])


@router.get("/today/agenda", response_model=TodayAgendaOut)
async def agenda(
    day: date = Query(default_factory=local_today),
    session: AsyncSession = Depends(get_session),
):
    return await service.agenda(session, day)
