from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.goal.router import router
from app.modules.goal.service import deadline_provider

MODULE = ModuleSpec(
    id="goal",
    title="Goals",
    router=router,
    entity_types=[
        # C8 has a list/editor surface, not a standalone relation-detail surface.
        EntityTypeSpec(
            "goal", "Hedef", "Hedefler", "/opportunities?tab=career", "Target", linkable=False
        ),
        EntityTypeSpec(
            "goal_milestone",
            "Hedef kilometre taşı",
            "Hedef kilometre taşları",
            "/opportunities?tab=career",
            "Flag",
            linkable=False,
        ),
    ],
    event_verbs=[
        "goal.created",
        "goal.updated",
        "goal.milestone_added",
        "goal.milestone_updated",
    ],
    deadline_provider=deadline_provider,
)
