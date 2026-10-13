"""Small model-facing meanings; canonical identity and approval remain server-owned."""

import re
from datetime import timedelta
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.modules.goal.package_authoring import Outcome, PackageDraft, user_capacity
from app.modules.goal.package_constraints import (
    dates,
    deadline,
    numeric_target,
    requested_count,
    requested_tasks,
)
from app.modules.goal.package_schemas import Closed
from app.modules.goal.studio_inference import ReplyError

Need = Literal["required", "optional", "not_applicable", "unknown"]


class Needs(Closed):
    tasks: Need = "required"
    learning: Need = "unknown"
    resources: Need = "unknown"
    project: Need = "optional"
    schedule: Need = "optional"
    outcome: Need = "unknown"
    verification: Need = "unknown"
    periods: Need = "not_applicable"


class Requirements(Closed):
    objective: str = Field(min_length=1, max_length=300)
    needs: Needs
    dimensions: list[str] = Field(default_factory=list, max_length=6)
    unknowns: list[str] = Field(default_factory=list, max_length=6)
    justification: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def bounded(self):
        values = [*self.dimensions, *self.unknowns]
        if any(not s.strip() or len(s) > 240 or re.search(r"https?://", s) for s in values):
            raise ValueError("İhtiyaç açıklamaları kısa ve bağlantısız olmalı")
        if len(set(s.casefold().strip() for s in self.dimensions)) != len(self.dimensions):
            raise ValueError("İhtiyaç boyutları tekrar edemez")
        return self


def literal_constraints(data):
    text = next((m["text"] for m in reversed(data.get("messages", [])) if m["role"] == "user"), "")
    lower = text.casefold().replace("i\u0307", "i")
    excluded = []
    rules = {
        "learning": r"(?:learning|öğrenme)(?:\s+\w+){0,3}\s+(?:oluşturma|ekleme|istemiyorum|olmasın)|(?:sadece|yalnızca)\s+(?:yapılacaklar|görev|todo)",
        "project": r"proje(?:ye)?(?:\s+\w+){0,2}\s+(?:bağlama|ekleme|istemiyorum)",
        "schedule": r"takvim(?:e)?(?:\s+\w+){0,3}\s+(?:yerleştirme|ekleme|planlama)|(?:şimdilik|henüz)\s+planlama",
    }
    for name, pattern in rules.items():
        if re.search(pattern, lower):
            excluded.append(name)
    capacity_data = {
        **data,
        "messages": [
            {
                "role": "user",
                "text": re.sub(
                    r"(günde|günlük)\s+(?:en fazla|en çok|maksimum)\s+", r"\1 ", text, flags=re.I
                ),
            }
        ],
    }
    amount = numeric_target(data)
    target = deadline(data)
    return {
        "numeric_target": str(amount) if amount is not None else None,
        "target_date": target.isoformat() if target else None,
        "allowed_dates": sorted(d.isoformat() for d in dates(data)),
        "capacity_min": user_capacity(capacity_data),
        "excluded": excluded,
        "requested_tasks": requested_tasks(data),
        "requested_topics": requested_count(data, r"konu(?:su)?"),
        "requested_resources": requested_count(data, r"kaynak|kaynağı"),
        "long_term": bool(data.get("long_term"))
        or bool(re.search(r"\b(?:beş|[5-9]|on)\s+yıl(?:da|de)?\b", lower)),
        "origin": "explicit_user_request",
    }


def accepted_requirements(value, constraints):
    req = Requirements.model_validate(value)
    for excluded in constraints["excluded"]:
        setattr(req.needs, excluded, "not_applicable")
    if constraints["numeric_target"] is not None:
        req.needs.outcome = "required"
    req.needs.periods = "required" if constraints["long_term"] else "not_applicable"
    return req


class SemanticTopic(Closed):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(None, max_length=1500)
    phase: str | None = Field(None, max_length=300)
    resource_needs: list[str] = Field(default_factory=list, max_length=3)
    sources: list[str] = Field(default_factory=list, max_length=5)
    reuse: str | None = None

    @field_validator("title")
    @classmethod
    def meaningful_title(cls, value):
        if not value.strip():
            raise ValueError("Konu başlığı boş olamaz")
        return value.strip()

    @field_validator("resource_needs")
    @classmethod
    def meaningful_needs(cls, values):
        if any(not value.strip() or len(value) > 300 for value in values):
            raise ValueError("Kaynak ihtiyacı kısa ve boş olmayan bir açıklama olmalı")
        return values


class SemanticTask(Closed):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(None, max_length=1500)
    phase: str | None = Field(None, max_length=300)
    topic: str | None = Field(None, max_length=300)
    duration_min: int = Field(30, ge=1, le=480)
    reuse: str | None = None

    @field_validator("title")
    @classmethod
    def meaningful_title(cls, value):
        if not value.strip():
            raise ValueError("Görev başlığı boş olamaz")
        return value.strip()


class Period(Closed):
    title: str = Field(min_length=1, max_length=300)
    label: str = Field(min_length=1, max_length=100)
    tasks: list[SemanticTask] = Field(default_factory=list, max_length=6)
    topics: list[SemanticTopic] = Field(default_factory=list, max_length=8)


class SemanticDraft(Closed):
    kind: Literal["semantic_plan"]
    version: Literal[3] = 3
    title: str = Field(min_length=1, max_length=300)
    tasks: list[SemanticTask] = Field(default_factory=list, max_length=20)
    topics: list[SemanticTopic] = Field(default_factory=list, max_length=12)
    periods: list[Period] = Field(default_factory=list, max_length=6)
    outcome: Outcome | None = None
    acceptance_criterion: str | None = Field(None, max_length=300)
    projects: list[str] = Field(default_factory=list, max_length=5)
    unknowns: list[str] = Field(default_factory=list, max_length=8)

    def package(self, *, catalog=()):
        def phases(tasks, topics, label):
            grouped = {}

            def group(name):
                name = name or label
                return grouped.setdefault(
                    name.casefold().strip(), {"title": name, "topics": [], "tasks": []}
                )

            by_title = {}
            for topic in topics:
                key = topic.title.casefold().strip()
                if key in by_title:
                    raise ReplyError("ambiguous_topic", "Aynı konu birden çok kez tanımlanmış")
                authored_phases = {
                    t.phase
                    for t in tasks
                    if t.topic and t.topic.casefold().strip() == key and t.phase
                }
                g = group(
                    topic.phase or next(iter(authored_phases), None)
                    if len(authored_phases) <= 1
                    else topic.phase
                )
                by_title[key] = (g, len(g["topics"]))
                g["topics"].append(
                    {
                        "title": topic.title,
                        "description": topic.description,
                        "resource_needs": topic.resource_needs,
                        "resources": topic.sources,
                        **({"reuse": topic.reuse} if topic.reuse else {}),
                    }
                )
            for task in tasks:
                value = {"title": task.title, "duration_min": task.duration_min}
                if task.description:
                    value["description"] = task.description
                if task.reuse:
                    value["reuse"] = task.reuse
                if task.topic:
                    topic = by_title.get(task.topic.casefold().strip())
                    if topic:
                        topic_group, index = topic
                        g = group(task.phase) if task.phase else topic_group
                        if g is topic_group:
                            value["topic_index"] = index
                        else:
                            value["new_topic_title"] = task.topic
                    else:
                        match = scope_item(task.topic, catalog, "topic")
                        g = group(task.phase)
                        value["existing_topic"] = match["candidate"]
                else:
                    g = group(task.phase)
                g["tasks"].append(value)
            # Compiler's per-phase bound is explicit: ask for smaller authored groups; never pad.
            return list(grouped.values())

        result = {
            "kind": "package",
            "title": self.title,
            "phases": phases(self.tasks, self.topics, self.title),
            "projects": self.projects,
            "missing_information": self.unknowns,
        }
        if self.outcome:
            result["outcome"] = self.outcome.model_dump(mode="json")
        if self.acceptance_criterion:
            result["acceptance_criterion"] = self.acceptance_criterion
        if self.periods:
            result["long_term"] = True
            result["children"] = [
                {"title": p.title, "period": p.label, "phases": phases(p.tasks, p.topics, p.title)}
                for p in self.periods
            ]
        return PackageDraft.model_validate(result).model_dump(mode="json")


def scope_catalog(snapshot, candidates):
    if not snapshot:
        return []
    tokens = {c["id"]: c["token"] for c in candidates}
    items = []
    area_ids = {t["area_id"] for t in snapshot.get("learning", [])}
    for c in candidates:
        if c["type"] == "study_area" and c["id"] in area_ids:
            items.append(
                {
                    "ref": f"area_{sum(i['kind'] == 'area' for i in items) + 1}",
                    "kind": "area",
                    "title": c["title"],
                    "id": c["id"],
                    "candidate": c["token"],
                }
            )
    for i, node in enumerate(snapshot.get("revision_nodes", snapshot["roadmap"]["nodes"])):
        if node.get("persisted") and not node.get("missing"):
            items.append(
                {
                    "ref": f"node_{i + 1}",
                    "kind": "node",
                    "title": node["title"],
                    "node_kind": node["kind"],
                    "index": node["index"],
                    "id": node["id"],
                    "detached": node.get("detached", False),
                    "status": "done"
                    if node.get("completed")
                    else "open"
                    if node.get("percent") == 0
                    else "active"
                    if node.get("percent")
                    else "unknown",
                }
            )
    for kind, key in [("work", "todos"), ("topic", "learning")]:
        for i, item in enumerate(snapshot.get(key, [])[:12]):
            if item["id"] in tokens:
                items.append(
                    {
                        "ref": f"{kind}_{i + 1}",
                        "kind": kind,
                        "title": item["title"],
                        "status": item["status"],
                        "id": item["id"],
                        "candidate": tokens[item["id"]],
                    }
                )
    for i, slot in enumerate(snapshot.get("planned_slots", [])[:20]):
        task_id = slot.get("entity_id")
        if task_id in tokens:
            items.append(
                {
                    "ref": f"slot_{i + 1}",
                    "kind": "slot",
                    "title": next(
                        (t["title"] for t in snapshot["todos"] if t["id"] == task_id), "Çalışma"
                    ),
                    "id": slot["id"],
                    "candidate": tokens[task_id],
                    "day": slot["day"],
                    "duration_min": slot["duration_min"],
                    "start_min": slot.get("start_min"),
                }
            )
    return items


def public_catalog(items):
    return [
        {k: v for k, v in item.items() if k not in {"id", "index", "candidate"}} for item in items
    ]


def scope_item(ref, catalog, kind=None):
    matches = [
        i
        for i in catalog
        if (i["ref"] == ref or i["title"].casefold().strip() == ref.casefold().strip())
        and (
            kind is None or i["kind"] in kind
            if isinstance(kind, tuple)
            else kind is None or i["kind"] == kind
        )
    ]
    if len(matches) != 1:
        raise ReplyError(
            "invalid_candidate_reference",
            "Değiştirilecek kayıt tekil değil veya seçili hedefte bulunmuyor; adını belirt",
        )
    return matches[0]


class RevisionChange(Closed):
    ref: str = Field(min_length=1, max_length=300)
    day: str | None = None
    duration_min: int | None = Field(None, ge=1, le=480)
    title: str | None = Field(None, min_length=1, max_length=300)
    priority: int | None = Field(None, ge=0, le=3)


class SemanticRevision(Closed):
    kind: Literal["revision"]
    action: Literal[
        "add_tasks",
        "add_topics",
        "add_resources",
        "attach_record",
        "rename",
        "edit",
        "move",
        "reduce",
        "replan",
        "detach",
        "attach",
        "prioritize",
    ]
    target: str | None = Field(None, max_length=300)
    tasks: list[SemanticTask] = Field(default_factory=list, max_length=6)
    topics: list[SemanticTopic] = Field(default_factory=list, max_length=8)
    sources: list[str] = Field(default_factory=list, max_length=5)
    resource_needs: list[str] = Field(default_factory=list, max_length=3)
    record: str | None = None
    area: str | None = Field(None, max_length=300)
    changes: list[RevisionChange] = Field(default_factory=list, max_length=12)

    def package(self, snapshot, catalog, constraints):
        needs = [
            *self.resource_needs,
            *[need for topic in self.topics for need in topic.resource_needs],
        ]
        if any(re.search(r"https?://|www\.", need, flags=re.I) for need in needs):
            raise ReplyError("unsupported_claim", "Kaynak ihtiyacı doğrulanmamış bağlantı içeremez")
        label = snapshot["goal"]["title"]
        result = {"kind": "package", "title": label, "phases": [], "preserve_goal_metadata": True}
        if self.area and (self.action not in {"add_tasks", "add_topics"} or not self.topics):
            raise ReplyError(
                "incomplete_revision", "Öğrenme alanı yalnız yeni konu eklemesi için seçilebilir"
            )
        if self.action == "add_resources":
            if not self.target or self.tasks or self.topics or self.changes or self.record:
                raise ReplyError(
                    "incomplete_revision",
                    "Kaynak eklemek için mevcut konu ve kaynak ihtiyacı gerekli",
                )
            topic = scope_item(self.target, catalog, "topic")
            if not self.sources and not self.resource_needs:
                raise ReplyError("missing_resources", "Kaynak eklemesi boş olamaz")
            if constraints.get("requested_resources") is not None and (
                len(self.sources) + len(self.resource_needs) != constraints["requested_resources"]
            ):
                raise ReplyError("incomplete_revision", "İstenen yeni kaynak sayısını koru")
            SemanticTopic(title=topic["title"], resource_needs=self.resource_needs)
            result["topic_resources"] = [
                {
                    "topic": topic["candidate"],
                    "sources": self.sources,
                    "resource_needs": self.resource_needs,
                }
            ]
            return PackageDraft.model_validate(result).model_dump(mode="json")
        if self.action == "attach_record":
            if (
                not self.record
                or self.tasks
                or self.topics
                or self.changes
                or self.sources
                or self.resource_needs
            ):
                raise ReplyError("incomplete_revision", "Yalnız doğrulanmış mevcut kaydı bağla")
            # Public candidate tokens are resolved by the compiler; no model database IDs.
            attachment = {"record": self.record}
            if self.target:
                target = scope_item(
                    self.target,
                    [
                        i
                        for i in catalog
                        if i["kind"] == "node" and i["node_kind"] in {"phase", "period"}
                    ],
                    "node",
                )
                attachment["parent_index"] = target["index"]
            result["record_attachments"] = [attachment]
            return PackageDraft.model_validate(result).model_dump(mode="json")
        if self.sources or self.resource_needs or self.record:
            raise ReplyError("incomplete_revision", "Revizyon kapsam dışı kaynak/kayıt içeriyor")
        if self.action in {"add_tasks", "add_topics"}:
            if (
                self.changes
                or (self.action == "add_topics" and self.tasks)
                or (self.action == "add_tasks" and not self.tasks)
                or (self.action == "add_topics" and not self.topics)
            ):
                raise ReplyError(
                    "incomplete_revision", "Yalnız istenen yeni görev/konu içeriği gerekli"
                )
            if (
                constraints["requested_tasks"] is not None
                and len(self.tasks) != constraints["requested_tasks"]
            ):
                raise ReplyError("incomplete_revision", "İstenen yeni görev sayısını koru")
            if constraints.get("requested_topics") is not None and (
                len(self.topics) != constraints["requested_topics"]
            ):
                raise ReplyError("incomplete_revision", "İstenen yeni konu sayısını koru")
            if any(
                t.title.casefold().strip() == i["title"].casefold().strip()
                for t in self.topics
                for i in catalog
                if i["kind"] == "topic"
            ):
                raise ReplyError(
                    "invalid_candidate_reference", "Konu zaten hedefte; mevcut konuyu kullan"
                )
            result = SemanticDraft(
                kind="semantic_plan", title=label, tasks=self.tasks, topics=self.topics
            ).package(catalog=catalog)
            result["preserve_goal_metadata"] = True
            areas = [i for i in catalog if i["kind"] == "area"]
            if self.topics:
                if self.area:
                    result["reuse_area"] = scope_item(self.area, catalog, "area")["candidate"]
                elif len(areas) == 1:
                    result["reuse_area"] = areas[0]["candidate"]
                elif len(areas) > 1:
                    raise ReplyError(
                        "invalid_candidate_reference",
                        "Konuyu ekleyeceğin mevcut öğrenme alanını belirt",
                    )
            if self.target:
                target = scope_item(
                    self.target,
                    [
                        i
                        for i in catalog
                        if i["kind"] == "node" and i["node_kind"] in {"phase", "period"}
                    ],
                    "node",
                )
                if target["node_kind"] not in {"phase", "period"}:
                    raise ReplyError(
                        "invalid_candidate_reference", "Yeni çalışma için mevcut aşamayı seç"
                    )
                if len(result["phases"]) != 1:
                    raise ReplyError(
                        "incomplete_revision", "Mevcut aşamaya ekleme tek grupta olmalı"
                    )
                result["phases"][0]["attach_node_index"] = target["index"]
            return result
        if self.tasks or self.topics or not self.changes:
            raise ReplyError("incomplete_revision", "Mevcut kayıt değişikliği yeni plan üretmemeli")
        if self.target:
            raise ReplyError("incomplete_revision", "Düzenleme hedefini changes.ref içinde belirt")
        if len({c.ref for c in self.changes}) != len(self.changes):
            raise ReplyError("incomplete_revision", "Aynı kayıt iki kez değiştirilemez")
        for change in self.changes:
            if self.action in {"rename", "detach", "attach"}:
                item = scope_item(change.ref, catalog, "node")
                if change.day or change.duration_min or change.priority is not None:
                    raise ReplyError(
                        "incomplete_revision", "Yol haritası değişikliği kapsam dışı alan içeriyor"
                    )
                if self.action == "rename" and item["node_kind"] not in {"phase", "period"}:
                    raise ReplyError(
                        "incomplete_revision",
                        "Ad değiştirmek için mevcut aşama veya dönem kaydını seç",
                    )
                if self.action == "rename" and not change.title:
                    raise ReplyError("incomplete_revision", "Yeni aşama adı gerekli")
                if self.action != "rename" and change.title:
                    raise ReplyError("incomplete_revision", "Bağ ayırma ad değiştiremez")
                result.setdefault("node_changes", []).append(
                    {
                        "node_index": item["index"],
                        **({"title": change.title} if change.title else {}),
                        "detached": self.action == "detach",
                    }
                )
            elif self.action in {"edit", "prioritize"}:
                item = scope_item(change.ref, catalog, "work")
                if (
                    change.day
                    or change.duration_min
                    or (self.action == "prioritize" and change.title)
                ):
                    raise ReplyError(
                        "incomplete_revision", "Görev düzenleme kapsam dışı alan içeriyor"
                    )
                result.setdefault("task_changes", []).append(
                    {
                        "task": item["candidate"],
                        **({"title": change.title} if change.title else {}),
                        **({"priority": change.priority} if change.priority is not None else {}),
                    }
                )
            else:
                item = slot_item(change.ref, catalog)
                if change.title or change.priority is not None:
                    raise ReplyError("incomplete_revision", "Plan değişikliği görevi düzenleyemez")
                if self.action == "reduce" and (
                    change.day
                    or not change.duration_min
                    or not item.get("duration_min")
                    or change.duration_min >= item["duration_min"]
                ):
                    raise ReplyError(
                        "incomplete_revision", "Hafifletme mevcut bloğun süresini azaltmalı"
                    )
                day = change.day or item["day"]
                if self.action == "move" and (not change.day or day == item["day"]):
                    raise ReplyError(
                        "incomplete_revision", "Taşıma farklı bir çalışma günü gerektirir"
                    )
                if (
                    self.action == "replan"
                    and day == item["day"]
                    and (
                        change.duration_min is None
                        or change.duration_min == item.get("duration_min")
                    )
                ):
                    raise ReplyError(
                        "incomplete_revision", "Yeniden planlama gerçek bir değişiklik gerektirir"
                    )
                if (change.day or self.action == "replan") and day not in constraints[
                    "schedule_days"
                ]:
                    raise ReplyError(
                        "incomplete_revision", "Çalışma günü istenen tarih aralığında değil"
                    )
                result.setdefault("schedule_changes", []).append(
                    {
                        "task": item["candidate"],
                        "from_day": item["day"],
                        "day": day,
                        **({"duration_min": change.duration_min} if change.duration_min else {}),
                    }
                )
        return PackageDraft.model_validate(result).model_dump(mode="json")


ERRORS = {
    "missing_required_learning": "Bu hedef için öğrenme konuları eksik.",
    "missing_explicit_outcome": "Belirttiğin sayısal hedef korunmamış.",
    "insufficient_delivery_coverage": "İstenen işlerin bir kısmı planda eksik.",
    "unrelated_administrative_scope": "Plan, istediğin süreçten farklı işler içeriyor.",
    "invalid_candidate_reference": "Mevcut kayıt eşleşmesi doğrulanamadı.",
    "incomplete_revision": "İstenen değişiklik seçili hedefte çözülemedi.",
    "unsupported_claim": "Yanıtta kaydedilmiş bilgilerle desteklenmeyen bir ifade var.",
    "negative_constraint": "Plan, belirttiğin bir sınırı karşılamıyor.",
    "missing_resources": "Öğrenme için kaynak ihtiyaçları belirtilmemiş.",
    "missing_periods": "Uzun vadeli hedefin dönemleri eksik.",
}


def validate_literal_package(package, constraints):
    """Explicit exclusions apply equally to the default and experimental generators."""
    p = PackageDraft.model_validate(package)
    phases = [*p.phases, *[phase for child in p.children for phase in child.phases]]
    if constraints.get("requested_topics") is not None and (
        sum(not topic.reuse for phase in phases for topic in phase.topics)
        != constraints["requested_topics"]
    ):
        raise ReplyError("incomplete_revision", "İstenen yeni konu sayısını koru")
    if "learning" in constraints["excluded"] and any(phase.topics for phase in phases):
        raise ReplyError("negative_constraint", "Öğrenme çalışması istemediğin için konu eklenemez")
    if "project" in constraints["excluded"] and p.projects:
        raise ReplyError(
            "negative_constraint", "Proje bağlantısı istemediğin için proje bağlanamaz"
        )
    if "schedule" in constraints["excluded"] and p.schedule_changes:
        raise ReplyError(
            "negative_constraint",
            "Takvim değişikliği istemediğin için çalışma bloğu değiştirilemez",
        )
    return p


def quality_gate(package, requirements, constraints, candidates):
    p = PackageDraft.model_validate(package)
    phases = [*p.phases, *[phase for child in p.children for phase in child.phases]]
    tasks = [t for phase in phases for t in phase.tasks]
    topics = [t for phase in phases for t in phase.topics]
    if requirements.needs.learning == "required" and not topics:
        raise ReplyError("missing_required_learning", ERRORS["missing_required_learning"])
    if requirements.needs.tasks == "required" and not tasks:
        raise ReplyError("insufficient_delivery_coverage", "Somut yakın dönem işler eksik")
    if (
        requirements.needs.resources == "required"
        and topics
        and not all(t.resources or t.resource_needs for t in topics)
    ):
        raise ReplyError("missing_resources", ERRORS["missing_resources"])
    if constraints["numeric_target"] is not None and (
        not p.outcome or p.outcome.target_value != Decimal(constraints["numeric_target"])
    ):
        raise ReplyError("missing_explicit_outcome", ERRORS["missing_explicit_outcome"])
    if constraints["numeric_target"] is None and p.outcome:
        raise ReplyError(
            "unsupported_claim", "Kullanıcının belirtmediği sayısal sonuç hedefi üretilemez"
        )
    if requirements.needs.learning == "not_applicable" and topics:
        raise ReplyError("negative_constraint", "Bu amaca ilgisiz öğrenme içeriği eklenmiş")
    if (
        requirements.needs.project == "required"
        and any(c["type"] == "project" for c in candidates)
        and not p.projects
    ):
        raise ReplyError("invalid_candidate_reference", "İstenen mevcut proje bağlantısı eksik")
    if requirements.needs.periods == "required" and (not p.long_term or len(p.children) < 2):
        raise ReplyError("missing_periods", ERRORS["missing_periods"])
    for name in constraints["excluded"]:
        if (name == "learning" and topics) or (name == "project" and p.projects):
            raise ReplyError("negative_constraint", ERRORS["negative_constraint"])
    catalog = {c["token"]: c for c in candidates}
    references = [(r, {"project"}) for r in p.projects]
    references += [(t.reuse, {"todo"}) for t in tasks if t.reuse]
    references += [(t.existing_topic, {"study_topic"}) for t in tasks if t.existing_topic]
    references += [(t.reuse, {"study_topic"}) for t in topics if t.reuse]
    references += [
        (r, {"bookmark", "course", "learning_resource", "flashcard_deck"})
        for t in topics
        for r in t.resources
    ]
    for token, types in references:
        if token not in catalog or catalog[token]["type"] not in types:
            raise ReplyError("invalid_candidate_reference", ERRORS["invalid_candidate_reference"])
    if re.search(r"https?://|www\.", p.model_dump_json(), flags=re.I):
        raise ReplyError(
            "unsupported_claim", "Kaynak URL'si veya doğrulanmamış dış bağlantı üretilemez"
        )
    return p


class Issue(Closed):
    code: Literal[
        "missing_required_learning",
        "missing_explicit_outcome",
        "insufficient_delivery_coverage",
        "unrelated_administrative_scope",
        "invalid_candidate_reference",
        "incomplete_revision",
        "unsupported_claim",
        "negative_constraint",
        "missing_resources",
        "missing_periods",
    ]
    detail: str = Field(min_length=1, max_length=400)
    layer: Literal["requirements", "draft"] = "draft"
    excerpt: str = Field("", max_length=300)


class QualityReview(Closed):
    verdict: Literal["accept", "reject"]
    covered: list[int] = Field(default_factory=list, max_length=6)
    issues: list[Issue] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def consistent(self):
        if (self.verdict == "accept") != (not self.issues):
            raise ValueError("Kalite kararı ve gerekçeleri çelişiyor")
        return self


class CoachingReply(Closed):
    advice: str = Field(min_length=1, max_length=700)
    actions: list[str] = Field(default_factory=list, max_length=2)

    def checked(self, catalog):
        if len(set(self.actions)) != len(self.actions):
            raise ReplyError("unsupported_claim", "Aynı sonraki iş tekrar edemez")
        for ref in self.actions:
            item = scope_item(ref, action_catalog(catalog))
            if item.get("status") in {"done", "dropped", "unknown"}:
                raise ReplyError(
                    "unsupported_claim", "Sonraki iş gerçekten bekleyen bir çalışma olmalı"
                )
        names = {i["ref"]: i["title"] for i in catalog}

        def human_name(match):
            ref = match.group()
            if ref not in names:
                raise ReplyError(
                    "unsupported_claim", "Yorum bilinmeyen bir kayıt referansı içeriyor"
                )
            return names[ref]

        advice = re.sub(r"\b(?:work|topic|node|slot|area)_[0-9]+\b", human_name, self.advice)
        return CoachingReply(advice=advice, actions=self.actions)


def action_catalog(catalog):
    return [
        i
        for i in catalog
        if i["kind"] in {"work", "topic"}
        or i["kind"] == "node"
        and i.get("node_kind") == "milestone"
        and not i.get("detached")
    ]


def slot_item(ref, catalog):
    direct = [
        i
        for i in catalog
        if i["kind"] == "slot" and (i["ref"] == ref or i["title"].casefold() == ref.casefold())
    ]
    if len(direct) == 1:
        return direct[0]
    work = [i for i in catalog if i["kind"] == "work" and i["ref"] == ref]
    if len(work) == 1:
        matches = [
            i for i in catalog if i["kind"] == "slot" and i["candidate"] == work[0]["candidate"]
        ]
        if len(matches) == 1:
            return matches[0]
    raise ReplyError(
        "invalid_candidate_reference",
        "Çalışma bloğu tekil değil veya planlanmamış; taşınacak mevcut gününü belirt",
    )


def schedule_days(data, constraints):
    from datetime import datetime

    from app.core.time import local_today

    active = data["turns"][data["active_turn"]]
    today = local_today(datetime.fromisoformat(active["at"]))
    if re.search(r"(?:önümüzdeki|gelecek)\s+hafta", active["message"].casefold()):
        start = today + timedelta(days=7 - today.weekday())
        return [(start + timedelta(days=i)).isoformat() for i in range(7)]
    return constraints["allowed_dates"] or [
        (today + timedelta(days=i)).isoformat() for i in range(14)
    ]


async def revision_nodes(db, snapshot):
    """Detached nodes can be explicitly reattached, without reintroducing them into progress."""
    from uuid import UUID

    from sqlalchemy import select

    from app.core.models import Entity
    from app.modules.goal.roadmap_models import GoalRoadmapNode

    active = list(snapshot["roadmap"]["nodes"])
    found = {n["id"] for n in active}
    rows = (
        await db.execute(
            select(GoalRoadmapNode, Entity)
            .join(Entity, Entity.id == GoalRoadmapNode.id)
            .where(
                GoalRoadmapNode.goal_id == UUID(snapshot["goal"]["id"]),
                Entity.archived_at.is_(None),
                GoalRoadmapNode.detached.is_(True),
            )
            .order_by(GoalRoadmapNode.position, GoalRoadmapNode.id)
            .limit(60)
        )
    ).all()
    for node, entity in rows:
        if str(node.id) not in found and len(active) < 60:
            active.append(
                {
                    "index": len(active),
                    "id": str(node.id),
                    "title": entity.title,
                    "kind": node.kind,
                    "persisted": True,
                    "detached": True,
                    "missing": False,
                    "parent_id": str(node.parent_id) if node.parent_id else None,
                    "target_id": str(node.target_id) if node.target_id else None,
                    "updated_at": entity.updated_at.isoformat(),
                }
            )
    return active


async def validate_revision_scope(db, pipeline):
    from uuid import UUID

    from app.modules.todo.models import PlanSlot

    for change in pipeline.get("semantic_revision", {}).get("changes", []):
        ref = change["ref"]
        if pipeline["semantic_revision"]["action"] not in {"move", "reduce", "replan"}:
            continue
        item = slot_item(ref, pipeline["catalog"])
        row = await db.get(PlanSlot, UUID(item["id"]))
        if not row or (row.day.isoformat(), row.duration_min, row.start_min) != (
            item["day"],
            item["duration_min"],
            item["start_min"],
        ):
            raise ReplyError(
                "invalid_candidate_reference",
                "Çalışma bloğu görüşme sırasında değişmiş; güncel bağlamla yeniden iste",
            )
