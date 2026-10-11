import html
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pypdf import PdfReader
from pypdf.errors import PyPdfError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import archive_entity, create_entity
from app.core.events import log_event
from app.core.models import Entity
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


DOCUMENTS_DIR = Path(__file__).resolve().parents[3] / "data" / "documents"

_PLAIN_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".csv", ".json", ".yaml", ".yml"}


def extract_local_document_text(
    path: Path,
    *,
    mime: str | None = None,
    max_chars: int = 120_000,
) -> str | None:
    """Yerel aday belgesinden metin çıkarır; dosya içeriği ağdan çıkmaz.

    PDF için saf-Python ``pypdf`` kullanılır. DOCX, ek bir ofis paketi veya
    harici servis gerektirmeden ZIP/XML yapısından okunur. Bozuk veya taranmış
    dosya değerlendirmeyi düşürmez; yalnızca belge kanıtı olmadan devam eder.
    """

    if not path.is_file() or max_chars <= 0:
        return None
    suffix = path.suffix.casefold()
    normalized_mime = (mime or "").casefold()
    try:
        if normalized_mime.startswith("text/") or suffix in _PLAIN_TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
        elif normalized_mime == "application/pdf" or suffix == ".pdf":
            reader = PdfReader(path)
            chunks: list[str] = []
            remaining = max_chars
            for page in reader.pages:
                chunk = page.extract_text() or ""
                if chunk:
                    chunks.append(chunk[:remaining])
                    remaining -= len(chunk)
                if remaining <= 0:
                    break
            text = "\n".join(chunks)
        elif (
            normalized_mime
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            or suffix == ".docx"
        ):
            with zipfile.ZipFile(path) as archive:
                xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
            xml = re.sub(r"</w:p>|<w:br[^>]*/>", "\n", xml)
            text = html.unescape(re.sub(r"<[^>]+>", " ", xml))
        elif normalized_mime in {"text/html", "application/xhtml+xml"} or suffix in {
            ".html",
            ".htm",
        }:
            raw = path.read_text(encoding="utf-8", errors="replace")
            text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
        else:
            return None
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, PyPdfError):
        return None

    compact = re.sub(r"[ \t]+", " ", text)
    compact = re.sub(r"\n{3,}", "\n\n", compact).strip()
    return compact[:max_chars] or None


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
    commit: bool = True,
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
    if commit:
        await session.commit()
    else:
        await session.flush()
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
