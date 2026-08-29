from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.learning.router import router

MODULE = ModuleSpec(
    id="learning",
    title="Learning",
    router=router,
    entity_types=[
        EntityTypeSpec('course', 'Kurs', 'Kurslar', '/learning', 'GraduationCap',
        linkable=False),
        EntityTypeSpec('study_area', 'Çalışma alanı',
                       'Çalışma alanları', '/learning', 'FolderOpen',
        linkable=False),
        EntityTypeSpec('study_topic', 'Çalışma konusu',
                       'Çalışma konuları', '/learning', 'BookOpen'),
    ],
    event_verbs=[
        "course.progressed", "course.completed",
        "study.topic_completed", "study.confidence_changed",
        "study.topic_deleted", "study.area_deleted",
    ],
)
