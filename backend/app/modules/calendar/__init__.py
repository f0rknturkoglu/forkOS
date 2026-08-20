from app.modules import ModuleSpec
from app.modules.calendar.router import router

MODULE = ModuleSpec(
    id="calendar",
    title="Calendar",
    router=router,
    entity_types=["external_event"],
    event_verbs=["calendar.synced", "calendar.plan_pushed"],
)
