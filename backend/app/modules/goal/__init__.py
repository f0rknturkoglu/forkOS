from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.goal.router import router
from app.modules.goal.service import deadline_provider

MODULE = ModuleSpec(
    id="goal",
    title="Goals",
    router=router,
    entity_types=[
        EntityTypeSpec(
            "strategic_plan", "Stratejik plan", "Stratejik planlar", "/goals?entity={id}", "Compass"
        ),
        EntityTypeSpec(
            "strategic_pillar",
            "Stratejik alan",
            "Stratejik alanlar",
            "/goals?entity={id}",
            "Layers",
        ),
        EntityTypeSpec(
            "strategic_plan_revision",
            "Plan revizyonu",
            "Plan revizyonları",
            "/goals?view=history&entity={id}",
            "History",
            linkable=False,
        ),
        EntityTypeSpec(
            "key_result",
            "Ölçülebilir sonuç",
            "Ölçülebilir sonuçlar",
            "/goals?entity={id}",
            "TrendingUp",
        ),
        EntityTypeSpec("goal", "Hedef", "Hedefler", "/goals?entity={id}", "Target", linkable=True),
        EntityTypeSpec(
            "goal_milestone",
            "Hedef kilometre taşı",
            "Hedef kilometre taşları",
            "/goals?entity={id}",
            "Flag",
            linkable=True,
        ),
    ],
    event_verbs=[
        "strategic_plan.created",
        "strategic_plan.updated",
        "strategic_plan.revised",
        "strategic_pillar.created",
        "strategic_pillar.updated",
        "key_result.created",
        "key_result.updated",
        "key_result.manual_value_updated",
        "goal.created",
        "goal.updated",
        "goal.milestone_added",
        "goal.milestone_updated",
    ],
    deadline_provider=deadline_provider,
)
