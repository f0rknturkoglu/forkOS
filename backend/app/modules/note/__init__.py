from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.note.router import router

MODULE = ModuleSpec(
    id="note",
    title="Notes",
    router=router,
    # Rota Documents icindeki focused nota gider (Faz 21) -- ayri sidebar
    # modulu yoktur; Documents sayfasi "Yerel Notlar" + "Drive Belgeleri"
    # ayrimini gosterir.
    entity_types=[EntityTypeSpec(
        'note', 'Not', 'Notlar', '/documents?focus={id}', 'StickyNote',
    )],
    event_verbs=["note.created", "note.updated", "note.pinned",
                 "note.archived", "note.deleted"],
)
