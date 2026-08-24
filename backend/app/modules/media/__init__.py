from app.modules.media.router import router


def _spec():
    from app.modules import ModuleSpec

    return ModuleSpec(
        id="media",
        title="Medya",
        router=router,
        entity_types=[
            "media_item",
            "media_unit",
            "media_cycle",
            "media_consumption",
            "media_collection",
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
    )


MODULE = _spec()
