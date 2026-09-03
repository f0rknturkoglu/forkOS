from __future__ import annotations

import calendar
import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import extract, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity
from app.core.time import local_datetime, local_today
from app.modules import DeadlineRow
from app.modules.finance.models import Expense, Income, RecurringPayment

#: Kaydin tarih kolonu -- gelir/gider ayni sekle sahip, kolon adi farkli.
DATE_COLUMN = {Expense: Expense.spent_on, Income: Income.received_on}

#: Tekrarlayan odemenin bir aya dusen payi (kur donusumu yok).
MONTHS_PER_PERIOD = {"monthly": 1, "quarterly": 3, "yearly": 12}

CENT = Decimal("0.01")


def _serialize_item(item, title: str) -> dict:
    return {
        "id": item.id,
        "title": title,
        **{
            column.name: getattr(item, column.name)
            for column in item.__table__.columns
            if column.name != "id"
        },
    }


async def out(session: AsyncSession, item) -> dict:
    title = (await session.execute(select(Entity.title).where(Entity.id == item.id))).scalar_one()
    return _serialize_item(item, title)


async def list_items(session: AsyncSession, model) -> list[dict]:
    if model is RecurringPayment:
        order = RecurringPayment.next_due_at.asc().nullslast()
    else:
        order = DATE_COLUMN[model].desc()
    rows = (
        await session.execute(
            select(model, Entity.title).join(Entity, Entity.id == model.id).order_by(order)
        )
    ).all()
    return [_serialize_item(item, title) for item, title in rows]


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


async def _month_totals(session: AsyncSession, model, year: int, month: int) -> list[tuple]:
    """(currency, category, toplam) satirlari -- verilen ay icin."""
    column = DATE_COLUMN[model]
    rows = (
        await session.execute(
            select(model.currency, model.category, func.sum(model.amount))
            .where(extract("year", column) == year, extract("month", column) == month)
            .group_by(model.currency, model.category)
            .order_by(model.currency, func.sum(model.amount).desc())
        )
    ).all()
    return [(currency.strip(), category, amount) for currency, category, amount in rows]


def monthly_share(amount: Decimal, frequency: str) -> Decimal:
    """Tekrarlayan odemenin bir aya dusen payi (yillik 1200 -> 100)."""
    months = MONTHS_PER_PERIOD.get(frequency, 1)
    return (Decimal(amount) / months).quantize(CENT, rounding=ROUND_HALF_UP)


async def month_overview(session: AsyncSession, year: int, month: int) -> dict:
    """Bir ayin tam finans tablosu: gelir, gider, net, kategori dagilimi.

    Kur donusumu YOK -- her para birimi kendi bloguna dusuyor. Arayuz basligi
    tek cagriyla dolsun diye gelir/gider/abonelik ayni yanitta toplanir.
    """
    expenses = await _month_totals(session, Expense, year, month)
    incomes = await _month_totals(session, Income, year, month)
    recurring = (
        await session.execute(
            select(RecurringPayment.currency, RecurringPayment.frequency, RecurringPayment.amount)
            .where(RecurringPayment.active.is_(True))
        )
    ).all()

    buckets: dict[str, dict] = {}

    def bucket(currency: str) -> dict:
        return buckets.setdefault(
            currency,
            {
                "currency": currency,
                "income": Decimal(0),
                "expense": Decimal(0),
                "net": Decimal(0),
                "recurring_monthly": Decimal(0),
                "expense_by_category": [],
                "income_by_category": [],
            },
        )

    for currency, category, amount in expenses:
        row = bucket(currency)
        row["expense"] += amount
        row["expense_by_category"].append({"category": category, "amount": amount})
    for currency, category, amount in incomes:
        row = bucket(currency)
        row["income"] += amount
        row["income_by_category"].append({"category": category, "amount": amount})
    for currency, frequency, amount in recurring:
        row = bucket(currency.strip())
        row["recurring_monthly"] += monthly_share(amount, frequency)

    for row in buckets.values():
        row["net"] = row["income"] - row["expense"]

    # Hareketi en yogun para birimi basta -- arayuz ilkini one cikarir.
    order = sorted(
        buckets.values(), key=lambda r: r["income"] + r["expense"], reverse=True
    )
    return {"year": year, "month": month, "currencies": order}


async def monthly_summary(session: AsyncSession, months: int) -> list[dict]:
    """Son `months` ayin gelir/gider toplamlari -- grafik serisi.

    Eksen surekli olsun diye bos ay da sifirli satir olarak gelir; sira
    eskiden yeniye, bugun dahil. Kur donusumu YOK; grafik basina tek seri
    cizdigi icin ay icindeki tum para birimleri tek toplamda birlestirilir
    (tek kur kullanan kullanicilar icin fark yoktur).
    """
    today = local_today()
    end_index = today.year * 12 + today.month  # gelecek ayin basi (haric)
    start_index = end_index - months
    start = date(start_index // 12, start_index % 12 + 1, 1)
    end = date(end_index // 12, end_index % 12 + 1, 1)

    totals: dict[str, dict[str, Decimal]] = {}
    for model, key in ((Expense, "expense"), (Income, "income")):
        column = DATE_COLUMN[model]
        # 'month' literal olmali: parametreli date_trunc($1, ...) SELECT ve
        # GROUP BY'da farkli parametre indeksine duser, Postgres eslesmez.
        month_trunc = func.date_trunc(literal("month"), column)
        rows = (
            await session.execute(
                select(month_trunc, func.sum(model.amount))
                .where(column >= start, column < end)
                .group_by(month_trunc)
            )
        ).all()
        for month_start, amount in rows:
            month = month_start.strftime("%Y-%m")
            totals.setdefault(month, {"income": Decimal(0), "expense": Decimal(0)})[key] += amount

    return [
        {
            "month": f"{index // 12:04d}-{index % 12 + 1:02d}",
            "income": totals.get(f"{index // 12:04d}-{index % 12 + 1:02d}", {}).get("income", Decimal(0)),
            "expense": totals.get(f"{index // 12:04d}-{index % 12 + 1:02d}", {}).get("expense", Decimal(0)),
        }
        for index in range(start_index, end_index)
    ]


def advance(value: date, frequency: str, billing_day: int | None = None) -> date:
    """Bir sonraki odeme tarihi. billing_day verilmisse o gune sabitlenir."""
    months = MONTHS_PER_PERIOD.get(frequency)
    if months is None:
        raise ValueError("geçersiz ödeme sıklığı")
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(billing_day or value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


async def pay_recurring(session: AsyncSession, item_id: uuid.UUID) -> dict | None:
    payment = await session.get(RecurringPayment, item_id)
    if payment is None:
        return None
    entity = await session.get(Entity, payment.id)
    paid_on = payment.next_due_at or local_today()
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
        sub=payment.sub,
        note=payment.note,
    )
    session.add(expense)
    await link(session, payment.id, expense.id, "paid_as")
    payment.next_due_at = advance(paid_on, payment.frequency, payment.billing_day)
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


async def deadline_provider(session: AsyncSession) -> list[DeadlineRow]:
    """Aktif tekrarlayan odemelerin vadesi (kural 16)."""
    from app.core.deadlines import rows_with_titles

    payments = list((await session.execute(
        select(RecurringPayment).where(
            RecurringPayment.active.is_(True),
            RecurringPayment.next_due_at.is_not(None),
        )
    )).scalars())
    # due_at sozlesmesi timezone-aware datetime'dir (todo/opportunity gibi):
    # collect_deadlines satirlari birlikte siralar, ICS disa aktarimi
    # astimezone() cagirir -- ciplak date ikisini de patlatir.
    return await rows_with_titles(
        session, type_="recurring_payment", module="recurring",
        ids=[x.id for x in payments],
        due_at={x.id: local_datetime(x.next_due_at) for x in payments},
        priority={x.id: 1 for x in payments},
    )
