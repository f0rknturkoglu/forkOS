from app.modules import ModuleSpec
from app.modules.opportunity.router import router

MODULE = ModuleSpec(
    id="opportunity",
    title="Opportunities",
    router=router,
    entity_types=["opportunity"],
    event_verbs=["opportunity.created", "opportunity.updated", "opportunity.items_added"],
)
