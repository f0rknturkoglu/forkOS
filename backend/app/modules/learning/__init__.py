from app.modules import ModuleSpec
from app.modules.learning.router import router

MODULE = ModuleSpec(
    id="learning",
    title="Learning",
    router=router,
    entity_types=["course", "book"],
    event_verbs=["course.progressed", "course.completed", "book.finished"],
)
