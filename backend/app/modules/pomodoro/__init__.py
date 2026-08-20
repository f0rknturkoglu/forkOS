from app.modules.pomodoro.router import router


def _spec():
    from app.modules import ModuleSpec
    return ModuleSpec(id="pomodoro", title="Pomodoro", router=router,
                      entity_types=["pomodoro_session"],
                      event_verbs=["pomodoro.completed", "pomodoro.interrupted"])


MODULE = _spec()
