"""V1 retired product. Schema and historical event vocabulary only; no active jobs or API."""
from fastapi import APIRouter

from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.finance import models as _models  # noqa: F401

router = APIRouter()

MODULE = ModuleSpec(
    id="finance",
    title="Finance",
    router=router,
    entity_types=[
        EntityTypeSpec(
            'expense', 'Harcama', 'Harcamalar', '/activity', 'Wallet', searchable=False, linkable=False),
        EntityTypeSpec(
            'income', 'Gelir', 'Gelirler', '/activity', 'TrendingUp', searchable=False, linkable=False),
        EntityTypeSpec(
            'recurring_payment', 'Düzenli ödeme', 'Düzenli ödemeler', '/activity', 'Repeat', searchable=False, linkable=False),
    ],
    event_verbs=[
        "expense.created",
        "expense.deleted",
        "income.created",
        "income.deleted",
        "recurring_payment.created",
        "recurring_payment.deleted",
        "recurring.paid",
    ],
)
