from app.modules.review.router import router


def _spec():
    from app.modules import EntityTypeSpec, ModuleSpec
    return ModuleSpec(id="review", title="Reviews", router=router,
                      entity_types=[EntityTypeSpec(
            'review', 'Değerlendirme', 'Değerlendirmeler', '/review/daily', 'ClipboardCheck',
        linkable=False)], event_verbs=["review.completed"])


MODULE = _spec()
