"""Semantic package draft -> stable typed operations; no model-supplied database IDs."""

import re
from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator

from app.modules.goal.package_planning import propose
from app.modules.goal.package_schemas import Closed, PlanningConstraints
from app.modules.goal.studio_schemas import StudioProposal


class Outcome(Closed):
    title: str = Field(min_length=1, max_length=200)
    target_value: Decimal
    baseline_value: Decimal = Decimal(0)
    unit: str = Field("adet", max_length=60)

    @model_validator(mode="after")
    def unmeasured_baseline(self):
        if self.baseline_value != 0:
            raise ValueError(
                "Model ölçülmüş başlangıç puanı üretemez; baseline yalnız sıfır hesap referansıdır"
            )
        return self


class Topic(Closed):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(None, max_length=1500)
    parent_index: int | None = Field(None, ge=0, le=39)
    resources: list[str] = Field(default_factory=list, max_length=5)
    resource_needs: list[str] = Field(default_factory=list, max_length=3)
    reuse: str | None = Field(None, pattern=r"^candidate_[0-9]{1,2}$")


class Task(Closed):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(None, max_length=1500)
    duration_min: int = Field(30, ge=1, le=480)
    due_date: date | None = None
    topic_index: int | None = Field(None, ge=0, le=39)
    existing_topic: str | None = Field(None, pattern=r"^candidate_[0-9]{1,2}$")
    new_topic_title: str | None = Field(None, min_length=1, max_length=300)
    reuse: str | None = Field(None, pattern=r"^candidate_[0-9]{1,2}$")


class Phase(Closed):
    attach_node_index: int | None = Field(None, ge=0, le=59)
    due_date: date | None = None
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(None, max_length=1500)
    milestone: str | None = Field(None, min_length=1, max_length=300)
    completion_gate: bool = False
    depends_on: list[int] = Field(default_factory=list, max_length=8)
    topics: list[Topic] = Field(default_factory=list, max_length=8)
    tasks: list[Task] = Field(default_factory=list, max_length=6)


class Child(Closed):
    reuse: str | None = Field(None, pattern=r"^candidate_[0-9]{1,2}$")
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(None, max_length=1500)
    period: str = Field(min_length=1, max_length=100)
    target_date: date | None = None
    phases: list[Phase] = Field(default_factory=list, max_length=8)


class TaskChange(Closed):
    task: str = Field(pattern=r"^candidate_[0-9]{1,2}$")
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = Field(None, max_length=5000)
    priority: int | None = Field(None, ge=0, le=3)
    due_date: date | None = None


class NodeChange(Closed):
    node_index: int = Field(ge=0, le=59)
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = Field(None, max_length=3000)
    parent_index: int | None = Field(None, ge=0, le=59)
    detached: bool = False
    depends_on_indexes: list[int] | None = Field(None, max_length=12)
    due_date: date | None = None


class ScheduleChange(Closed):
    task: str = Field(pattern=r"^candidate_[0-9]{1,2}$")
    day: date
    from_day: date | None = None
    duration_min: int = Field(30, ge=1, le=480)


class TopicResources(Closed):
    topic: str = Field(pattern=r"^candidate_[0-9]{1,2}$")
    sources: list[str] = Field(default_factory=list, max_length=5)
    resource_needs: list[str] = Field(default_factory=list, max_length=3)


class RecordAttachment(Closed):
    record: str = Field(pattern=r"^candidate_[0-9]{1,2}$")
    parent_index: int | None = Field(None, ge=0, le=59)


class PackageDraft(Closed):
    preserve_goal_metadata: bool = False
    kind: Literal["package"]
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(None, max_length=3000)
    target_date: date | None = None
    long_term: bool = False
    outcome: Outcome | None = None
    acceptance_criterion: str | None = Field(None, min_length=1, max_length=300)
    learning_area: str | None = Field(None, max_length=100)
    reuse_area: str | None = Field(None, pattern=r"^candidate_[0-9]{1,2}$")
    topic_resources: list[TopicResources] = Field(default_factory=list, max_length=8)
    record_attachments: list[RecordAttachment] = Field(default_factory=list, max_length=8)
    task_changes: list[TaskChange] = Field(default_factory=list, max_length=20)
    node_changes: list[NodeChange] = Field(default_factory=list, max_length=20)
    schedule_changes: list[ScheduleChange] = Field(default_factory=list, max_length=20)
    projects: list[Annotated[str, Field(pattern=r"^candidate_[0-9]{1,2}$")]] = Field(
        default_factory=list, max_length=5
    )
    phases: list[Phase] = Field(default_factory=list, max_length=8)
    children: list[Child] = Field(default_factory=list, max_length=8)
    planning: PlanningConstraints = Field(default_factory=PlanningConstraints)
    assumptions: list[str] = Field(default_factory=list, max_length=12)
    missing_information: list[str] = Field(default_factory=list, max_length=12)
    warnings: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def scope(self):
        import re

        for note in self.assumptions:
            if not re.search(r"bilinm|bilinme|unknown|not known", note.casefold()) and re.search(
                r"(?:mevcut|şu anki|current|initial|kullanıcı|user).*(?:seviye|puan|score|proficiency|level)",
                note.casefold(),
            ):
                raise ValueError(
                    "Mevcut seviye veya puan için varsayım yapılamaz; bilinmiyor olarak belirt"
                )
        if self.long_term and not self.children:
            raise ValueError("Uzun vadeli paket dönemlere bağlı alt hedefler içermeli")
        dated = [c.target_date for c in self.children if c.target_date]
        if dated != sorted(dated) or any(self.target_date and d > self.target_date for d in dated):
            raise ValueError("Dönem tarihleri kronolojik ve ana hedefin tarihi içinde olmalı")
        phase_sets = [self.phases, *[c.phases for c in self.children]]
        task_titles, topic_titles = set(), set()
        count = 0
        for phases in phase_sets:
            phase_titles = set()
            for i, p in enumerate(phases):
                normalized_phase = p.title.strip().casefold()
                if not normalized_phase or normalized_phase in phase_titles:
                    raise ValueError("Aşama başlığı boş veya aynı kapsamda tekrar olamaz")
                phase_titles.add(normalized_phase)
                if p.completion_gate and not p.milestone:
                    raise ValueError("Sonuç kapısı açık bir kabul kriteri/milestone gerektirir")
                if any(d < 0 or d >= i for d in p.depends_on):
                    raise ValueError("Ön koşullar önceki aşamalara bağlanmalı; döngü olamaz")
                for j, t in enumerate(p.topics):
                    if t.parent_index is not None and t.parent_index >= j:
                        raise ValueError("Konu üstü önce tanımlanmalı")
                    normalized = t.title.casefold().strip()
                    if normalized in topic_titles and not t.reuse:
                        raise ValueError("Paket içinde aynı öğrenme konusu tekrarlanamaz")
                    topic_titles.add(normalized)
                for t in p.tasks:
                    if (
                        sum(
                            v is not None
                            for v in (t.topic_index, t.existing_topic, t.new_topic_title)
                        )
                        > 1
                    ):
                        raise ValueError("Görev tek bir doğrulanmış öğrenme konusuna bağlanabilir")
                    if t.topic_index is not None and t.topic_index >= len(p.topics):
                        raise ValueError("Görevin öğrenme konusu yok")
                    normalized = t.title.casefold().strip()
                    if normalized in task_titles and not t.reuse:
                        raise ValueError("Paket içinde aynı görev tekrarlanamaz")
                    task_titles.add(normalized)
                    count += 1
        if count > 20:
            raise ValueError("İlk paket en fazla 20 yakın dönem görev içerebilir")
        return self


def stamp(day):
    return datetime.combine(day, time.min, ZoneInfo("Europe/Istanbul")).isoformat() if day else None


def instructions(*, existing=False, long_term=False, add_tasks=None):
    from app.modules.goal.studio_inference import authoring_prompt

    return authoring_prompt(existing=existing, long_term=long_term, add_tasks=add_tasks)


def user_capacity(data):
    import re

    numbers = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8}
    messages = [m["text"] for m in data.get("messages", []) if m.get("role") == "user"]
    for message in reversed(messages):
        match = re.search(
            r"(?:günde|günlük|her gün)\s+(\d+(?:[.,]\d+)?|bir|iki|üç|dört|beş|altı|yedi|sekiz)\s*(saat|dakika)",
            message.casefold().replace("i\u0307", "i"),
        )
        if match:
            number = numbers.get(match[1]) or float(match[1].replace(",", "."))
            return int(number * (60 if match[2] == "saat" else 1))
    return None


async def compile_draft(
    db,
    value,
    *,
    goal_id=None,
    candidates=(),
    target_date=None,
    long_term=False,
    planning_default=None,
    confirmed_capacity=None,
    confirmed_availability=None,
    roadmap_snapshot=None,
    task_snapshot=None,
    allowed_dates=None,
    expected_new_tasks=None,
    expected_outcome_target=None,
    expected_learning=False,
    skip_scheduling=False,
):
    draft = PackageDraft.model_validate(value)
    if draft.preserve_goal_metadata and not goal_id:
        raise ValueError("Kısmi revizyon mevcut hedef gerektirir")
    if (
        expected_learning
        and not goal_id
        and not any(
            p.topics for p in [*draft.phases, *[p for c in draft.children for p in c.phases]]
        )
    ):
        raise ValueError(
            "Kullanıcı öğrenme çalışması istedi; taslak anlamlı Learning konuları içermeli"
        )
    if expected_outcome_target is not None and (
        (not goal_id and draft.outcome is None)
        or draft.outcome
        and draft.outcome.target_value != expected_outcome_target
    ):
        raise ValueError("Kullanıcının açık sayısal hedefi aynen korunmalı")
    if goal_id:
        from uuid import UUID

        goal_id = UUID(str(goal_id))
    if (
        not goal_id
        and draft.long_term
        and draft.children
        and any(
            p.tasks for p in [*draft.phases, *[p for c in draft.children[1:] for p in c.phases]]
        )
    ):
        raise ValueError(
            "Uzun vadeli hedefte ayrıntılı görevler yalnız ilk dönem alt hedefinde olabilir; ana hedefte ve gelecek dönemlerde tasks boş olmalı. children dönem alt hedefleri demektir, insan çocukları veya çocuk gelişimi değildir."
        )
    if planning_default:
        draft.planning = PlanningConstraints.model_validate(planning_default)
    else:
        draft.planning.capacity_confirmed = False
        # Model-invented time windows or weekdays cannot become facts.
        draft.planning.available_start_min = None
        draft.planning.available_end_min = None
        draft.planning.weekdays = list(range(7))
        draft.planning.unavailable_days = []
    if confirmed_capacity:
        draft.planning.daily_capacity_min = confirmed_capacity
        draft.planning.capacity_confirmed = True
    if confirmed_availability:
        draft.planning = PlanningConstraints.model_validate(
            {**draft.planning.model_dump(), **confirmed_availability}
        )
    if not goal_id and not (
        draft.projects
        or any(c.reuse for c in draft.children)
        or any(
            p.tasks or p.topics
            for p in [*draft.phases, *[p for c in draft.children for p in c.phases]]
        )
    ):
        raise ValueError(
            "Yeni plan somut görev, öğrenme çalışması veya doğrulanmış mevcut proje/hedef içermeli"
        )
    if long_term and not goal_id and not draft.long_term:
        raise ValueError("Uzun vadeli tercih için dönemli paket gerekli")
    if allowed_dates is not None:
        dates = [
            draft.target_date,
            *[c.target_date for c in draft.children],
            *[p.due_date for p in [*draft.phases, *[p for c in draft.children for p in c.phases]]],
            *[
                t.due_date
                for p in [*draft.phases, *[p for c in draft.children for p in c.phases]]
                for t in p.tasks
            ],
            *[c.due_date for c in draft.task_changes],
            *[c.due_date for c in draft.node_changes],
        ]
        if any(day and day not in allowed_dates for day in dates):
            raise ValueError(
                "Kullanıcının belirtmediği hedef/teslim tarihi önerilemez; bilinmeyen tarihleri null bırak. Çalışma günleri ayrı takvim planıdır."
            )
    ops, tasks_to_plan = [], []
    candidate_map = {c["token"]: c for c in candidates}
    from app.modules.goal.package_resolution import load

    resolved = await load(db, candidates)
    node_map = {n["index"]: n for n in (roadmap_snapshot or [])}
    from sqlalchemy import func, select

    from app.modules.goal.roadmap_models import GoalRoadmapNode

    offsets = dict(
        (
            await db.execute(
                select(GoalRoadmapNode.goal_id, func.max(GoalRoadmapNode.position))
                .where(GoalRoadmapNode.kind.in_(["phase", "period"]))
                .group_by(GoalRoadmapNode.goal_id)
            )
        ).all()
    )

    def candidate(token, types):
        return resolved.identity(token, types)

    def add(key, type, data, **refs):
        ops.append({"key": key, "type": type, "data": data, **refs})
        return key

    goal_data = {
        "title": draft.title,
        "description": draft.description,
        "target_at": stamp(target_date or draft.target_date),
    }
    root = str(goal_id) if goal_id else "goal"
    if goal_id:
        if not (target_date or draft.target_date):
            goal_data.pop("target_at")
        if draft.description is None:
            goal_data.pop("description")
        if not draft.preserve_goal_metadata:
            add("goal_edit", "goal.update", goal_data, target_id=str(goal_id))
    else:
        add(
            root,
            "goal.create",
            {**goal_data, "horizon": "long_term" if draft.long_term else "quarter"},
        )
    if draft.outcome:
        if draft.outcome.target_value == draft.outcome.baseline_value:
            raise ValueError("Ölçüm başlangıcı ve hedefi aynı olamaz")
        existing_kr = None
        if goal_id:
            from sqlalchemy import select

            from app.core.models import Entity
            from app.modules.goal.models import KeyResult

            rows = (
                await db.scalars(
                    select(KeyResult)
                    .join(Entity, Entity.id == KeyResult.id)
                    .where(
                        KeyResult.goal_id == goal_id,
                        Entity.archived_at.is_(None),
                        Entity.title == draft.outcome.title,
                        KeyResult.source_key == "manual",
                        KeyResult.unit == draft.outcome.unit,
                    )
                    .limit(2)
                )
            ).all()
            if len(rows) == 1:
                existing_kr = rows[0].id
        add(
            "outcome",
            "key_result.save",
            {
                **draft.outcome.model_dump(mode="json"),
                "direction": "increase"
                if draft.outcome.target_value > draft.outcome.baseline_value
                else "decrease",
                "source_key": "manual",
            },
            goal_ref=root,
            target_id=str(existing_kr) if existing_kr else None,
        )
    if draft.acceptance_criterion:
        criterion = add(
            "acceptance", "milestone.create", {"title": draft.acceptance_criterion}, goal_ref=root
        )
        add(
            "acceptance_node",
            "roadmap.create",
            {"title": draft.acceptance_criterion, "kind": "milestone", "completion_gate": True},
            goal_ref=root,
            target_ref=criterion,
        )
    all_phases = [*draft.phases, *[p for c in draft.children for p in c.phases]]
    has_topics = any(p.topics for p in all_phases)
    area_match = draft.reuse_area or resolved.exact(
        draft.learning_area or draft.title[:100], "study_area"
    )
    area = candidate(area_match, {"study_area"}) if area_match else None
    if has_topics and not area:
        area = add("area", "learning.area", {"title": draft.learning_area or draft.title[:100]})
    project_ids = [candidate(t, {"project"}) for t in draft.projects]
    for j, pid in enumerate(project_ids):
        add(
            f"project_node_{j}",
            "roadmap.create",
            {"title": candidate_map[draft.projects[j]]["title"], "kind": "record"},
            goal_ref=root,
            target_ref=pid,
        )

    async def phases_for(phases, goal_ref, prefix):
        from uuid import UUID

        offset = offsets.get(UUID(goal_ref), -1) + 1 if len(goal_ref) == 36 else 0
        phase_refs = []
        pending_tasks = []
        named_topics = {}
        for i, p in enumerate(phases):
            matches = [
                n
                for n in node_map.values()
                if n.get("persisted")
                and n["kind"] in {"phase", "period"}
                and n["title"].strip().casefold() == p.title.strip().casefold()
            ]
            if goal_id and p.attach_node_index is None and matches:
                raise ValueError(
                    f"Mevcut aşama yeniden oluşturulamaz: {p.title}. attach_node_index={matches[0]['index']} kullan ve yalnız yeni istenen görevleri ekle. Eski konuları/görevleri/kaynakları tekrar yazma."
                )
            phase = add(
                f"{prefix}phase_{i}",
                "roadmap.create",
                {
                    "title": p.title,
                    "kind": "phase",
                    "description": p.description,
                    "position": offset + i,
                },
                goal_ref=goal_ref,
                depends_on=[phase_refs[d] for d in p.depends_on],
            )
            if p.attach_node_index is not None:
                existing_node = node_map.get(p.attach_node_index)
                if (
                    not goal_id
                    or not existing_node
                    or not existing_node.get("persisted")
                    or existing_node["kind"] not in {"phase", "period"}
                ):
                    raise ValueError("Eklenecek aşama hedefin doğrulanmış bağlamında olmalı")
                from uuid import UUID

                from app.core.models import Entity

                owner = await db.get(GoalRoadmapNode, UUID(existing_node["id"]))
                owner_entity = await db.get(Entity, UUID(existing_node["id"]))
                if (
                    not owner
                    or str(owner.goal_id) != goal_ref
                    or owner.detached
                    or not owner_entity
                    or owner_entity.archived_at
                    or (
                        existing_node.get("updated_at")
                        and owner_entity.updated_at
                        != datetime.fromisoformat(
                            existing_node["updated_at"].replace("Z", "+00:00")
                        )
                    )
                ):
                    raise ValueError("Eklenecek aşama değişmiş veya başka hedefe ait")
                if p.depends_on:
                    raise ValueError("Mevcut aşama ön koşulları node_changes ile düzenlenmeli")
                ops.pop()
                phase = str(existing_node["id"])
            phase_refs.append(phase)
            step_node = phase
            if p.milestone:
                milestone = add(
                    f"{prefix}step_{i}",
                    "milestone.create",
                    {"title": p.milestone, "due_at": stamp(p.due_date)},
                    goal_ref=goal_ref,
                )
                step_node = add(
                    f"{prefix}gate_{i}",
                    "roadmap.create",
                    {
                        "title": p.milestone,
                        "kind": "milestone",
                        "completion_gate": p.completion_gate,
                    },
                    goal_ref=goal_ref,
                    parent_ref=phase,
                    target_ref=milestone,
                )
            topic_refs = []
            for j, t in enumerate(p.topics):
                topic_parent = topic_refs[t.parent_index] if t.parent_index is not None else None
                reuse = t.reuse or resolved.exact(
                    t.title, "study_topic", area=area, parent=topic_parent
                )
                ref = (
                    candidate(reuse, {"study_topic"})
                    if reuse
                    else add(
                        f"{prefix}topic_{i}_{j}",
                        "learning.topic",
                        {"title": t.title, "description": t.description},
                        area_ref=area,
                        parent_ref=topic_refs[t.parent_index]
                        if t.parent_index is not None
                        else None,
                    )
                )
                topic_refs.append(ref)
                named_topics[t.title.casefold().strip()] = ref
                add(
                    f"{prefix}tn_{i}_{j}",
                    "roadmap.create",
                    {"title": t.title, "kind": "record", "position": j},
                    goal_ref=goal_ref,
                    parent_ref=f"{prefix}tn_{i}_{t.parent_index}"
                    if t.parent_index is not None
                    else step_node,
                    target_ref=ref,
                )
                for k, token in enumerate(t.resources):
                    resource = candidate(
                        token, {"bookmark", "course", "learning_resource", "flashcard_deck"}
                    )
                    add(
                        f"{prefix}rl_{i}_{j}_{k}",
                        "record.link",
                        {"relation": "learns_from"},
                        from_ref=ref,
                        to_ref=resource,
                    )
                for k, need in enumerate(t.resource_needs):
                    add(
                        f"{prefix}rn_{i}_{j}_{k}",
                        "learning.resource",
                        {
                            "title": need[:300],
                            "kind": "exercise",
                            "note": "Henüz seçilmemiş kaynak ihtiyacı; doğrulanmış dış bağlantı yok.",
                        },
                        topic_ref=ref,
                    )
            pending_tasks.append((i, p, list(topic_refs), step_node))
        for i, p, topic_refs, step_node in pending_tasks:
            for j, t in enumerate(p.tasks):
                if (
                    goal_id
                    and not t.reuse
                    and any(
                        existing["title"].strip().casefold() == t.title.strip().casefold()
                        for existing in (task_snapshot or [])
                    )
                ):
                    raise ValueError(
                        f"Mevcut görev yeniden oluşturulamaz: {t.title}. İstenen yeni pratikler için farklı, somut görevler öner; mevcut görevi değiştirmek için task_changes kullan."
                    )
                topic_ref = (
                    topic_refs[t.topic_index]
                    if t.topic_index is not None
                    else candidate(t.existing_topic, {"study_topic"})
                    if t.existing_topic
                    else named_topics.get(t.new_topic_title.casefold().strip())
                    if t.new_topic_title
                    else None
                )
                if t.new_topic_title and not topic_ref:
                    raise ValueError(
                        "Görevin adlandırılmış öğrenme konusu bu çalışma kapsamında yok"
                    )
                reuse = t.reuse or resolved.exact(
                    t.title,
                    "todo",
                    topic=topic_ref,
                    project=project_ids[0] if project_ids else None,
                    description=t.description,
                )
                ref = (
                    candidate(reuse, {"todo"})
                    if reuse
                    else add(
                        f"{prefix}task_{i}_{j}",
                        "todo.create",
                        {
                            "title": t.title,
                            "description": t.description,
                            "due_at": stamp(t.due_date),
                        },
                        topic_ref=topic_ref,
                        project_ref=project_ids[0] if project_ids else None,
                    )
                )
                if reuse and topic_ref:
                    add(
                        f"{prefix}prep_{i}_{j}",
                        "record.link",
                        {"relation": "prepares_for"},
                        from_ref=ref,
                        to_ref=topic_ref,
                    )
                add(
                    f"{prefix}taskn_{i}_{j}",
                    "roadmap.create",
                    {"title": t.title, "kind": "record", "position": j},
                    goal_ref=goal_ref,
                    parent_ref=step_node,
                    target_ref=ref,
                )
                if not reuse:
                    tasks_to_plan.append((ref, t.duration_min))

    await phases_for(draft.phases, root, "")
    for i, c in enumerate(draft.children):
        child = (
            candidate(c.reuse, {"goal"})
            if c.reuse
            else add(
                f"child_{i}",
                "goal.create",
                {"title": c.title, "description": c.description, "target_at": stamp(c.target_date)},
                parent_ref=root,
            )
        )
        period = add(
            f"period_{i}",
            "roadmap.create",
            {"title": c.period, "kind": "period", "position": i},
            goal_ref=root,
        )
        add(
            f"childn_{i}",
            "roadmap.create",
            {"title": c.title, "kind": "child_goal"},
            goal_ref=root,
            parent_ref=period,
            target_ref=child,
        )
        await phases_for(c.phases, child, f"c{i}_")
    from app.core.models import Entity

    for i, attachment in enumerate(draft.record_attachments):
        if not goal_id:
            raise ValueError("Kayıt bağlama mevcut hedef gerektirir")
        rid = candidate(attachment.record, {"todo", "study_topic", "project"})
        if any(n.get("target_id") == rid for n in (roadmap_snapshot or [])):
            raise ValueError("Kayıt zaten bu hedefte; mevcut bağını kullan")
        parent = None
        if attachment.parent_index is not None:
            node = node_map.get(attachment.parent_index)
            if not node or node.get("kind") not in {"phase", "period"} or node.get("detached"):
                raise ValueError("Bağlanacak aşama hedefin etkin bağlamında olmalı")
            current_parent = await db.get(GoalRoadmapNode, node["id"])
            parent_entity = await db.get(Entity, node["id"])
            if (
                not current_parent
                or current_parent.goal_id != goal_id
                or current_parent.detached
                or not parent_entity
                or parent_entity.archived_at
                or (
                    node.get("updated_at")
                    and parent_entity.updated_at
                    != datetime.fromisoformat(node["updated_at"].replace("Z", "+00:00"))
                )
            ):
                raise ValueError("Bağlanacak aşama değişmiş; güncel hedefi yeniden oku")
            parent = str(node["id"])
        add(
            f"attach_{i}",
            "roadmap.create",
            {"title": candidate_map[attachment.record]["title"], "kind": "record"},
            goal_ref=root,
            parent_ref=parent,
            target_ref=rid,
        )
    for i, change in enumerate(draft.topic_resources):
        tid = candidate(change.topic, {"study_topic"})
        if not goal_id or not any(
            n.get("target_id") == tid and not n.get("detached") for n in (roadmap_snapshot or [])
        ):
            raise ValueError("Kaynak hedefin etkin öğrenme konusuna eklenebilir")
        active_topic_node = await db.scalar(
            select(GoalRoadmapNode.id)
            .join(Entity, Entity.id == GoalRoadmapNode.id)
            .where(
                GoalRoadmapNode.goal_id == goal_id,
                GoalRoadmapNode.target_id == tid,
                GoalRoadmapNode.detached.is_(False),
                Entity.archived_at.is_(None),
            )
        )
        if not active_topic_node:
            raise ValueError("Kaynak konusunun hedef bağlantısı değişmiş; hedefi yeniden oku")
        if not change.sources and not change.resource_needs:
            raise ValueError("Kaynak eklemesi boş olamaz")
        for j, token in enumerate(change.sources):
            resource = candidate(
                token, {"bookmark", "course", "learning_resource", "flashcard_deck"}
            )
            add(
                f"resource_link_{i}_{j}",
                "record.link",
                {"relation": "learns_from"},
                from_ref=tid,
                to_ref=resource,
            )
        for j, need in enumerate(change.resource_needs):
            if (
                not need.strip()
                or len(need) > 300
                or re.search(r"https?://|www\.", need, flags=re.I)
            ):
                raise ValueError("Kaynak ihtiyacı kısa ve bağlantısız olmalı")
            add(
                f"resource_need_{i}_{j}",
                "learning.resource",
                {
                    "title": need,
                    "kind": "exercise",
                    "note": "Henüz seçilmemiş kaynak ihtiyacı; doğrulanmış dış bağlantı yok.",
                },
                topic_ref=tid,
            )
    for i, change in enumerate(draft.task_changes):
        tid = candidate(change.task, {"todo"})
        if not goal_id or tid not in {str(t["id"]) for t in (task_snapshot or [])}:
            raise ValueError("Görev düzenlemesi yalnız bu hedefin mevcut çalışmalarında olabilir")
        data = {
            k: getattr(change, k) for k in change.model_fields_set if k not in {"task", "due_date"}
        }
        if "due_date" in change.model_fields_set:
            data["due_at"] = stamp(change.due_date)
        if not data:
            raise ValueError("Görev düzenlemesi boş olamaz")
        add(f"task_edit_{i}", "todo.update", data, target_id=tid)
    node_map = {n["index"]: n for n in (roadmap_snapshot or [])}
    from app.core.models import Entity
    from app.modules.goal.roadmap_models import GoalRoadmapNode

    for i, change in enumerate(draft.node_changes):
        node = node_map.get(change.node_index)
        if not goal_id or not node or not node.get("persisted"):
            raise ValueError("Düzenlenecek adım hedefin doğrulanmış bağlamında olmalı")
        current = await db.get(GoalRoadmapNode, node["id"])
        entity = await db.get(Entity, node["id"])
        if (
            not current
            or current.goal_id != goal_id
            or not entity
            or entity.archived_at
            or (
                node.get("updated_at")
                and entity.updated_at
                != datetime.fromisoformat(node["updated_at"].replace("Z", "+00:00"))
            )
        ):
            raise ValueError("Yol haritası adımı değişmiş; hedefi yeniden oku")
        data = {
            "title": entity.title,
            **{
                k: getattr(current, k)
                for k in (
                    "kind",
                    "description",
                    "position",
                    "weight",
                    "progress_bearing",
                    "completion_gate",
                )
            },
        }
        for field in ("title", "description"):
            if field in change.model_fields_set:
                data[field] = getattr(change, field)

        def resolve(index):
            parent = node_map.get(index)
            if not parent or not parent.get("persisted"):
                raise ValueError("Adım bağlantısı bağlamda doğrulanamıyor")
            return str(parent["id"])

        parent = (
            resolve(change.parent_index)
            if change.parent_index is not None
            else (None if "parent_index" in change.model_fields_set else node.get("parent_id"))
        )
        add(
            f"node_edit_{i}",
            "roadmap.update",
            data,
            target_id=str(node["id"]),
            parent_ref=parent,
            detached=change.detached,
            depends_on=[resolve(j) for j in change.depends_on_indexes]
            if change.depends_on_indexes is not None
            else None,
        )
        if "due_date" in change.model_fields_set:
            if node.get("target_type") != "goal_milestone":
                raise ValueError("Adım tarihi kanonik hedef adımından düzenlenebilir")
            add(
                f"step_edit_{i}",
                "milestone.update",
                {"due_at": stamp(change.due_date)},
                target_id=node["target_id"],
            )

    from sqlalchemy import select

    from app.modules.todo.models import PlanSlot

    for i, change in enumerate(draft.schedule_changes):
        tid = candidate(change.task, {"todo"})
        query = select(PlanSlot).where(PlanSlot.entity_id == tid)
        if change.from_day:
            query = query.where(PlanSlot.day == change.from_day)
        existing = (await db.scalars(query.limit(2))).all()
        if len(existing) != 1:
            raise ValueError("Taşınacak çalışma bloğu tekil olmalı; mevcut gününü belirt")
        add(
            f"move_{i}",
            "plan.schedule",
            {
                "day": change.day.isoformat(),
                "duration_min": change.duration_min
                if "duration_min" in change.model_fields_set
                else (existing[0].duration_min or 30),
                "start_min": existing[0].start_min,
                "note": existing[0].note,
            },
            task_ref=tid,
            replace_slot_id=str(existing[0].id),
        )
    slots, warnings = (
        ([], []) if skip_scheduling else await propose(db, tasks_to_plan, draft.planning)
    )
    if (
        goal_id
        and expected_new_tasks is not None
        and sum(op["type"] == "todo.create" for op in ops) != expected_new_tasks
    ):
        raise ValueError(
            f"Kullanıcı tam {expected_new_tasks} yeni görev istedi. Yalnız bu sayıda yeni somut görev öner; mevcut çalışmaları tekrar oluşturma."
        )
    ops.extend(slots)
    assumptions = list(draft.assumptions)
    if not draft.planning.capacity_confirmed:
        assumptions.append(
            f"Başlangıç için günlük {draft.planning.daily_capacity_min} dakika varsayıldı; düzenleyebilirsin."
        )
    return StudioProposal.model_validate(
        {
            "schema_version": 2,
            "rationale": draft.description or draft.title,
            "assumptions": assumptions[:12],
            "missing_information": draft.missing_information,
            "warnings": [*draft.warnings, *warnings][:12],
            "operations": ops,
            "planning": draft.planning.model_dump(mode="json"),
        }
    )
