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
        event_verbs=["media.item_added", "media.status_changed", "media.item_deleted"],
    )


MODULE = _spec()
