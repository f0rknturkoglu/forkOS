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
                       'Çalışma konuları', '/learning?focus={id}', 'BookOpen'),
        EntityTypeSpec('learning_resource', 'Kaynak', 'Kaynaklar',
                       '/learning?resource={id}', 'Link'),
    ],
    event_verbs=[
        # Alan yasam dongusu
        "study.area_created", "study.area_archived", "study.area_reopened",
        "study.area_deleted",
        # Konu yasam dongusu
        "study.topic_created", "study.topic_renamed", "study.topic_moved",
        "study.topic_started", "study.topic_reopened", "study.topic_completed",
        "study.topic_deleted", "study.confidence_changed", "study.mastery_changed",
        "study.reviewed",
        # Kurs yasam dongusu
        "course.created", "course.started", "course.progressed", "course.completed",
        "course.reopened", "course.deleted",
        # Kaynak yasam dongusu + ice aktarma
        "learning.resource_added", "learning.resource_updated",
        "learning.resource_completed", "learning.resource_reopened",
        "learning.resource_deleted", "learning.imported",
    ],
)
