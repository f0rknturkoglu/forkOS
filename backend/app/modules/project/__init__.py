from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.project.router import router
from app.modules.project.service import deadline_provider as project_deadlines

MODULE = ModuleSpec(id="project",
    title="Projects",
    router=router,
    entity_types=[EntityTypeSpec(
            'project', 'Proje', 'Projeler', '/projects?focus={id}', 'Layers',
        ),
        EntityTypeSpec(
            'milestone', 'Kilometre taşı', 'Kilometre taşları', '/projects?focus={id}', 'Flag',
        linkable=False)],
    event_verbs=[
        "project.created",
        "project.updated",
        "project.milestone_added",
        "project.milestone_updated",
        "project.milestone_deleted",
        "github.commit",
    ],
        deadline_provider=project_deadlines,
)
