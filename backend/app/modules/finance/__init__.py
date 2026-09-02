from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.finance.router import router
from app.modules.finance.service import deadline_provider as finance_deadlines

MODULE = ModuleSpec(
    id="finance",
    title="Finance",
    router=router,
    entity_types=[
        EntityTypeSpec(
            'expense', 'Harcama', 'Harcamalar', '/finance', 'Wallet',
        ),
        EntityTypeSpec(
            'income', 'Gelir', 'Gelirler', '/finance', 'TrendingUp',
        ),
        EntityTypeSpec(
            'recurring_payment', 'Düzenli ödeme', 'Düzenli ödemeler', '/finance', 'Repeat',
        ),
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
    deadline_provider=finance_deadlines,
)
