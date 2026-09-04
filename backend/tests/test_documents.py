from __future__ import annotations

import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.entity import create_entity
from app.core.models import Entity
from app.db import SessionLocal
from app.modules.document import service
from app.modules.document.models import Document


class FakeResponse:
    status_code = 200
    text = ""

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "files": [
                {
                    "id": "keep-a",
                    "name": "Yeni CV",
                    "mimeType": "application/pdf",
                    "webViewLink": "https://drive.test/keep-a",
                    "size": "123",
                    "modifiedTime": "2026-08-23T08:00:00Z",
                }
            ]
        }


class FakeClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, *_args, **_kwargs):
        return FakeResponse()


async def test_sync_archives_only_the_matching_folder_and_category(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(service, "access_token", lambda _session: _async_value("token"))
    monkeypatch.setattr(service.httpx, "AsyncClient", lambda **_kwargs: FakeClient())

    async with SessionLocal() as session:
        for title, drive_file_id, folder_id in (
            ("Eski A", "old-a", "folder-a"),
            ("Başka klasör", "old-b", "folder-b"),
        ):
            entity = await create_entity(session, type="document", title=title)
            session.add(
                Document(
                    id=entity.id,
                    drive_file_id=drive_file_id,
                    folder_id=folder_id,
                    category="cv",
                    synced_at=datetime.now(UTC),
                )
            )
        await session.commit()

        assert await service.sync_folder(session, "folder-a", "cv") == 1

        rows = {
            doc.drive_file_id: archived_at
            for doc, archived_at in (
                await session.execute(select(Document, Entity.archived_at).join(Entity))
            ).all()
        }
        assert rows["old-a"] is not None
        assert rows["old-b"] is None
        assert rows["keep-a"] is None


async def _async_value(value):
    return value


@pytest.mark.no_database
def test_extract_local_candidate_text_from_plain_text_and_docx(tmp_path: Path):
    plain = tmp_path / "cv.txt"
    plain.write_text("Python ve Kubernetes deneyimi", encoding="utf-8")
    assert service.extract_local_document_text(plain) == "Python ve Kubernetes deneyimi"

    docx = tmp_path / "cv.docx"
    with zipfile.ZipFile(docx, "w") as archive:
        archive.writestr(
            "word/document.xml",
            "<w:document><w:body><w:p><w:r><w:t>Terraform</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>Azure platform</w:t></w:r></w:p></w:body></w:document>",
        )
    extracted = service.extract_local_document_text(docx)
    assert extracted is not None
    assert "Terraform" in extracted
    assert "Azure platform" in extracted
