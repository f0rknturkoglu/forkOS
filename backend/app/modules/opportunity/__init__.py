from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.opportunity.router import router
from app.modules.opportunity.service import deadline_provider as opportunity_deadlines

MODULE = ModuleSpec(id="opportunity",
    title="Opportunities",
    router=router,
    entity_types=[EntityTypeSpec(
            'opportunity', 'Fırsat', 'Fırsatlar', '/opportunities?focus={id}', 'Target',
        )],
    event_verbs=[
        "opportunity.created",
        "opportunity.updated",
        "opportunity.items_added",
        "opportunity.duplicates_merged",
    ],
        deadline_provider=opportunity_deadlines,
)
