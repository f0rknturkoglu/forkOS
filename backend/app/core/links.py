"""Entity'ler arasi iliski.

RELATIONS -- iliski (relation) sozlugu TEK yerde: ileri/geri etiket cifti.
UI iki yonu de buradan yazar. Yeni iliski eklemek = buraya bir satir
(AGENTS.md kural 13'ün link tarafi).
"""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, Link

#: relation -> (ileri etiket, geri etiket). UI yonu duzeltir.
RELATIONS: dict[str, tuple[str, str]] = {
    "related": ("İlgili", "İlgili"),
    "saved_from": ("Kaynağı", "Buradan kaydedildi"),
    "belongs_to": ("Ait olduğu", "Alt kaydı"),
    "application_step": ("Başvuru adımı", "Adımı olduğu başvuru"),
    "paid_as": ("Ödemesi", "Ödendiği harcama"),
    "media.collection_item": ("Koleksiyon", "Koleksiyon öğesi"),
    "prepares_for": ("Hazırlık", "Hazırlanılan"),
    "references": ("Kaynak", "Kaynak gösterilen"),
    # Faz 12: konu -> kurs/kitap/video (learning baglaminda).
    # from = konu (study_topic), to = kaynak (course | media_item).
    "learns_from": ("Kaynakları", "Çalışıldığı konu"),
    # Faz 21: not -> konu/entity. from = not, to = hakkinda oldugu kayit.
    "notes_about": ("Hakkında not", "Notları"),
    # Medya alintisi: from = yer imi (bookmark.selection), to = medya kaydi.
    # Ayri bir highlight tablosu YOK: alinti metni bookmark.selection'ta durur,
    # baglami (sayfa/zaman kodu) bookmark.note'una yazilir (mevcut altyapi).
    "highlights": ("Alıntıları", "Alıntılandığı kayıt"),
    # Govde metnindeki [[wikilink]]'ten uretilir (core/refs.py). Backlink
    # paneli ve graf bu iliskiyi okur; elle kurulmaz, metinden turer.
    "mentions": ("Bahsettikleri", "Buraya bağlananlar"),
}


async def link(
    session: AsyncSession, from_id: uuid.UUID, to_id: uuid.UUID,
    relation: str = "related",
) -> None:
    if from_id == to_id:
        return
    stmt = insert(Link).values(from_id=from_id, to_id=to_id, relation=relation)
    await session.execute(stmt.on_conflict_do_nothing(constraint="link_uniq"))


async def unlink(
    session: AsyncSession, from_id: uuid.UUID, to_id: uuid.UUID,
    relation: str = "related",
) -> None:
    row = (await session.execute(
        select(Link).where(Link.from_id == from_id, Link.to_id == to_id,
                           Link.relation == relation))).scalar_one_or_none()
    if row is not None:
        await session.delete(row)


async def related(session: AsyncSession, entity_id: uuid.UUID) -> list[dict]:
    """Yon fark etmeksizin bagli tum entity'ler; her satir icin iliski ve yon.

    direction: "outgoing" (bu kayittan disari), "incoming" (disaridan bu kayda).
    label: iliski sozlugundeki ileri/geri etiket -- UI yonu duzeltir.
    """
    links = (await session.execute(
        select(Link).where(or_(Link.from_id == entity_id, Link.to_id == entity_id))
    )).scalars()
    rows: list[dict] = []
    other_ids: set[uuid.UUID] = set()
    for lk in links:
        outgoing = lk.from_id == entity_id
        other_ids.add(lk.to_id if outgoing else lk.from_id)
        forward, backward = RELATIONS.get(lk.relation, (lk.relation, lk.relation))
        rows.append({
            "relation": lk.relation,
            "direction": "outgoing" if outgoing else "incoming",
            "label": forward if outgoing else backward,
            "to_id": str(lk.to_id if outgoing else lk.from_id),
        })
    entities = {
        e.id: e for e in (await session.execute(
            select(Entity).where(Entity.id.in_(other_ids)))).scalars()
    }
    return [
        {
            **row,
            "entity": {
                "id": str(entity.id),
                "type": entity.type,
                "title": entity.title,
                "created_at": entity.created_at.isoformat(),
                "updated_at": entity.updated_at.isoformat(),
            },
        }
        for row in rows
        if (entity := entities.get(uuid.UUID(row["to_id"])))
    ]
