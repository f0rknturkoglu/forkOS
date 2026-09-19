from app.modules import ModuleSpec
from app.modules.system.router import router

MODULE = ModuleSpec(
    id="system",
    title="Settings",
    router=router,
    event_verbs=[
        "system.refresh.started",
        "system.refresh.completed",
        "system.maintenance",
        "system.automation_profile",
        "settings.updated",
        "backup.restored",
        "settings.reset",
    ],
)
