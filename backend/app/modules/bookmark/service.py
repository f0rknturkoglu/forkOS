"""Bookmark/Inbox is mantigi.

Kural 2: entity yazan her yer core/entity.py helper'larini kullanir.
Kural 3: anlamli her aksiyondan sonra log_event().
Kural 7: Inbox ve Bookmark ayni tablo -- ayirici alan `collection`.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import search as search_svc
from app.core import tags as tag_svc
from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.core.readability import fetch_and_extract
from app.core.time import local_day_bounds, local_today
from app.integrations.obsidian import service as obsidian_service
from app.integrations.obsidian.models import VaultItem
from app.modules.bookmark.models import COLLECTIONS, Bookmark, BookmarkHighlight
from app.modules.bookmark.schemas import (
    BookmarkBulkActionIn,
    BookmarkFullTextOut,
    BookmarkHighlightIn,
    BookmarkHighlightOut,
    BookmarkOut,
    BookmarkUpdate,
    CaptureIn,
    ConvertToTaskIn,
    CreateSourceNoteIn,
)

_TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid", "ref")


def normalize_url(url: str) -> str:
    """Takip parametrelerini atar, host'u sadelestirir. Dedup burada baslar."""
    parts = urlsplit(url.strip())
    query = "&".join(
        p
        for p in parts.query.split("&")
        if p and not p.split("=")[0].lower().startswith(_TRACKING_PREFIXES)
    )
    host = parts.netloc.lower().removeprefix("www.")
    return urlunsplit((parts.scheme.lower(), host, parts.path.rstrip("/"), query, ""))


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()


def _search_text(*parts: str | None) -> str:
    cleaned = []
    for p in parts:
        if p and p.strip():
            # Ilk 5000 karakteri alarak FTS indeksini koru
            cleaned.append(p.strip()[:5000])
    return " ".join(cleaned)


async def find_by_url(
    session: AsyncSession,
    url: str,
    *,
    exclude: uuid.UUID | None = None,
) -> Bookmark | None:
    """En eski eslesme -- "zaten kayitli" uyarisi icin."""
    stmt = (
        select(Bookmark)
        .where(Bookmark.url_hash == url_hash(url))
        .order_by(Bookmark.saved_at)
        .limit(1)
    )
    if exclude is not None:
        stmt = stmt.where(Bookmark.id != exclude)
    return (await session.execute(stmt)).scalar_one_or_none()


async def capture(
    session: AsyncSession,
    data: CaptureIn,
) -> tuple[Bookmark, bool, Bookmark | None]:
    """Idempotent capture.

    Doner: (bookmark, replayed, prior)
      replayed -> ayni client_uuid ikinci kez geldi, YENI KAYIT ACILMADI
      prior    -> ayni URL daha once kaydedilmis (hata degil, sadece bilgi)
    """
    if data.client_uuid:
        existing = (
            await session.execute(select(Bookmark).where(Bookmark.client_uuid == data.client_uuid))
        ).scalar_one_or_none()
        if existing is not None:
            return existing, True, None

    # Kendisiyle karsilastirmamak icin kayit ACILMADAN once bakilir.
    prior = await find_by_url(session, data.url)

    entity = await create_entity(
        session,
        type=Bookmark.ENTITY_TYPE,
        title=data.title.strip() or normalize_url(data.url),
        search_text=_search_text(data.url, data.description, data.selection, data.note, data.author),
    )
    bookmark = Bookmark(
        id=entity.id,
        url=data.url,
        url_hash=url_hash(data.url),
        description=data.description,
        selection=data.selection,
        note=data.note,
        collection=data.collection,
        source=data.source,
        client_uuid=data.client_uuid,
        hero_image_url=data.hero_image_url,
        favicon_url=data.favicon_url,
        author=data.author,
        reading_time_min=data.reading_time_min or 1,
        word_count=data.word_count or 0,
    )
    session.add(bookmark)
    await session.flush()

    if data.tags:
        await tag_svc.add_tags(session, entity.id, data.tags)

    await log_event(
        session,
        verb="bookmark.saved",
        entity_id=entity.id,
        entity_type="bookmark",
        payload={
            "collection": data.collection,
            "source": data.source,
            "url": data.url,
            "duplicate": prior is not None,
        },
    )
    await session.commit()
    return bookmark, False, prior


async def move(session: AsyncSession, bookmark_id: uuid.UUID, collection: str) -> Bookmark | None:
    bookmark = await session.get(Bookmark, bookmark_id)
    if bookmark is None:
        return None
    previous, bookmark.collection = bookmark.collection, collection
    await touch_entity(session, bookmark_id)
    if previous != collection:
        await log_event(
            session,
            verb="bookmark.moved",
            entity_id=bookmark_id,
            entity_type="bookmark",
            payload={"from": previous, "to": collection},
        )
    await session.commit()
    return bookmark


async def update(
    session: AsyncSession,
    bookmark_id: uuid.UUID,
    data: BookmarkUpdate,
) -> Bookmark | None:
    bookmark = await session.get(Bookmark, bookmark_id)
    if bookmark is None:
        return None

    if data.collection is not None and data.collection != bookmark.collection:
        await log_event(
            session,
            verb="bookmark.moved",
            entity_id=bookmark_id,
            entity_type="bookmark",
            payload={"from": bookmark.collection, "to": data.collection},
        )
        bookmark.collection = data.collection
    if data.note is not None:
        bookmark.note = data.note
    if data.description is not None:
        bookmark.description = data.description
    if data.favorite is not None and data.favorite != bookmark.favorite:
        bookmark.favorite = data.favorite
        await log_event(
            session,
            verb="bookmark.favorited",
            entity_id=bookmark_id,
            entity_type="bookmark",
            payload={"favorite": data.favorite},
        )
    if data.read_status is not None and data.read_status != bookmark.read_status:
        bookmark.read_status = data.read_status
        if data.read_status == "read":
            await log_event(
                session,
                verb="bookmark.read",
                entity_id=bookmark_id,
                entity_type="bookmark",
                payload={},
            )
    if data.hero_image_url is not None:
        bookmark.hero_image_url = data.hero_image_url
    if data.favicon_url is not None:
        bookmark.favicon_url = data.favicon_url
    if data.author is not None:
        bookmark.author = data.author
    if data.reading_time_min is not None:
        bookmark.reading_time_min = data.reading_time_min
    if data.scroll_progress is not None:
        bookmark.scroll_progress = data.scroll_progress
    if data.tags is not None:
        await tag_svc.set_tags(session, bookmark_id, data.tags)

    await touch_entity(
        session,
        bookmark_id,
        title=data.title.strip() if data.title else None,
        search_text=_search_text(
            bookmark.url,
            bookmark.description,
            bookmark.selection,
            bookmark.note,
            bookmark.author,
            bookmark.content_text,
        ),
    )
    await session.commit()
    return bookmark


async def delete(session: AsyncSession, bookmark_id: uuid.UUID) -> bool:
    """entity satirini siler -- bookmark, link ve tag cascade ile gider.

    event tablosuna DOKUNULMAZ (kural 3): entity_id NULL'a duser, entity_type kalir.
    """
    entity = await session.get(Entity, bookmark_id)
    if entity is None:
        return False
    await log_event(
        session,
        verb="bookmark.deleted",
        entity_id=bookmark_id,
        entity_type="bookmark",
        payload={"title": entity.title},
    )
    await session.flush()
    await session.delete(entity)
    await session.commit()
    return True


async def list_bookmarks(
    session: AsyncSession,
    *,
    collection: str | None = None,
    read_status: str | None = None,
    favorite: bool | None = None,
    source: str | None = None,
    q: str | None = None,
    tag: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[BookmarkOut]:
    stmt = (
        select(Bookmark, Entity.title)
        .join(Entity, Entity.id == Bookmark.id)
        .order_by(Bookmark.saved_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if collection:
        stmt = stmt.where(Bookmark.collection == collection)
    if read_status:
        stmt = stmt.where(Bookmark.read_status == read_status)
    if source:
        stmt = stmt.where(Bookmark.source == source)
    if favorite is not None:
        stmt = stmt.where(Bookmark.favorite.is_(favorite))
    if q and q.strip():
        stmt = stmt.where(search_svc.match_clause(q.strip()))
    if tag:
        ids = await tag_svc.entity_ids_with_tag(session, tag)
        if not ids:
            return []
        stmt = stmt.where(Bookmark.id.in_(ids))

    rows = (await session.execute(stmt)).all()
    if not rows:
        return []
    b_ids = [b.id for b, _ in rows]
    tag_map = await tag_svc.tags_for(session, b_ids)

    # Highlight sayilari
    hl_counts = dict(
        (
            await session.execute(
                select(BookmarkHighlight.bookmark_id, func.count())
                .where(BookmarkHighlight.bookmark_id.in_(b_ids))
                .group_by(BookmarkHighlight.bookmark_id)
            )
        ).all()
    )

    hashes = list({b.url_hash for b, _ in rows})
    other_bookmarks = (
        await session.execute(
            select(Bookmark.url_hash, Bookmark.collection)
            .where(Bookmark.url_hash.in_(hashes))
        )
    ).all()
    collection_by_hash: dict[str, list[str]] = {}
    for h, col in other_bookmarks:
        collection_by_hash.setdefault(h, []).append(col)

    out: list[BookmarkOut] = []
    for b, title in rows:
        all_cols = collection_by_hash.get(b.url_hash, [])
        is_dup = len(all_cols) > 1
        other_col = next((c for c in all_cols if c != b.collection), None) if is_dup else None
        out.append(
            _to_out(
                b,
                title,
                tag_map.get(b.id, []),
                is_duplicate=is_dup,
                existing_collection=other_col,
                highlights_count=hl_counts.get(b.id, 0),
            )
        )
    return out


async def get(session: AsyncSession, bookmark_id: uuid.UUID) -> BookmarkOut | None:
    row = (
        await session.execute(
            select(Bookmark, Entity.title)
            .join(Entity, Entity.id == Bookmark.id)
            .where(Bookmark.id == bookmark_id)
        )
    ).first()
    if row is None:
        return None
    bookmark, title = row
    tag_map = await tag_svc.tags_for(session, [bookmark.id])
    prior = await find_by_url(session, bookmark.url, exclude=bookmark.id)

    hl_count = (
        await session.execute(
            select(func.count())
            .select_from(BookmarkHighlight)
            .where(BookmarkHighlight.bookmark_id == bookmark_id)
        )
    ).scalar_one()

    return _to_out(
        bookmark,
        title,
        tag_map.get(bookmark.id, []),
        is_duplicate=prior is not None,
        existing_collection=prior.collection if prior else None,
        highlights_count=hl_count,
    )


def _to_out(
    bookmark: Bookmark,
    title: str,
    tags: list[str],
    *,
    is_duplicate: bool = False,
    existing_collection: str | None = None,
    highlights_count: int = 0,
) -> BookmarkOut:
    return BookmarkOut(
        id=bookmark.id,
        title=title,
        url=bookmark.url,
        description=bookmark.description,
        collection=bookmark.collection,
        queue_kind=bookmark.queue_kind,
        source=bookmark.source,
        read_status=bookmark.read_status,
        favorite=bookmark.favorite,
        note=bookmark.note,
        selection=bookmark.selection,
        saved_at=bookmark.saved_at,
        tags=tags,
        is_duplicate=is_duplicate,
        existing_collection=existing_collection,
        hero_image_url=bookmark.hero_image_url,
        favicon_url=bookmark.favicon_url,
        author=bookmark.author,
        published_at=bookmark.published_at,
        reading_time_min=bookmark.reading_time_min,
        word_count=bookmark.word_count,
        scroll_progress=bookmark.scroll_progress,
        highlights_count=highlights_count,
    )


async def get_full_text(
    session: AsyncSession, bookmark_id: uuid.UUID
) -> BookmarkFullTextOut | None:
    row = (
        await session.execute(
            select(Bookmark, Entity.title)
            .join(Entity, Entity.id == Bookmark.id)
            .where(Bookmark.id == bookmark_id)
        )
    ).first()
    if row is None:
        return None
    bookmark, title = row

    # Icerik henuz cekilmemisse veya bossa readability ile cek
    if not bookmark.content_html:
        extracted = await fetch_and_extract(bookmark.url)
        if extracted and extracted.content_html:
            bookmark.content_html = extracted.content_html
            bookmark.content_text = extracted.content_text
            if extracted.hero_image_url and not bookmark.hero_image_url:
                bookmark.hero_image_url = extracted.hero_image_url
            if extracted.favicon_url and not bookmark.favicon_url:
                bookmark.favicon_url = extracted.favicon_url
            if extracted.author and not bookmark.author:
                bookmark.author = extracted.author
            if extracted.published_at and not bookmark.published_at:
                bookmark.published_at = extracted.published_at
            if extracted.word_count:
                bookmark.word_count = extracted.word_count
            if extracted.reading_time_min:
                bookmark.reading_time_min = extracted.reading_time_min

            await touch_entity(
                session,
                bookmark.id,
                search_text=_search_text(
                    bookmark.url,
                    bookmark.description,
                    bookmark.selection,
                    bookmark.note,
                    bookmark.author,
                    bookmark.content_text,
                ),
            )
            await session.commit()

    hl_stmt = (
        select(BookmarkHighlight)
        .where(BookmarkHighlight.bookmark_id == bookmark_id)
        .order_by(BookmarkHighlight.anchor_index, BookmarkHighlight.created_at)
    )
    highlights = list((await session.execute(hl_stmt)).scalars().all())

    return BookmarkFullTextOut(
        id=bookmark.id,
        title=title,
        url=bookmark.url,
        content_html=bookmark.content_html,
        content_text=bookmark.content_text,
        hero_image_url=bookmark.hero_image_url,
        favicon_url=bookmark.favicon_url,
        author=bookmark.author,
        published_at=bookmark.published_at,
        reading_time_min=bookmark.reading_time_min,
        word_count=bookmark.word_count,
        scroll_progress=bookmark.scroll_progress,
        highlights=[BookmarkHighlightOut.model_validate(h) for h in highlights],
    )


async def update_progress(
    session: AsyncSession, bookmark_id: uuid.UUID, scroll_progress: int
) -> BookmarkOut | None:
    bookmark = await session.get(Bookmark, bookmark_id)
    if bookmark is None:
        return None

    bookmark.scroll_progress = max(0, min(100, scroll_progress))
    was_unread = bookmark.read_status == "unread"
    if bookmark.scroll_progress >= 90 and was_unread:
        bookmark.read_status = "read"
        await log_event(
            session,
            verb="bookmark.read",
            entity_id=bookmark_id,
            entity_type="bookmark",
            payload={"progress": bookmark.scroll_progress, "trigger": "auto_scroll"},
        )

    await touch_entity(session, bookmark_id)
    await log_event(
        session,
        verb="bookmark.scrolled",
        entity_id=bookmark_id,
        entity_type="bookmark",
        payload={"scroll_progress": bookmark.scroll_progress},
    )
    await session.commit()
    return await get(session, bookmark_id)


async def add_highlight(
    session: AsyncSession, bookmark_id: uuid.UUID, data: BookmarkHighlightIn
) -> BookmarkHighlightOut | None:
    bookmark = await session.get(Bookmark, bookmark_id)
    if bookmark is None:
        return None

    highlight = BookmarkHighlight(
        id=uuid.uuid4(),
        bookmark_id=bookmark_id,
        text=data.text.strip(),
        note=data.note.strip() if data.note else None,
        color=data.color or "yellow",
        anchor_index=data.anchor_index or 0,
        position_start=data.position_start,
        position_end=data.position_end,
    )
    session.add(highlight)
    await touch_entity(session, bookmark_id)
    await log_event(
        session,
        verb="bookmark.highlighted",
        entity_id=bookmark_id,
        entity_type="bookmark",
        payload={
            "highlight_id": str(highlight.id),
            "color": highlight.color,
            "snippet": highlight.text[:80],
        },
    )
    await session.commit()
    return BookmarkHighlightOut.model_validate(highlight)


async def delete_highlight(
    session: AsyncSession, bookmark_id: uuid.UUID, highlight_id: uuid.UUID
) -> bool:
    stmt = select(BookmarkHighlight).where(
        BookmarkHighlight.id == highlight_id,
        BookmarkHighlight.bookmark_id == bookmark_id,
    )
    hl = (await session.execute(stmt)).scalar_one_or_none()
    if hl is None:
        return False

    await session.delete(hl)
    await touch_entity(session, bookmark_id)
    await session.commit()
    return True


async def list_highlights(
    session: AsyncSession, bookmark_id: uuid.UUID
) -> list[BookmarkHighlightOut]:
    stmt = (
        select(BookmarkHighlight)
        .where(BookmarkHighlight.bookmark_id == bookmark_id)
        .order_by(BookmarkHighlight.anchor_index, BookmarkHighlight.created_at)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [BookmarkHighlightOut.model_validate(h) for h in rows]


async def convert_highlight_to_flashcard(
    session: AsyncSession, bookmark_id: uuid.UUID, highlight_id: uuid.UUID
) -> uuid.UUID:
    bookmark = await session.get(Bookmark, bookmark_id)
    if bookmark is None:
        raise ValueError("Bookmark bulunamadi")
    entity = await session.get(Entity, bookmark_id)
    if entity is None:
        raise ValueError("Entity bulunamadi")

    stmt = select(BookmarkHighlight).where(
        BookmarkHighlight.id == highlight_id,
        BookmarkHighlight.bookmark_id == bookmark_id,
    )
    hl = (await session.execute(stmt)).scalar_one_or_none()
    if hl is None:
        raise ValueError("Highlight bulunamadi")

    from app.core.links import link
    from app.modules.flashcard import service as flashcard_svc
    from app.modules.flashcard.schemas import CardIn

    deck = await flashcard_svc._find_or_create_deck(session, "Yer İmleri ve Okuma")
    front = hl.note.strip() if hl.note else f"[{entity.title}] Alıntı"
    back = hl.text.strip()

    card_dict = await flashcard_svc.create_card(session, deck.id, CardIn(front=front, back=back))
    if card_dict is None:
        raise ValueError("Kart olusturulamadi")
    card_id = card_dict["id"]
    await link(session, card_id, bookmark.id, "generated_from")
    await session.commit()
    return card_id


async def bulk_action(session: AsyncSession, data: BookmarkBulkActionIn) -> int:
    if not data.bookmark_ids:
        return 0
    stmt = select(Bookmark).where(Bookmark.id.in_(data.bookmark_ids))
    bookmarks = (await session.execute(stmt)).scalars().all()
    if not bookmarks:
        return 0

    affected = 0
    if data.action == "move" and data.collection:
        for b in bookmarks:
            if b.collection != data.collection:
                old_col = b.collection
                b.collection = data.collection
                await touch_entity(session, b.id)
                await log_event(
                    session,
                    verb="bookmark.moved",
                    entity_id=b.id,
                    entity_type="bookmark",
                    payload={"from": old_col, "to": data.collection},
                )
                affected += 1
    elif data.action == "read_status" and data.read_status:
        for b in bookmarks:
            if b.read_status != data.read_status:
                b.read_status = data.read_status
                await touch_entity(session, b.id)
                if data.read_status == "read":
                    await log_event(
                        session,
                        verb="bookmark.read",
                        entity_id=b.id,
                        entity_type="bookmark",
                        payload={},
                    )
                affected += 1
    elif data.action == "tag" and data.tags is not None:
        for b in bookmarks:
            await tag_svc.add_tags(session, b.id, data.tags)
            await touch_entity(session, b.id)
            affected += 1
    elif data.action == "delete":
        for b in bookmarks:
            entity = await session.get(Entity, b.id)
            if entity:
                await log_event(
                    session,
                    verb="bookmark.deleted",
                    entity_id=b.id,
                    entity_type="bookmark",
                    payload={"title": entity.title},
                )
                await session.delete(entity)
                affected += 1

    await session.commit()
    return affected


async def convert_to_task(
    session: AsyncSession,
    bookmark_id: uuid.UUID,
    data: ConvertToTaskIn,
) -> uuid.UUID:
    bookmark = await session.get(Bookmark, bookmark_id)
    if bookmark is None:
        raise ValueError("Bookmark bulunamadi")
    entity = await session.get(Entity, bookmark_id)
    if entity is None:
        raise ValueError("Entity bulunamadi")

    from app.core.links import link
    from app.modules.todo import service as todo_svc
    from app.modules.todo.schemas import TodoIn

    desc_parts = [f"Kaynak: {bookmark.url}"]
    if bookmark.note:
        desc_parts.append(f"Not: {bookmark.note}")
    if bookmark.selection:
        desc_parts.append(f"Alinti: {bookmark.selection}")
    description = "\n\n".join(desc_parts)

    todo_in = TodoIn(
        title=entity.title,
        description=description,
        priority=data.priority,
        plan_day=data.plan_day,
        due_at=data.due_at,
    )
    todo_out = await todo_svc.create(session, todo_in, commit=False)
    await link(session, todo_out.id, bookmark.id, "task_for")

    old_col = bookmark.collection
    bookmark.collection = "archive"
    await touch_entity(session, bookmark.id)
    await log_event(
        session,
        verb="bookmark.moved",
        entity_id=bookmark.id,
        entity_type="bookmark",
        payload={"from": old_col, "to": "archive", "reason": "converted_to_task"},
    )
    await session.commit()
    return todo_out.id


async def ensure_source_note(
    session: AsyncSession,
    bookmark_id: uuid.UUID,
    data: CreateSourceNoteIn,
) -> VaultItem:
    """Yer iminin kanonik Vault kaynak notunu çözer veya oluşturur.

    Kimlik yer iminin UUID'sidir; aynı yer imi için ikinci dosya üretilmez.
    Yer iminin KENDİ alanları (url, read state, highlights, not) operasyonel
    kalır -- buraya yalnızca notun başlangıç gövdesi olarak yansır. Makale
    gövdesi KOPYALANMAZ (PHASE 3 §36).
    """
    bookmark = await session.get(Bookmark, bookmark_id)
    if bookmark is None:
        raise ValueError("Bookmark bulunamadi")
    entity = await session.get(Entity, bookmark_id)
    if entity is None:
        raise ValueError("Entity bulunamadi")

    body_parts = [f"# {entity.title}", "", f"Source: {bookmark.url}", "", "## Notlar"]
    if bookmark.note:
        body_parts.extend(["", f"> Not: {bookmark.note}"])
    body_parts.extend(["", "## Öne çıkanlar"])
    highlights = await list_highlights(session, bookmark_id)
    if highlights:
        body_parts.extend(f"> {highlight.text}" for highlight in highlights)
    elif bookmark.selection:
        body_parts.extend(["", f"> Alıntı: {bookmark.selection}"])
    if data.additional_text:
        body_parts.extend(["", data.additional_text])

    return await obsidian_service.ensure_entity_knowledge_note(
        session,
        bookmark_id,
        initial_body="\n".join(body_parts),
        source_url=bookmark.url,
    )


async def enrich_bookmark(session: AsyncSession, bookmark_id: uuid.UUID) -> BookmarkOut | None:
    bookmark = await session.get(Bookmark, bookmark_id)
    if bookmark is None:
        return None
    entity = await session.get(Entity, bookmark_id)
    if entity is None:
        return None

    extracted = await fetch_and_extract(bookmark.url)
    if extracted:
        if extracted.title and (
            entity.title == bookmark.url
            or not entity.title
            or entity.title == normalize_url(bookmark.url)
        ):
            entity.title = extracted.title
        if extracted.content_html:
            bookmark.content_html = extracted.content_html
        if extracted.content_text:
            bookmark.content_text = extracted.content_text
        if extracted.hero_image_url and not bookmark.hero_image_url:
            bookmark.hero_image_url = extracted.hero_image_url
        if extracted.favicon_url and not bookmark.favicon_url:
            bookmark.favicon_url = extracted.favicon_url
        if extracted.author and not bookmark.author:
            bookmark.author = extracted.author
        if extracted.published_at and not bookmark.published_at:
            bookmark.published_at = extracted.published_at
        if extracted.word_count:
            bookmark.word_count = extracted.word_count
        if extracted.reading_time_min:
            bookmark.reading_time_min = extracted.reading_time_min

        await touch_entity(
            session,
            bookmark.id,
            title=entity.title,
            search_text=_search_text(
                bookmark.url,
                bookmark.description,
                bookmark.selection,
                bookmark.note,
                bookmark.author,
                bookmark.content_text,
            ),
        )
        await session.commit()

    return await get(session, bookmark_id)


async def export_bookmarks(session: AsyncSession) -> str:
    """Netscape Bookmark HTML formatinda tum yer imlerini cikarir."""
    stmt = (
        select(Bookmark, Entity.title)
        .join(Entity, Entity.id == Bookmark.id)
        .order_by(Bookmark.saved_at.desc())
    )
    rows = (await session.execute(stmt)).all()
    tag_map = await tag_svc.tags_for(session, [b.id for b, _ in rows])

    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        "<!-- This is an automatically generated file. -->",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>forkOS Bookmarks</TITLE>",
        "<H1>forkOS Bookmarks</H1>",
        "<DL><p>",
    ]

    for b, title in rows:
        ts = int(b.saved_at.timestamp())
        tags = ",".join(tag_map.get(b.id, []))
        tag_attr = f' TAGS="{tags}"' if tags else ""
        lines.append(f'    <DT><A HREF="{b.url}" ADD_DATE="{ts}"{tag_attr}>{title}</A>')
        if b.note:
            lines.append(f"    <DD>{b.note}")

    lines.append("</DL><p>")
    return "\n".join(lines)


async def import_bookmarks(
    session: AsyncSession, raw_content: str, default_collection: str = "inbox"
) -> int:
    """Netscape Bookmark HTML veya Pocket JSON formatindaki veriyi ice aktarir."""
    imported_count = 0

    # 1. Pocket JSON format denemesi
    if raw_content.strip().startswith("{") and "list" in raw_content:
        try:
            data = json.loads(raw_content)
            items = data.get("list", {})
            if isinstance(items, dict):
                for item in items.values():
                    given_url = item.get("given_url") or item.get("resolved_url")
                    if not given_url:
                        continue
                    title = item.get("given_title") or item.get("resolved_title") or given_url
                    author = item.get("authors", {})
                    author_name = None
                    if isinstance(author, dict) and author:
                        author_name = list(author.values())[0].get("name")

                    read_status = "read" if str(item.get("status")) == "1" else "unread"
                    col = "archive" if read_status == "read" else default_collection

                    cap = CaptureIn(
                        url=given_url,
                        title=title,
                        collection=col,
                        source="pocket_import",
                        author=author_name,
                        word_count=int(item.get("word_count", 0) or 0),
                        reading_time_min=max(1, math.ceil(int(item.get("word_count", 0) or 0) / 200))
                        if item.get("word_count")
                        else 1,
                    )
                    b, _, _ = await capture(session, cap)
                    if read_status == "read":
                        b.read_status = "read"
                        await session.commit()
                    imported_count += 1
                return imported_count
        except Exception:
            pass

    # 2. Netscape Bookmark HTML format tespiti
    a_regex = re.compile(
        r'<A\s+HREF=["\']([^"\']+)["\'](?:[^>]*?TAGS=["\']([^"\']*)["\'])?[^>]*>([^<]+)</A>',
        re.IGNORECASE,
    )
    for match in a_regex.finditer(raw_content):
        url, tags_str, title = match.group(1).strip(), match.group(2), match.group(3).strip()
        if not url.startswith(("http://", "https://")):
            continue
        tags = [t.strip() for t in tags_str.split(",")] if tags_str else []
        cap = CaptureIn(
            url=url,
            title=title,
            collection=default_collection,
            source="html_import",
            tags=tags,
        )
        try:
            await capture(session, cap)
            imported_count += 1
        except Exception:
            pass

    return imported_count


async def stats(session: AsyncSession) -> dict:
    per_collection = dict(
        (
            await session.execute(
                select(Bookmark.collection, func.count()).group_by(Bookmark.collection)
            )
        ).all()
    )
    unread = (
        await session.execute(
            select(func.count()).select_from(Bookmark).where(Bookmark.read_status == "unread")
        )
    ).scalar_one()
    midnight, tomorrow = local_day_bounds(local_today())
    saved_today = (
        await session.execute(
            select(func.count()).select_from(Bookmark).where(
                Bookmark.saved_at >= midnight,
                Bookmark.saved_at < tomorrow,
            )
        )
    ).scalar_one()
    return {
        "inbox": per_collection.get("inbox", 0),
        "unread": unread,
        "saved_today": saved_today,
        "total": sum(per_collection.values()),
        "collections": [{"collection": c, "count": per_collection.get(c, 0)} for c in COLLECTIONS],
    }
