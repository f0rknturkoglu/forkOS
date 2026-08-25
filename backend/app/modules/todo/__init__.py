from app.modules.todo.router import router
from app.modules.todo.service import deadline_provider as todo_deadlines


def _spec():
    from app.modules import EntityTypeSpec, ModuleSpec
    return ModuleSpec(id="todo", title="Todo & Planner", router=router,
                      entity_types=[EntityTypeSpec(
            'todo', 'Görev', 'Görevler', '/todos?focus={id}', 'ListChecks',
        )], event_verbs=[
                          "todo.created", "todo.completed", "todo.dropped",
                          "todo.rescheduled", "plan.scheduled",
                          "plan.rescheduled", "plan.unscheduled"],
        deadline_provider=todo_deadlines)


MODULE = _spec()
