from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.opportunity.router import router
from app.modules.opportunity.service import deadline_provider as opportunity_deadlines

MODULE = ModuleSpec(
    id="opportunity",
    title="Opportunities",
    router=router,
    entity_types=[
        EntityTypeSpec(
            "opportunity",
            "Fırsat",
            "Fırsatlar",
            "/opportunities?focus={id}",
            "Target",
        ),
        EntityTypeSpec(
            "career_story",
            "Kariyer hikâyesi",
            "Kariyer hikâyeleri",
            "/opportunities?story={id}",
            "BookOpen",
            # Gereksinim eslestirmesi kendi surumlu degerlendirme belgesinde tutulur.
            linkable=False,
        ),
        EntityTypeSpec(
            "career_connection",
            "Kariyer bağlantısı",
            "Kariyer bağlantıları",
            "/opportunities?connection={id}",
            "Users",
            # Firsat baglantisi kurum tokenlarindan dinamik uretilir; genel link degildir.
            linkable=False,
        ),
    ],
    event_verbs=[
        "opportunity.created",
        "opportunity.updated",
        "opportunity.items_added",
        "opportunity.duplicates_merged",
        "opportunity.evaluated",
        "opportunity.evaluation_updated",
        "opportunity.interview_updated",
        "opportunity.interview_deleted",
        "career_story.created",
        "career_story.updated",
        "career_story.archived",
        "career_connections.imported",
    ],
    deadline_provider=opportunity_deadlines,
)
