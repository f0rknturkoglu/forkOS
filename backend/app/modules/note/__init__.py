from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.note.router import router

MODULE = ModuleSpec(
    id="note",
    title="Notes",
    router=router,
    entity_types=[
        EntityTypeSpec('note', 'Not', 'Notlar', '/notes?focus={id}', 'StickyNote'),
        EntityTypeSpec(
            'note_folder', 'Not klasörü', 'Not klasörleri',
            '/notes?folder={id}', 'Folder', searchable=False, linkable=False,
        ),
    ],
    event_verbs=["note.created", "note.updated", "note.pinned",
                 "note.archived", "note.deleted", "note.attachment_added",
                 "note.attachment_deleted", "note.moved", "note.folder_created",
                 "note.folder_updated", "note.folder_deleted"],
)
