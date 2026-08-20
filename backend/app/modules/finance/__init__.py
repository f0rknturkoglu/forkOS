from app.modules import ModuleSpec
from app.modules.finance.router import router

MODULE = ModuleSpec(
    id="finance",
    title="Finance",
    router=router,
    entity_types=["expense", "recurring_payment"],
    event_verbs=["expense.created", "recurring_payment.created", "recurring.paid"],
)
