from app.modules.bookmark import receipts  # noqa: F401
from app.modules.bookmark.router import router


def _spec():
    from app.modules import EntityTypeSpec, ModuleSpec

    return ModuleSpec(
        id="bookmark",
        title="Bookmarks & Inbox",
        router=router,
        entity_types=[
            EntityTypeSpec(
                "capture_receipt",
                "Capture makbuzu",
                "Capture makbuzları",
                "/bookmarks",
                "Inbox",
                searchable=False,
                linkable=False,
            ),
            EntityTypeSpec(
                "bookmark",
                "Yer imi",
                "Yer imleri",
                "/bookmarks?focus={id}",
                "Bookmark",
            ),
        ],
        event_verbs=[
            "capture.delivered",
            "bookmark.saved",
            "bookmark.moved",
            "bookmark.read",
            "bookmark.favorited",
            "bookmark.deleted",
            "bookmark.highlighted",
            "bookmark.scrolled",
        ],
    )


MODULE = _spec()
