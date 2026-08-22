from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.integrations.google_auth import access_token
from app.modules.document.models import Document


async def list_documents(session: AsyncSession, category=None):
    stmt = (
        select(Document, Entity.title)
        .join(Entity)
        .where(Entity.archived_at.is_(None))
        .order_by(Document.category, Entity.title)
    )
    if category:
        stmt = stmt.where(Document.category == category)
    return [
        {
            "id": d.id,
            "title": t,
            "drive_file_id": d.drive_file_id,
            "mime": d.mime,
            "category": d.category,
            "web_view_link": d.web_view_link,
            "size_bytes": d.size_bytes,
            "drive_modified_at": d.drive_modified_at,
            "synced_at": d.synced_at,
        }
        for d, t in (await session.execute(stmt)).all()
    ]


async def sync_folder(session: AsyncSession, folder_id: str, category: str):
    token = await access_token(session)
    params = {
        "q": f"'{folder_id}' in parents and trashed=false",
        "fields": "files(id,name,mimeType,webViewLink,size,modifiedTime)",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Sessiz olum istemiyoruz: Drive 403/404'te kullanici ne oldugunu gormeli
            raise RuntimeError(
                f"Drive hatası ({response.status_code}): {response.text[:300]}"
            ) from exc
        files = response.json().get("files", [])
    seen = set()
    now = datetime.now(UTC)
    for raw in files:
        seen.add(raw["id"])
        doc = (
            await session.execute(select(Document).where(Document.drive_file_id == raw["id"]))
        ).scalar_one_or_none()
        if doc is None:
            entity = await create_entity(
                session,
                type="document",
                title=raw["name"],
                search_text=f"{category} {raw.get('mimeType', '')}",
            )
            doc = Document(id=entity.id, drive_file_id=raw["id"])
            session.add(doc)
        else:
            await touch_entity(session, doc.id, title=raw["name"])
        doc.mime = raw.get("mimeType")
        doc.category = category
        doc.web_view_link = raw.get("webViewLink")
        doc.size_bytes = int(raw["size"]) if raw.get("size") else None
        doc.drive_modified_at = datetime.fromisoformat(raw["modifiedTime"].replace("Z", "+00:00"))
        doc.synced_at = now
    existing = list(
        (await session.execute(select(Document).where(Document.category == category))).scalars()
    )
    for doc in existing:
        if doc.drive_file_id not in seen:
            entity = await session.get(Entity, doc.id)
            entity.archived_at = now
    await log_event(
        session, verb="document.synced", payload={"count": len(files), "category": category}
    )
    await session.commit()
    return len(files)
