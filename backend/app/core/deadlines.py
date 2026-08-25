"""Son tarih toplayici (kural 16).

Her modul istege bagli deadline_provider verir; /api/deadlines kayitli
sağlayicilari toplar ve siralar. deadline_v gibi elle SQL gorunumu YAZILMAZ;
yeni son-tarihli modul eklemek = ModuleSpec.deadline_provider'a bir fonksiyon.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.modules import MODULES, DeadlineRow


async def rows_with_titles(
    session: AsyncSession,
    *,
    type_: str,
    module: str,
    ids: list,
    due_at: dict,
    sub_kind: dict | None = None,
    priority: dict | None = None,
) -> list[DeadlineRow]:
    """Entity id listesi + son tarih haritasindan satir kurar; basliklari
    entity tablosundan okur (arşivlenmişler atlanir)."""
    entities = {
        e.id: e for e in (await session.execute(
            select(Entity).where(Entity.id.in_(ids), Entity.archived_at.is_(None))
        )).scalars()
    }
    return [
        DeadlineRow(
            entity_id=eid,
            type=type_,
            title=entity.title,
            due_at=due_at[eid],
            module=module,
            sub_kind=sub_kind.get(eid) if sub_kind else None,
            priority=(priority or {}).get(eid, 2),
        )
        for eid, entity in entities.items()
        if due_at.get(eid) is not None
    ]


async def collect_deadlines(session: AsyncSession, *, limit: int = 200) -> list[dict]:
    rows: list[DeadlineRow] = []
    for module in MODULES:
        if module.deadline_provider is not None:
            rows.extend(await module.deadline_provider(session))
    rows.sort(key=lambda r: (r.due_at is None, r.due_at or datetime.min))
    return [
        {
            "entity_id": str(row.entity_id),
            "type": row.type,
            "title": row.title,
            "due_at": row.due_at,
            "module": row.module,
            "sub_kind": row.sub_kind,
            "priority": row.priority,
        }
        for row in rows[:limit]
    ]
