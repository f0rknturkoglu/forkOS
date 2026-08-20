from app.modules.habit.router import router


def _spec():
    from app.modules import ModuleSpec
    return ModuleSpec(id="habit", title="Habits", router=router,
                      entity_types=["habit"], event_verbs=["habit.checked"])


MODULE = _spec()
