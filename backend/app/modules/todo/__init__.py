from app.modules.todo.router import router


def _spec():
    from app.modules import ModuleSpec
    return ModuleSpec(id="todo", title="Todo & Planner", router=router,
                      entity_types=["todo"], event_verbs=[
                          "todo.created", "todo.completed", "todo.dropped",
                          "todo.rescheduled", "plan.scheduled"])


MODULE = _spec()
