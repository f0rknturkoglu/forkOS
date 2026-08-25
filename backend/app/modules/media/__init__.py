from app.modules.media.router import router
from app.modules.media.service import deadline_provider as media_deadlines


def _spec():
    from app.modules import EntityTypeSpec, ModuleSpec

    return ModuleSpec(id="media",
        title="Medya",
        router=router,
        entity_types=[
            EntityTypeSpec('media_item', 'Medya', 'Medyalar', '/media/{id}', 'Film'),
            EntityTypeSpec('media_collection', 'Koleksiyon', 'Koleksiyonlar', '/media/collections', 'Library'),
            EntityTypeSpec('media_unit', 'Bölüm', 'Bölümler', '/media', 'FileVideo'),
            EntityTypeSpec('media_cycle', 'Döngü', 'Döngüler', '/media', 'RefreshCw'),
            EntityTypeSpec('media_consumption', 'Tüketim', 'Tüketimler', '/media', 'Play'),
        ],
        event_verbs=[
            "media.item_added",
            "media.item_updated",
            "media.item_trashed",
            "media.item_restored",
            "media.item_deleted",
            "media.cycle_started",
            "media.cycle_completed",
            "media.cycle_reopened",
            "media.consumed",
            "media.progress_corrected",
            "media.collection_created",
            "media.collection_updated",
            "media.collection_deleted",
            "media.collection_item_added",
            "media.collection_item_removed",
            "media.release_discovered",
            "media.sync_completed",
            "media.sync_failed",
            "media.sync_empty",
        ],
        deadline_provider=media_deadlines,
    )


MODULE = _spec()
