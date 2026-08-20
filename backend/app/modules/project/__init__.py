from app.modules import ModuleSpec
from app.modules.project.router import router

MODULE = ModuleSpec(
    id="project",
    title="Projects",
    router=router,
    entity_types=["project"],
    event_verbs=["project.created", "project.updated", "github.commit"],
)
