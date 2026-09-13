from app.modules.pomodoro.router import router


def _spec():
    from app.modules import EntityTypeSpec, ModuleSpec
    return ModuleSpec(id="pomodoro", title="Pomodoro", router=router,
                      entity_types=[EntityTypeSpec(
            'pomodoro_session', 'Pomodoro seansı', 'Pomodoro seansları', '/pomodoro', 'Timer',
        linkable=False)],
                      event_verbs=["pomodoro.completed", "pomodoro.interrupted", "pomodoro.deleted"])


MODULE = _spec()
