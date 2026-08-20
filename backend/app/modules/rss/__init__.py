from app.modules.rss.router import router


def _spec():
    from app.modules import ModuleSpec
    return ModuleSpec(
        id="rss",
        title="RSS Reader",
        router=router,
        entity_types=["feed", "feed_item"],
        event_verbs=["rss.feed_added", "rss.feed_removed", "rss.items_added",
                     "rss.item_read", "rss.item_saved", "rss.marked_all_read",
                     "rss.feed_failed", "rss.feed_disabled", "rss.pruned"],
    )


MODULE = _spec()
