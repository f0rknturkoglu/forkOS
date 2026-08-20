from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.finance import service
from app.modules.finance.models import Expense, RecurringPayment
from app.modules.finance.schemas import ExpenseIn, ExpensePatch, RecurringIn, RecurringPatch

router = APIRouter(tags=["finance"])


@router.get("/expenses")
async def expenses(session: AsyncSession = Depends(get_session)):
    return await service.list_items(session, Expense)


@router.post("/expenses", status_code=201)
async def add_expense(body: ExpenseIn, session: AsyncSession = Depends(get_session)):
    return await service.create_item(session, Expense, body)


@router.patch("/expenses/{item_id}")
async def patch_expense(
    item_id: uuid.UUID, body: ExpensePatch, session: AsyncSession = Depends(get_session)
):
    result = await service.patch_item(session, Expense, item_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.get("/expenses/summary")
async def summary(
    year: int = date.today().year,
    month: int = date.today().month,
    session: AsyncSession = Depends(get_session),
):
    return await service.monthly_summary(session, year, month)


@router.get("/recurring-payments")
async def recurring(session: AsyncSession = Depends(get_session)):
    return await service.list_items(session, RecurringPayment)


@router.post("/recurring-payments", status_code=201)
async def add_recurring(body: RecurringIn, session: AsyncSession = Depends(get_session)):
    return await service.create_item(session, RecurringPayment, body)


@router.patch("/recurring-payments/{item_id}")
async def patch_recurring(
    item_id: uuid.UUID,
    body: RecurringPatch,
    session: AsyncSession = Depends(get_session),
):
    result = await service.patch_item(session, RecurringPayment, item_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.post("/recurring-payments/{item_id}/pay")
async def pay(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await service.pay_recurring(session, item_id)
    if result is None:
        raise HTTPException(404)
    return result
