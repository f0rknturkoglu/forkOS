"""V2 operations join the existing Studio transaction; no independent commits."""

from sqlalchemy import select

from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity
from app.modules.goal import roadmap
from app.modules.goal.package_schemas import (
    ConnectRecord,
    EditNode,
    EditTask,
    NewArea,
    NewNode,
    NewResource,
    NewTask,
    NewTopic,
    ScheduleTask,
)
from app.modules.goal.roadmap_models import GoalRoadmapNode
from app.modules.learning import service as learning
from app.modules.learning.schemas import AreaIn, ResourceIn, TopicIn
from app.modules.todo import service as todos
from app.modules.todo.models import PlanSlot
from app.modules.todo.schemas import PlanSlotIn, TodoIn, TodoUpdate


async def operation(db, op, ref):
    if isinstance(op, NewArea):
        result = await learning.create_area(db, AreaIn(**op.data.model_dump()), commit=False)
        return result["id"]
    if isinstance(op, NewTopic):
        result = await learning.create_topic(
            db,
            TopicIn(
                area_id=ref(op.area_ref),
                parent_id=ref(op.parent_ref) if op.parent_ref else None,
                **op.data.model_dump(exclude={"description"}),
            ),
            commit=False,
        )
        if op.data.description:
            await learning.create_resource(
                db,
                result["id"],
                ResourceIn(title="Çalışma açıklaması", kind="doc", note=op.data.description),
                commit=False,
            )
        return result["id"]
    if isinstance(op, NewResource):
        result = await learning.create_resource(
            db, ref(op.topic_ref), ResourceIn(**op.data.model_dump()), commit=False
        )
        return result["id"]
    if isinstance(op, NewTask):
        result = await todos.create(
            db,
            TodoIn(
                **op.data.model_dump(), project_id=ref(op.project_ref) if op.project_ref else None
            ),
            commit=False,
        )
        if op.topic_ref:
            await connect(db, result.id, ref(op.topic_ref), "prepares_for")
        return result.id
    if isinstance(op, EditTask):
        result = await todos.update(
            db, op.target_id, TodoUpdate(**op.data.model_dump(exclude_unset=True)), commit=False
        )
        if not result:
            raise ValueError("Görev bulunamadı")
        await log_event(
            db,
            verb="goal.task_updated",
            entity_id=result.id,
            entity_type="todo",
            payload={"fields": sorted(op.data.model_fields_set)},
        )
        return result.id
    if isinstance(op, ScheduleTask):
        identity = ref(op.task_ref)
        entity = await db.get(Entity, identity)
        if not entity or entity.archived_at or entity.type != "todo":
            raise ValueError("Yalnız etkin görev planlanabilir")
        existing = await db.scalar(
            select(PlanSlot).where(PlanSlot.entity_id == identity, PlanSlot.day == op.data.day)
        )
        if existing and existing.id != op.replace_slot_id:
            raise ValueError("Mevcut plan sessizce değiştirilemez")
        if op.replace_slot_id:
            old = await db.get(PlanSlot, op.replace_slot_id)
            if not old or old.entity_id != identity:
                raise ValueError("Değiştirilecek plan kaydı eşleşmiyor")
            if old.google_event_id:
                raise ValueError("Google bağlantılı planı normal Planlama üzerinden değiştir")
            if existing and existing.id != old.id:
                raise ValueError("Görevin hedef günde başka planı var")
            await db.delete(old)
            await db.flush()
        slot = await todos.schedule(
            db, PlanSlotIn(entity_id=identity, **op.data.model_dump()), commit=False
        )
        return identity, slot.id
    if isinstance(op, ConnectRecord):
        a, b = ref(op.from_ref), ref(op.to_ref)
        await connect(db, a, b, op.data.relation)
        return a
    if isinstance(op, NewNode):
        node = await roadmap.save_node(
            db,
            ref(op.goal_ref),
            op.data,
            parent_id=ref(op.parent_ref) if op.parent_ref else None,
            target_id=ref(op.target_ref) if op.target_ref else None,
            depends_on=[ref(i) for i in op.depends_on],
        )
        return node.id
    if isinstance(op, EditNode):
        existing = await db.get(GoalRoadmapNode, op.target_id)
        if not existing:
            raise ValueError("Yol haritası düğümü yok")
        node = await roadmap.save_node(
            db,
            existing.goal_id,
            op.data,
            parent_id=ref(op.parent_ref) if op.parent_ref else None,
            node_id=op.target_id,
            detached=op.detached,
            depends_on=[ref(i) for i in op.depends_on] if op.depends_on is not None else None,
        )
        return node.id
    raise ValueError("Desteklenmeyen paket işlemi")


async def connect(db, a, b, relation):
    source, target = await db.get(Entity, a), await db.get(Entity, b)
    if a == b or not source or not target or source.archived_at or target.archived_at:
        raise ValueError("İlişki için etkin ve farklı kayıtlar gerekli")
    allowed = {
        "prepares_for": ({"todo"}, {"study_topic"}),
        "advances_goal": (
            {
                "todo",
                "study_topic",
                "project",
                "bookmark",
                "course",
                "learning_resource",
                "flashcard_deck",
            },
            {"goal"},
        ),
        "advances_goal_milestone": ({"todo", "study_topic", "project"}, {"goal_milestone"}),
        "belongs_to": ({"todo"}, {"project"}),
        "learns_from": (
            {"study_topic"},
            {"bookmark", "learning_resource", "course", "flashcard_deck"},
        ),
        "references": (
            {"goal", "goal_roadmap_node", "study_topic"},
            {"bookmark", "course", "learning_resource", "flashcard_deck"},
        ),
    }
    if source.type not in allowed[relation][0] or target.type not in allowed[relation][1]:
        raise ValueError("İlişki kayıt türleriyle uyumlu değil")
    if relation == "learns_from" and target.type == "bookmark":
        await learning.attach_bookmark(db, a, b, commit=False)
        return
    await link(db, a, b, relation)
    await log_event(
        db,
        verb="link.created",
        entity_id=a,
        entity_type=source.type,
        payload={"to_id": str(b), "relation": relation},
    )
