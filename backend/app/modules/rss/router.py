from __future__ import annotations

import uuid
from datetime import datetime
from xml.etree.ElementTree import ParseError

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.bookmark import service as bookmark_svc
from app.modules.bookmark.models import COLLECTIONS
from app.modules.bookmark.schemas import BookmarkOut
from app.modules.rss import service
from app.modules.rss.models import Feed, FeedItem
from app.modules.rss.schemas import (
    FeedIn,
    FeedItemOut,
    FeedOut,
    FeedUpdate,
    ImportResult,
    RssStats,
    SaveItemIn,
)

router = APIRouter(tags=["rss"])


@router.get("/rss/feeds", response_model=list[FeedOut])
async def list_feeds(
    category: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    return await service.list_feeds(session, category=category)


@router.post("/rss/feeds", response_model=FeedOut, status_code=201)
async def add_feed(body: FeedIn, session: AsyncSession = Depends(get_session)):
    feed, created = await service.add_feed(session, body, probe=body.probe, commit=False)
    if body.probe:
        from app.modules.system.experience import activate_rss

        await activate_rss(session, commit=False)
    await session.commit()
    feeds = await service.list_feeds(session)
    return next(f for f in feeds if f.id == feed.id)


@router.patch("/rss/feeds/{feed_id}", response_model=FeedOut)
async def update_feed(
    feed_id: uuid.UUID,
    body: FeedUpdate,
    session: AsyncSession = Depends(get_session),
):
    if await service.update_feed(session, feed_id, body) is None:
        raise HTTPException(404)
    feeds = await service.list_feeds(session)
    return next(f for f in feeds if f.id == feed_id)


@router.delete("/rss/feeds/{feed_id}", status_code=204)
async def delete_feed(feed_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_feed(session, feed_id):
        raise HTTPException(404)


@router.post("/rss/feeds/{feed_id}/refresh")
async def refresh_feed(feed_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Tek feed'i simdi cek. Worker'i beklemeden test etmek icin."""
    feed = await session.get(Feed, feed_id)
    if feed is None:
        raise HTTPException(404)
    status, added = await service.poll_feed(session, feed)
    return {"status": status, "added": added}


@router.post("/rss/import", response_model=ImportResult)
async def import_opml(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """OPML disa aktarimi (Feedly/Inoreader/NetNewsWire) -> feed'ler.

    Kategori, feed'i saran outline grubunun basligindan gelir.
    """
    content = await file.read(2_000_001)
    try:
        added, skipped, names = await service.import_opml(session, content)
    except (ValidationError, ValueError, ParseError) as exc:
        raise HTTPException(
            422,
            "OPML geçersiz; hiçbir abonelik kaydedilmedi. HTTP(S) adreslerini ve dosya sınırlarını kontrol et.",
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(503, "OPML işlem süresi aşıldı; hiçbir abonelik kaydedilmedi") from exc
    if added:
        # Sorunun cozumu: import sonrasi yazilar aninda cekilsin diye
        # arka plan tazelemesi kuyruklanir (worker'i 30 dk beklemene gerek yok).
        background.add_task(service.refresh_all)
    return ImportResult(added=added, skipped=skipped, feeds=names[:50])


@router.get("/rss/items", response_model=list[FeedItemOut])
async def list_items(
    feed_id: uuid.UUID | None = None,
    category: str | None = None,
    unread_only: bool = False,
    saved_only: bool = False,
    since: datetime | None = None,
    q: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    return await service.list_items(
        session,
        feed_id=feed_id,
        category=category,
        unread_only=unread_only,
        saved_only=saved_only,
        since=since,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.get("/rss/items/{item_id}", response_model=FeedItemOut)
async def get_item(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Okuma bolmesi detayi -- content burada dolu gelir (liste hafif kalir)."""
    item = await service.get_item(session, item_id)
    if item is None:
        raise HTTPException(404)
    return item


@router.get("/rss/items/{item_id}/fulltext")
async def item_full_text(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Tam metin: cache'te varsa dondur, yoksa talebe bagli fetch edip kalicilastirir.

    Fetch basarisiz / cikarilamazsa full_text: null doner (hata mesaji yok;
    istemci butonu tekrar gosterir). Ayni item'a eszamanli cift istek null gorur.
    """
    item = await session.get(FeedItem, item_id)
    if item is None:
        raise HTTPException(404)
    return {"full_text": await service.get_item_full_text(session, item_id)}


@router.post("/rss/items/{item_id}/read", response_model=FeedItemOut)
async def mark_read(
    item_id: uuid.UUID,
    read: bool = Query(True),
    session: AsyncSession = Depends(get_session),
):
    if await service.mark_read(session, item_id, read=read) is None:
        raise HTTPException(404)
    item = await service.get_item(session, item_id)
    if item is None:
        raise HTTPException(404)
    return item


@router.post("/rss/read-all")
async def mark_all_read(
    feed_id: uuid.UUID | None = None,
    category: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    return {"marked": await service.mark_all_read(session, feed_id=feed_id, category=category)}


@router.post("/rss/items/{item_id}/save", response_model=BookmarkOut, status_code=201)
async def save_item(
    item_id: uuid.UUID,
    body: SaveItemIn,
    session: AsyncSession = Depends(get_session),
):
    """Item -> bookmark + link(feed_item -> bookmark, 'saved_from')."""
    if body.collection not in COLLECTIONS:
        raise HTTPException(422, f"collection su olmali: {COLLECTIONS}")
    bookmark = await service.save_item(session, item_id, body.collection)
    if bookmark is None:
        raise HTTPException(404)
    return await bookmark_svc.get(session, bookmark.id)


@router.get("/rss/stats", response_model=RssStats)
async def rss_stats(session: AsyncSession = Depends(get_session)):
    return await service.stats(session)


@router.post("/rss/refresh-all")
async def refresh_all(
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Suresi gelmis tum feed'leri arka planda ceker; yanit hemen doner.

    Cekim bir kez kuyruklanir; tekrar tiklamak suresi gelmemis feed bulamaz.
    """
    due = await service.due_feeds(session, interval_minutes=None)
    background.add_task(service.refresh_all)
    return {"started": len(due)}
