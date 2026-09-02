from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.flashcard.router import router

MODULE = ModuleSpec(
    id="flashcard",
    title="Kartlar",
    router=router,
    entity_types=[
        EntityTypeSpec(
            'flashcard_deck', 'Kart destesi', 'Kart desteleri',
            '/flashcard?deck={id}', 'Layers',
        ),
        EntityTypeSpec(
            'flashcard_card', 'Kart', 'Kartlar', '/flashcard', 'Layers',
            linkable=False,
        ),
    ],
    event_verbs=[
        "flashcard.deck_created", "flashcard.card_added",
        "flashcard.reviewed", "flashcard.imported",
    ],
)
