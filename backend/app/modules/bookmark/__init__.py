from app.modules.bookmark.router import router


def _spec():
    from app.modules import EntityTypeSpec, ModuleSpec
    return ModuleSpec(
        id="bookmark",
        title="Bookmarks & Inbox",
        router=router,
        entity_types=[EntityTypeSpec(
            'bookmark', 'Yer imi', 'Yer imleri', '/bookmarks?focus={id}', 'Bookmark',
        )],
        event_verbs=["bookmark.saved", "bookmark.moved", "bookmark.read",
                     "bookmark.favorited", "bookmark.deleted"],
    )


MODULE = _spec()
