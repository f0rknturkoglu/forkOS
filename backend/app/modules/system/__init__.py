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
        "settings.reset",
        # Yedek akisi (backup.py) bu fiilleri uretir; orada sabit adlarla
        # yazildigi icin test_registry'nin literal tarayicisi goremiyordu.
        "backup.created",
        "backup.restored",
        "backup.drive_uploaded",
        "backup.drive_upload_failed",
    ],
)
