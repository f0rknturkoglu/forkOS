from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.note.router import router

MODULE = ModuleSpec(
    id="note",
    title="Notes",
    router=router,
    entity_types=[EntityTypeSpec(
        'note', 'Not', 'Notlar', '/notes?focus={id}', 'StickyNote',
    )],
    event_verbs=["note.created", "note.updated", "note.pinned",
                 "note.archived", "note.deleted", "note.attachment_added",
                 "note.attachment_deleted"],
)
