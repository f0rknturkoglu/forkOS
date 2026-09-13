from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.document.router import router

MODULE = ModuleSpec(
    id="document",
    title="Documents",
    router=router,
    entity_types=[EntityTypeSpec('document', 'Belge', 'Belgeler', '/documents?focus={id}', 'FileText')],
    event_verbs=["document.created", "document.deleted", "document.synced"],
)
