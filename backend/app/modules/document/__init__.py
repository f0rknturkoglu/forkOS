from app.modules import ModuleSpec
from app.modules.document.router import router

MODULE = ModuleSpec(
    id="document",
    title="Documents",
    router=router,
    entity_types=["document"],
    event_verbs=["document.synced"],
)
