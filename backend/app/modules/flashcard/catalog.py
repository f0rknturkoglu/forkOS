"""Explicit catalog reads and imports reuse source health and canonical card writes."""

import time

import httpx
from fastapi import HTTPException

from app.core import runs
from app.modules.flashcard import service
from app.sources.ankiweb import AnkiWebSource, deck_info, download_deck


def catalog_error(exc):
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {429, 503}:
        delay = exc.response.headers.get("retry-after", "60")
        return HTTPException(
            429,
            "AnkiWeb misafir arama sınırına ulaşıldı. Destenin AnkiWeb bağlantısını buraya yapıştırabilirsin."
            if "Please log in" in exc.response.text
            else "AnkiWeb istek sınırına ulaşıldı. Biraz sonra yeniden dene.",
            headers={"Retry-After": delay},
        )
    return HTTPException(
        422, str(exc) if isinstance(exc, ValueError) else "AnkiWeb’e bağlanılamadı"
    )


_CACHE = {}


async def list_catalog(db, search):
    key = search.strip().casefold() or "english"
    cached = _CACHE.get(key)
    if cached and time.monotonic() - cached[0] < 300:
        return cached[1]
    source = AnkiWebSource(key)
    run = await runs.start_run(db, source.id)
    try:
        result = await source.fetch()
        status = runs.EMPTY if not result.items and key == "english" else runs.OK
        await runs.finish_run(
            db,
            run,
            status=status,
            items_found=len(result.items),
            telemetry=result.telemetry.as_dict(),
        )
        await runs.check_source_health(db, source.id, status=status, label="AnkiWeb")
        await db.commit()
    except (ValueError, httpx.HTTPError) as exc:
        await runs.finish_run(db, run, status=runs.ERROR, error=str(exc))
        await runs.check_source_health(db, source.id, status=runs.ERROR, label="AnkiWeb")
        await db.commit()
        raise catalog_error(exc) from exc
    rows = [
        {"id": int(item.external_id), "title": item.title, "url": item.url, **item.extra}
        for item in result.items
    ]
    if len(_CACHE) >= 32:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = (time.monotonic(), rows)
    return rows


async def preview(shared_id):
    try:
        data = await deck_info(shared_id)
    except (ValueError, httpx.HTTPError) as exc:
        raise catalog_error(exc) from exc
    return {key: value for key, value in data.items() if key != "download_key"}


async def import_shared(db, shared_id):
    source = "ankiweb:download"
    run = await runs.start_run(db, source)
    try:
        info, content = await download_deck(shared_id)
    except (ValueError, httpx.HTTPError) as exc:
        await runs.finish_run(db, run, status=runs.ERROR, error=str(exc))
        await runs.check_source_health(db, source, status=runs.ERROR, label="AnkiWeb indirme")
        await db.commit()
        raise catalog_error(exc) from exc
    await runs.finish_run(db, run, status=runs.OK, items_found=1)
    await db.commit()
    try:
        return await service.import_cards(db, content, f"{shared_id}.apkg", info["title"])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
