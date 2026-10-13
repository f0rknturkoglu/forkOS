"""Exact local matches become explicit reuse proposals, never silent record merges."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.core.models import Entity, Link
from app.modules.learning.models import StudyTopic
from app.modules.todo.models import Todo


class Candidates:
    def __init__(self, metadata, entities, topics, todos, links):
        self.metadata = {c["token"]: c for c in metadata}
        self.entities = entities
        self.topics = topics
        self.todos = todos
        self.links = links

    def identity(self, token, types):
        meta = self.metadata.get(token)
        entity = self.entities.get(UUID(meta["id"])) if meta else None
        if (
            not meta
            or not entity
            or entity.archived_at
            or entity.type not in types
            or entity.title != meta["title"]
        ):
            raise ValueError("Önerilen mevcut kayıt aday listesinde doğrulanamıyor veya değişmiş")
        if meta.get("updated_at") and entity.updated_at != datetime.fromisoformat(
            meta["updated_at"].replace("Z", "+00:00")
        ):
            raise ValueError("Aday kayıt değişmiş; yeniden oku")
        return str(entity.id)

    def exact(
        self, title, kind, *, area=None, parent=None, topic=None, project=None, description=None
    ):
        matches = []

        def normalize(value):
            return " ".join(value.casefold().split())

        for token, meta in self.metadata.items():
            entity = self.entities.get(UUID(meta["id"]))
            if (
                not entity
                or entity.archived_at
                or entity.type != kind
                or normalize(entity.title) != normalize(title)
            ):
                continue
            if kind == "study_topic":
                row = self.topics.get(entity.id)
                if (
                    not row
                    or str(row.area_id) != area
                    or (str(row.parent_id) if row.parent_id else None) != parent
                ):
                    continue
            if kind == "todo":
                row = self.todos.get(entity.id)
                if (
                    not row
                    or row.recur
                    or row.status == "done"
                    or (row.description or "") != (description or "")
                ):
                    continue
                projects = {
                    str(lk.to_id)
                    for lk in self.links
                    if lk.from_id == row.id and lk.relation == "belongs_to"
                }
                topics = {
                    str(lk.to_id)
                    for lk in self.links
                    if lk.from_id == row.id and lk.relation == "prepares_for"
                }
                if projects != ({project} if project else set()) or topics != (
                    {topic} if topic else set()
                ):
                    continue
            matches.append(token)
        return matches[0] if len(matches) == 1 else None


async def load(db, metadata):
    ids = {UUID(c["id"]) for c in metadata}
    entities = {e.id: e for e in (await db.scalars(select(Entity).where(Entity.id.in_(ids)))).all()}
    topics = {
        t.id: t for t in (await db.scalars(select(StudyTopic).where(StudyTopic.id.in_(ids)))).all()
    }
    todos = {t.id: t for t in (await db.scalars(select(Todo).where(Todo.id.in_(ids)))).all()}
    links = (
        await db.scalars(
            select(Link)
            .where(Link.from_id.in_(ids), Link.relation.in_(["belongs_to", "prepares_for"]))
            .limit(501)
        )
    ).all()
    if len(links) > 500:
        raise ValueError("Eşleştirme bağlantısı kapsamı çok büyük")
    return Candidates(metadata, entities, topics, todos, links)
