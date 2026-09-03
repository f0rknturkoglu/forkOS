from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import archive_entity, create_entity, touch_entity
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
            "folder_id": d.folder_id,
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
            doc = Document(id=entity.id, drive_file_id=raw["id"], folder_id=folder_id)
            session.add(doc)
        else:
            await touch_entity(session, doc.id, title=raw["name"])
        doc.mime = raw.get("mimeType")
        doc.folder_id = folder_id
        doc.category = category
        doc.web_view_link = raw.get("webViewLink")
        doc.size_bytes = int(raw["size"]) if raw.get("size") else None
        doc.drive_modified_at = datetime.fromisoformat(raw["modifiedTime"].replace("Z", "+00:00"))
        doc.synced_at = now
    existing = list(
        (
            await session.execute(
                select(Document).where(
                    Document.category == category,
                    Document.folder_id == folder_id,
                )
            )
        ).scalars()
    )
    for doc in existing:
        if doc.drive_file_id not in seen:
            await archive_entity(session, doc.id)
    await log_event(
        session,
        verb="document.synced",
        payload={"count": len(files), "category": category, "folder_id": folder_id},
    )
    await session.commit()
    return len(files)


DOCUMENTS_DIR = Path(__file__).resolve().parents[3] / "data" / "documents"


def get_local_file_path(doc_id: UUID, title: str) -> Path | None:
    doc_dir = DOCUMENTS_DIR / str(doc_id)
    target = doc_dir / title
    if target.exists():
        return target
    if doc_dir.exists():
        for f in doc_dir.iterdir():
            if f.is_file():
                return f
    return None


async def create_local_document(
    session: AsyncSession,
    *,
    title: str,
    category: str = "cv",
    mime: str | None = None,
    content: bytes,
) -> dict:
    now = datetime.now(UTC)
    entity = await create_entity(
        session,
        type="document",
        title=title,
        search_text=f"{category} {mime or ''} {title}",
    )
    doc_dir = DOCUMENTS_DIR / str(entity.id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    file_path = doc_dir / title
    file_path.write_bytes(content)

    doc = Document(
        id=entity.id,
        drive_file_id=f"local:{entity.id}",
        folder_id="local",
        mime=mime,
        category=category,
        web_view_link=f"/api/documents/{entity.id}/file",
        size_bytes=len(content),
        drive_modified_at=now,
        synced_at=now,
    )
    session.add(doc)
    await log_event(
        session,
        verb="document.created",
        entity_id=entity.id,
        entity_type="document",
        payload={"category": category, "title": title, "size": len(content)},
    )
    await session.commit()
    return {
        "id": doc.id,
        "title": title,
        "drive_file_id": doc.drive_file_id,
        "folder_id": doc.folder_id,
        "mime": doc.mime,
        "category": doc.category,
        "web_view_link": doc.web_view_link,
        "size_bytes": doc.size_bytes,
        "drive_modified_at": doc.drive_modified_at,
        "synced_at": doc.synced_at,
    }


async def delete_document(session: AsyncSession, doc_id: UUID) -> bool:
    doc = await session.get(Document, doc_id)
    if not doc:
        return False
    await archive_entity(session, doc_id)
    await log_event(
        session,
        verb="document.deleted",
        entity_id=doc_id,
        entity_type="document",
        payload={"category": doc.category},
    )
    await session.commit()
    return True

