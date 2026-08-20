from app.modules.review.router import router


def _spec():
    from app.modules import ModuleSpec
    return ModuleSpec(id="review", title="Reviews", router=router,
                      entity_types=["review"], event_verbs=["review.completed"])


MODULE = _spec()
