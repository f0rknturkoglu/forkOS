"""H1 yer imi eylem adaptörleri.

Kanıtlananlar: tamamen YEREL capture (ağ yok), URL tekilleştirme, yalnızca
izinli alanların güncellenmesi ve tazelik koruması.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.db import SessionLocal
from app.integrations.agent.actions import (
    ActionError,
    capture_bookmark,
    update_bookmark,
)
from app.integrations.agent.write_models import BookmarkCaptureIn, BookmarkUpdateIn
from app.modules.bookmark.models import Bookmark
from tests.agent_test_utils import table_counts


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch: pytest.MonkeyPatch):
    """§118: H1 yazma yolları HİÇBİR ağ çağrısı yapmamalı."""

    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("H1 yer imi eylemi ağ çağrısı yapmamalı")

    monkeypatch.setattr(httpx, "AsyncClient", _boom)
    monkeypatch.setattr(httpx, "Client", _boom)
    monkeypatch.setattr(httpx, "get", _boom)
    monkeypatch.setattr(httpx, "post", _boom)

    from app.core import readability

    monkeypatch.setattr(readability, "fetch_and_extract", _boom)


async def _bookmark_rows(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(Bookmark))).scalar_one())


# ---------------------------------------------------------------------------
# forkos_bookmark_capture
# ---------------------------------------------------------------------------


async def test_capture_creates_local_bookmark(db_session: AsyncSession) -> None:
    before = await table_counts(db_session)

    receipt = await capture_bookmark(
        db_session,
        BookmarkCaptureIn(url="https://example.com/article", title="Ornek makale", collection="inbox"),
        request_id="b1",
    )

    assert receipt.status == "executed"
    assert receipt.target_type == "bookmark"
    assert receipt.after["url"] == "https://example.com/article"
    assert receipt.after["collection"] == "inbox"
    assert receipt.after["read_status"] == "unread"

    bookmark = await db_session.get(Bookmark, uuid.UUID(receipt.target_id))
    assert bookmark is not None
    # §65: agent kaydı canonical `SOURCES` sözlüğünden geçerli bir değer taşır.
    assert bookmark.source == "manual"

    after = await table_counts(db_session)
    assert after["bookmark"] == before["bookmark"] + 1
    for table in ("todo", "project", "opportunity", "application", "flashcard_card"):
        assert after[table] == before[table], table


async def test_capture_dedupes_normalized_url_without_creating_duplicate(
    db_session: AsyncSession,
) -> None:
    """§41: aynı URL (takip parametreleri farklı olsa da) YENİ kayıt açmaz."""
    first = await capture_bookmark(
        db_session,
        BookmarkCaptureIn(url="https://example.com/article?utm_source=twitter", title="Ilk"),
    )
    assert first.status == "executed"
    rows_after_first = await _bookmark_rows(db_session)

    second = await capture_bookmark(
        db_session,
        BookmarkCaptureIn(url="https://example.com/article", title="Ikinci"),
    )

    assert second.status == "noop"
    assert second.target_id == first.target_id
    assert second.before == {}
    assert any("duplicate" in warning.lower() for warning in second.warnings)
    assert await _bookmark_rows(db_session) == rows_after_first


async def test_capture_rejects_non_http_url() -> None:
    from pydantic import ValidationError

    for bad in ("ftp://example.com/x", "example.com", "javascript:alert(1)"):
        with pytest.raises(ValidationError):
            BookmarkCaptureIn(url=bad)


async def test_capture_rejects_unknown_collection() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        BookmarkCaptureIn.model_validate({"url": "https://example.com", "collection": "bookmarks"})


# ---------------------------------------------------------------------------
# forkos_bookmark_update
# ---------------------------------------------------------------------------


async def test_update_bookmark_changes_only_allowed_fields(db_session: AsyncSession) -> None:
    created = await capture_bookmark(
        db_session, BookmarkCaptureIn(url="https://example.org/doc", title="Belge")
    )
    bookmark_id = created.target_id

    receipt = await update_bookmark(
        db_session,
        BookmarkUpdateIn(bookmark_id=bookmark_id, favorite=True, read_status="read"),
        request_id="u1",
    )

    assert receipt.status == "executed"
    assert sorted(receipt.changed_fields) == ["favorite", "read_status"]
    assert receipt.after["favorite"] is True
    assert receipt.after["read_status"] == "read"

    bookmark = await db_session.get(Bookmark, uuid.UUID(bookmark_id))
    assert bookmark is not None
    assert bookmark.favorite is True and bookmark.read_status == "read"


async def test_update_bookmark_rejects_unsupported_fields(db_session: AsyncSession) -> None:
    """§43: silme / ilerleme / zenginleştirme alanları şemada YOKTUR."""
    from pydantic import ValidationError

    for forbidden in ({"scroll_progress": 50}, {"delete": True}, {"enrich": True}):
        with pytest.raises(ValidationError):
            BookmarkUpdateIn.model_validate({"bookmark_id": str(uuid.uuid4()), **forbidden})


async def test_update_bookmark_stale_guard(db_session: AsyncSession) -> None:
    created = await capture_bookmark(
        db_session, BookmarkCaptureIn(url="https://example.net/stale", title="Stale")
    )
    bookmark_id = uuid.UUID(created.target_id)
    entity = await db_session.get(Entity, bookmark_id)
    assert entity is not None
    stale = (datetime.now(UTC) - timedelta(days=2)).isoformat()

    with pytest.raises(ActionError, match="STALE_ACTION"):
        await update_bookmark(
            db_session,
            BookmarkUpdateIn(
                bookmark_id=str(bookmark_id), favorite=True, expected_updated_at=stale
            ),
        )

    bookmark = await db_session.get(Bookmark, bookmark_id)
    assert bookmark is not None and bookmark.favorite is False


async def test_update_bookmark_same_value_is_noop(db_session: AsyncSession) -> None:
    created = await capture_bookmark(
        db_session, BookmarkCaptureIn(url="https://example.net/same", title="Ayni")
    )
    bookmark_id = created.target_id

    first = await update_bookmark(
        db_session, BookmarkUpdateIn(bookmark_id=bookmark_id, read_status="read")
    )
    assert first.status == "executed"

    second = await update_bookmark(
        db_session, BookmarkUpdateIn(bookmark_id=bookmark_id, read_status="read")
    )
    assert second.status == "noop"


async def test_update_bookmark_unknown_target(db_session: AsyncSession) -> None:
    with pytest.raises(ActionError, match="TARGET_NOT_FOUND"):
        await update_bookmark(
            db_session, BookmarkUpdateIn(bookmark_id=str(uuid.uuid4()), favorite=True)
        )
