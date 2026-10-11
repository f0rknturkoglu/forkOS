from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.document.router import router

MODULE = ModuleSpec(
    id="document",
    title="Documents",
    router=router,
    entity_types=[EntityTypeSpec('document', 'Belge', 'Belgeler', '/opportunities?tab=applications', 'FileText', searchable=False, linkable=False)],
    event_verbs=["document.created", "document.deleted", "document.synced"],
)
