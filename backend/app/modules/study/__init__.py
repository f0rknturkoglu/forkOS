from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.study.router import router

MODULE = ModuleSpec(
    id="study",
    title="Study",
    router=router,
    entity_types=[EntityTypeSpec(
            'study_area', 'Çalışma alanı', 'Çalışma alanları', '/study?focus={id}', 'FolderOpen',
        ),
        EntityTypeSpec(
            'study_topic', 'Çalışma konusu', 'Çalışma konuları', '/study?focus={id}', 'BookOpen',
        )],
    event_verbs=["study.topic_completed", "study.confidence_changed"],
)
