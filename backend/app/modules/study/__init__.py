from app.modules import ModuleSpec
from app.modules.study.router import router

MODULE = ModuleSpec(
    id="study",
    title="Study",
    router=router,
    entity_types=["study_area", "study_topic"],
    event_verbs=["study.topic_completed", "study.confidence_changed"],
)
