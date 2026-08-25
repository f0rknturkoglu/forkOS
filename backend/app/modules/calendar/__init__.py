from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.calendar.router import router
from app.modules.calendar.service import deadline_provider as calendar_deadlines

MODULE = ModuleSpec(id="calendar",
    title="Calendar",
    router=router,
    entity_types=[EntityTypeSpec(
            'external_event', 'Takvim etkinliği', 'Takvim etkinlikleri', '/calendar', 'Calendar',
        )],
    event_verbs=["calendar.synced", "calendar.plan_pushed"],
        deadline_provider=calendar_deadlines,
)
