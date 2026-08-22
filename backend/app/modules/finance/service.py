from __future__ import annotations

import calendar
import uuid
from datetime import date

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity
from app.modules.finance.models import Expense, RecurringPayment


async def out(session: AsyncSession, item) -> dict:
    title = (await session.execute(select(Entity.title).where(Entity.id == item.id))).scalar_one()
    return {
        "id": item.id,
        "title": title,
        **{
            column.name: getattr(item, column.name)
            for column in item.__table__.columns
            if column.name != "id"
        },
    }


async def list_items(session: AsyncSession, model) -> list[dict]:
    order = (
        Expense.spent_on.desc()
        if model is Expense
        else RecurringPayment.next_due_at.asc().nullslast()
    )
    items = list((await session.execute(select(model).join(Entity).order_by(order))).scalars())
    return [await out(session, item) for item in items]


async def create_item(session: AsyncSession, model, data) -> dict:
    values = data.model_dump()
    title = values.pop("title")
    entity = await create_entity(
        session, type=model.ENTITY_TYPE, title=title, search_text=str(values)
    )
    item = model(id=entity.id, **values)
    session.add(item)
    await log_event(
        session,
        verb=f"{model.ENTITY_TYPE}.created",
        entity_id=item.id,
        entity_type=model.ENTITY_TYPE,
        payload={"amount": str(item.amount), "currency": item.currency},
    )
    await session.commit()
    return await out(session, item)


async def patch_item(session: AsyncSession, model, item_id: uuid.UUID, data) -> dict | None:
    item = await session.get(model, item_id)
    if item is None:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    for key, value in values.items():
        setattr(item, key, value)
    await touch_entity(session, item.id, title=title, search_text=str(values))
    await session.commit()
    return await out(session, item)


async def monthly_summary(session: AsyncSession, year: int, month: int) -> list[dict]:
    rows = (
        await session.execute(
            select(Expense.currency, Expense.category, func.sum(Expense.amount))
            .where(
                extract("year", Expense.spent_on) == year,
                extract("month", Expense.spent_on) == month,
            )
            .group_by(Expense.currency, Expense.category)
            .order_by(Expense.currency, func.sum(Expense.amount).desc())
        )
    ).all()
    return [
        {"currency": currency.strip(), "category": category, "amount": amount}
        for currency, category, amount in rows
    ]


def advance(value: date, frequency: str) -> date:
    months = {"monthly": 1, "quarterly": 3, "yearly": 12}.get(frequency)
    if months is None:
        raise ValueError("geçersiz ödeme sıklığı")
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


async def pay_recurring(session: AsyncSession, item_id: uuid.UUID) -> dict | None:
    payment = await session.get(RecurringPayment, item_id)
    if payment is None:
        return None
    entity = await session.get(Entity, payment.id)
    paid_on = payment.next_due_at or date.today()
    expense_entity = await create_entity(
        session,
        type="expense",
        title=entity.title if entity else "Recurring payment",
        search_text=payment.note or "",
    )
    expense = Expense(
        id=expense_entity.id,
        amount=payment.amount,
        currency=payment.currency,
        category=payment.category,
        spent_on=paid_on,
        note=payment.note,
    )
    session.add(expense)
    await link(session, payment.id, expense.id, "paid_as")
    payment.next_due_at = advance(paid_on, payment.frequency)
    await log_event(
        session,
        verb="recurring.paid",
        entity_id=payment.id,
        entity_type="recurring_payment",
        payload={"expense_id": str(expense.id), "next_due_at": payment.next_due_at.isoformat()},
    )
    await session.commit()
    return {"expense": await out(session, expense), "next_due_at": payment.next_due_at}


async def delete_item(session: AsyncSession, model, item_id: uuid.UUID) -> bool:
    """Kaydi siler. `event` kalir -- append-only (kural 3)."""
    item = await session.get(model, item_id)
    if item is None:
        return False
    entity = await session.get(Entity, item_id)
    title = entity.title if entity else ""
    if not await delete_entity(session, item_id):
        return False
    await log_event(session, verb=f"{model.ENTITY_TYPE}.deleted",
                    entity_type=model.ENTITY_TYPE, payload={"title": title})
    await session.commit()
    return True
