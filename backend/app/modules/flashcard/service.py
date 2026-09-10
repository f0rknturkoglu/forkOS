"""Anki benzeri flashcard servisi: SM-2 zamanlama + .apkg/.csv ic aktarim.

Zamanlama (grade: 0=Again, 1=Hard, 2=Good, 3=Easy):

* Yeni kart (due_at NULL): again -> 10 dk, hard/good -> 1 gun, easy -> 4 gun.
* Bilinen kart: interval again x0.5 (min 1), hard x1.2, good x ease,
  easy x ease x 1.3. Ease ayari: again -0.20, hard -0.15, good 0, easy +0.15
  (min 1.3). due_at = bugun (yerel gun basi) + interval.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
import tempfile
import uuid
import zipfile
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity, Link
from app.core.time import local_datetime, local_today
from app.modules.flashcard.models import FlashcardCard, FlashcardDeck

#: Yeni kartin ilk tekrarinda interval (gun). 0 = dakika bazli (again, 10 dk).
NEW_INTERVAL_DAYS = {0: 0, 1: 1, 2: 1, 3: 4}
EASE_DELTA = {0: -0.20, 1: -0.15, 2: 0.0, 3: 0.15}
MIN_EASE = 1.3
REVIEW_LIMIT = 40
DEFAULT_IMPORT_DECK = "İçe Aktarılan Kartlar"
#: Anki esigi: 21 gunden uzun aralikli kart "olgun" sayilir (SRS dagilim cubugu).
MATURE_INTERVAL_DAYS = 21
#: Cram kuyrugu: desteler genelinde en cok unutulan kartlar.
MISSED_LIMIT = 30
#: Deste <-> not/dokuman bagi. Bu iliskiler "bu kartlar su kaynaktan" demektir.
STUDY_RELATIONS = ("studies", "generated_from")


def _round_interval(value: float) -> int:
    return max(1, int(value + 0.5))


def sm2_next(
    interval_days: int, ease: float, grade: int, is_new: bool
) -> tuple[int, float, datetime]:
    """SM-2 turevi zamanlama: (yeni interval, yeni ease, due_at)."""
    ease = max(MIN_EASE, round(ease + EASE_DELTA[grade], 2))
    if is_new:
        interval = NEW_INTERVAL_DAYS[grade]
        if grade == 0:
            due_at = datetime.now(UTC) + timedelta(minutes=10)
        else:
            due_at = local_datetime(local_today()) + timedelta(days=interval)
        return interval, ease, due_at
    if grade == 0:
        interval = _round_interval(interval_days * 0.5)
    elif grade == 1:
        interval = _round_interval(interval_days * 1.2)
    elif grade == 2:
        interval = _round_interval(interval_days * ease)
    else:  # 3 = Easy
        interval = _round_interval(interval_days * ease * 1.3)
    due_at = local_datetime(local_today()) + timedelta(days=interval)
    return interval, ease, due_at


# ---------------------------------------------------------------------------
# Destekler (deck)
# ---------------------------------------------------------------------------


def card_out(card: FlashcardCard) -> dict:
    return {
        "id": card.id,
        "deck_id": card.deck_id,
        "front": card.front,
        "back": card.back,
        "interval_days": card.interval_days,
        "ease": card.ease,
        "due_at": card.due_at,
        "reps": card.reps,
        "lapses": card.lapses,
        "suspended": card.suspended,
    }


async def _deck_out(session: AsyncSession, deck: FlashcardDeck, title: str) -> dict:
    row = (
        await session.execute(
            select(
                func.count().label("card_count"),
                # (card_count, due_count, new_count) sirasi: asagidaki tuple ile eslesir.
                func.count().filter(
                    FlashcardCard.due_at <= datetime.now(UTC), FlashcardCard.suspended.is_(False)
                ).label("due_count"),
                func.count().filter(FlashcardCard.due_at.is_(None)).label("new_count"),
                func.count().filter(
                    FlashcardCard.interval_days > MATURE_INTERVAL_DAYS
                ).label("mature_count"),
            ).where(FlashcardCard.deck_id == deck.id)
        )
    ).one()
    return {
        "id": deck.id,
        "title": title,
        "card_count": row.card_count,
        "due_count": row.due_count,
        "new_count": row.new_count,
        "mature_count": row.mature_count,
        "created_at": deck.created_at,
    }


async def list_decks(session: AsyncSession, linked_to: uuid.UUID | None = None) -> list[dict]:
    """Desteler + SRS sayaclari.

    `linked_to` verilirse yalnizca o kayda bagli desteler doner (not/dokuman ->
    deste bagi "studies"/"generated_from"): not sayfasi "bu notun kartlari"
    rozetini tek cagriyla doldurur.
    """
    stmt = (
        select(FlashcardDeck, Entity.title)
        .join(Entity, Entity.id == FlashcardDeck.id)
        .order_by(FlashcardDeck.created_at.desc())
    )
    if linked_to is not None:
        stmt = stmt.where(
            FlashcardDeck.id.in_(
                select(Link.from_id).where(
                    Link.to_id == linked_to,
                    Link.relation.in_(STUDY_RELATIONS),
                )
            )
        )
    decks = list((await session.execute(stmt)).all())
    if not decks:
        return []
    counts = {
        deck_id: (card_count, due_count, new_count, mature_count)
        for deck_id, card_count, due_count, new_count, mature_count in (
            await session.execute(
                select(
                    FlashcardCard.deck_id,
                    func.count(),
                    func.count().filter(
                        FlashcardCard.due_at <= datetime.now(UTC),
                        FlashcardCard.suspended.is_(False),
                    ),
                    func.count().filter(FlashcardCard.due_at.is_(None)),
                    func.count().filter(FlashcardCard.interval_days > MATURE_INTERVAL_DAYS),
                )
                .where(FlashcardCard.deck_id.in_([deck.id for deck, _ in decks]))
                .group_by(FlashcardCard.deck_id)
            )
        ).all()
    }
    empty = (0, 0, 0, 0)
    return [
        {
            "id": deck.id,
            "title": title,
            "card_count": counts.get(deck.id, empty)[0],
            "due_count": counts.get(deck.id, empty)[1],
            "new_count": counts.get(deck.id, empty)[2],
            "mature_count": counts.get(deck.id, empty)[3],
            "created_at": deck.created_at,
        }
        for deck, title in decks
    ]


async def create_deck(session: AsyncSession, data) -> dict:
    entity = await create_entity(
        session, type=FlashcardDeck.ENTITY_TYPE, title=data.title, search_text=data.title
    )
    deck = FlashcardDeck(id=entity.id)
    session.add(deck)
    await log_event(
        session, verb="flashcard.deck_created", entity_id=deck.id,
        entity_type=FlashcardDeck.ENTITY_TYPE, payload={"title": data.title},
    )
    await session.commit()
    return await _deck_out(session, deck, data.title)


async def patch_deck(session: AsyncSession, deck_id, data) -> dict | None:
    deck = await session.get(FlashcardDeck, deck_id)
    if deck is None:
        return None
    await touch_entity(session, deck.id, title=data.title, search_text=data.title)
    await session.commit()
    title = (
        await session.execute(select(Entity.title).where(Entity.id == deck.id))
    ).scalar_one()
    return await _deck_out(session, deck, title)


async def delete_deck(session: AsyncSession, deck_id) -> bool:
    deck = await session.get(FlashcardDeck, deck_id)
    if deck is None:
        return False
    await delete_entity(session, deck.id)
    await session.commit()
    return True


# ---------------------------------------------------------------------------
# Kartlar
# ---------------------------------------------------------------------------


async def list_cards(
    session: AsyncSession,
    deck_id,
    due: bool,
    only_lapses: bool = False,
    q: str | None = None,
) -> list[dict] | None:
    """Destenin kartlari.

    `due` tekrar kuyrugu (once vadesi gelenler, sonra yeniler) verir;
    `only_lapses` yalnizca en az bir kez "Yine" denmis kartlari suzer;
    `q` on/arka yuzde basit metin arar.
    """
    if await session.get(FlashcardDeck, deck_id) is None:
        return None
    base = select(FlashcardCard).where(FlashcardCard.deck_id == deck_id)
    if only_lapses:
        base = base.where(FlashcardCard.lapses >= 1)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        base = base.where(
            or_(FlashcardCard.front.ilike(pattern), FlashcardCard.back.ilike(pattern))
        )
    if due:
        # Tekrar sirasi: due kartlar once, sonra yeni kartlar; her biri 40 kart.
        due_cards = list(
            (
                await session.execute(
                    base.where(
                        FlashcardCard.due_at <= datetime.now(UTC),
                        FlashcardCard.suspended.is_(False),
                    )
                    .order_by(FlashcardCard.due_at.asc())
                    .limit(REVIEW_LIMIT)
                )
            ).scalars()
        )
        new_cards = list(
            (
                await session.execute(
                    base.where(
                        FlashcardCard.due_at.is_(None), FlashcardCard.suspended.is_(False)
                    )
                    .join(Entity, Entity.id == FlashcardCard.id)
                    .order_by(Entity.created_at.asc())
                    .limit(REVIEW_LIMIT)
                )
            ).scalars()
        )
        cards = due_cards + new_cards
    else:
        cards = list(
            (
                await session.execute(
                    base.join(Entity, Entity.id == FlashcardCard.id)
                    .order_by(Entity.created_at.asc())
                )
            ).scalars()
        )
    return [card_out(card) for card in cards]


async def create_card(session: AsyncSession, deck_id, data) -> dict | None:
    """Kart ekler; `reversible` ise tersi de (Arka -> On) ayni desteye girer."""
    if await session.get(FlashcardDeck, deck_id) is None:
        return None
    card = await _add_card(session, deck_id, data.front, data.back, reversible=False)
    if data.reversible and data.back.strip() != data.front.strip():
        await _add_card(session, deck_id, data.back, data.front, reversible=True)
    await session.commit()
    return card_out(card)


async def _add_card(
    session: AsyncSession, deck_id, front: str, back: str, *, reversible: bool
) -> FlashcardCard:
    entity = await create_entity(
        session, type=FlashcardCard.ENTITY_TYPE, title=front, search_text=back
    )
    card = FlashcardCard(id=entity.id, deck_id=deck_id, front=front, back=back)
    session.add(card)
    await log_event(
        session, verb="flashcard.card_added", entity_id=card.id,
        entity_type=FlashcardCard.ENTITY_TYPE,
        payload={"deck_id": str(deck_id), "reversible": reversible},
    )
    return card


async def missed_cards(session: AsyncSession, limit: int = MISSED_LIMIT) -> list[dict]:
    """Desteler genelinde en cok unutulan kartlar: "zayif noktalar" kuyrugu.

    Esitlikte daha yakin vadeli kart once gelir (tekrar faydasi yuksek olan).
    """
    rows = (
        await session.execute(
            select(FlashcardCard, Entity.title)
            .join(Entity, Entity.id == FlashcardCard.id)
            .where(
                FlashcardCard.lapses >= 1,
                FlashcardCard.suspended.is_(False),
            )
            .order_by(
                FlashcardCard.lapses.desc(),
                FlashcardCard.due_at.asc().nullsfirst(),
            )
            .limit(limit)
        )
    ).all()
    if not rows:
        return []
    deck_ids = {card.deck_id for card, _ in rows}
    titles = dict(
        (
            await session.execute(
                select(FlashcardDeck.id, Entity.title)
                .join(Entity, Entity.id == FlashcardDeck.id)
                .where(FlashcardDeck.id.in_(deck_ids))
            )
        ).all()
    )
    return [
        {**card_out(card), "deck_title": titles.get(card.deck_id, "Deste")}
        for card, _ in rows
    ]


async def patch_card(session: AsyncSession, card_id, data) -> dict | None:
    card = await session.get(FlashcardCard, card_id)
    if card is None:
        return None
    if data.front is not None:
        card.front = data.front
    if data.back is not None:
        card.back = data.back
    if data.suspended is not None:
        card.suspended = data.suspended
    if data.front is not None or data.back is not None:
        await touch_entity(session, card.id, title=card.front, search_text=card.back)
    await session.commit()
    return card_out(card)


async def delete_card(session: AsyncSession, card_id) -> bool:
    card = await session.get(FlashcardCard, card_id)
    if card is None:
        return False
    await delete_entity(session, card.id)
    await session.commit()
    return True


async def review_card(session: AsyncSession, card_id, grade: int) -> dict | None:
    card = await session.get(FlashcardCard, card_id)
    if card is None:
        return None
    interval, ease, due_at = sm2_next(
        card.interval_days, card.ease, grade, is_new=card.due_at is None
    )
    card.interval_days = interval
    card.ease = ease
    card.due_at = due_at
    card.reps += 1
    if grade == 0:
        card.lapses += 1
    await log_event(
        session, verb="flashcard.reviewed", entity_id=card.id,
        entity_type=FlashcardCard.ENTITY_TYPE,
        payload={"grade": grade, "interval_days": interval, "deck_id": str(card.deck_id)},
    )
    await session.commit()
    return {"due_at": due_at, "interval_days": interval}


# ---------------------------------------------------------------------------
# Ic aktarim: .apkg (zip + SQLite) ve .csv/.txt (metin satirlari)
# ---------------------------------------------------------------------------


def _parse_apkg(content: bytes) -> tuple[str | None, list[tuple[str, str]], int]:
    """Anki paketinden kartlari cikarir; media dosyalari atlanir (metin yeterli).

    'Basic' tip varsayilir: her notun flds JSON'unun ilk iki alani front/back.
    Donen: (koleksiyon destek adi, [(front, back)], atlanan satir sayisi).
    """
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if "collection.anki2" not in archive.namelist():
                raise ValueError("collection.anki2 bulunamadi (gecerli bir .apkg degil)")
            raw = archive.read("collection.anki2")
    except zipfile.BadZipFile as exc:
        raise ValueError("Gecersiz .apkg dosyasi") from exc

    fd, path = tempfile.mkstemp(suffix=".anki2")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            deck_names = dict(connection.execute("select id, name from decks").fetchall())
            notes = dict(connection.execute("select id, flds from notes").fetchall())
            rows = connection.execute("select nid, did from cards").fetchall()
        finally:
            connection.close()
    finally:
        os.unlink(path)

    deck_name: str | None = None
    cards: list[tuple[str, str]] = []
    seen: set[int] = set()
    skipped = 0
    for nid, did in rows:
        if nid in seen:
            continue
        seen.add(nid)
        if deck_name is None and did in deck_names:
            deck_name = deck_names[did]
        try:
            fields = json.loads(notes.get(nid) or "")
        except (ValueError, TypeError):
            skipped += 1
            continue
        if not isinstance(fields, list) or len(fields) < 2:
            skipped += 1
            continue
        front = str(fields[0]).strip()
        back = str(fields[1]).strip()
        if not front or not back:
            skipped += 1
            continue
        cards.append((front, back))
    return deck_name, cards, skipped


def _is_header(fields: list[str]) -> bool:
    lowered = [field.strip().casefold() for field in fields]
    has_front = any("front" in cell for cell in lowered)
    has_back = any("back" in cell for cell in lowered)
    return has_front and has_back


def _split_line(line: str) -> list[str]:
    if "\t" in line:
        return line.split("\t")
    return next(csv.reader([line]))


def _parse_text(content: bytes) -> tuple[list[tuple[str, str]], int]:
    """CSV (virgul) ya da tab-ayracli satirlar. Ilk satir basliksa atlanir."""
    text = content.decode("utf-8-sig", errors="replace")
    cards: list[tuple[str, str]] = []
    skipped = 0
    first = True
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        fields = _split_line(line)
        if first:
            first = False
            if _is_header(fields):
                continue
        if len(fields) < 2:
            skipped += 1
            continue
        front = fields[0].strip()
        back = fields[1].strip()
        if not front or not back:
            skipped += 1
            continue
        cards.append((front, back))
    return cards, skipped


async def _find_or_create_deck(session: AsyncSession, title: str) -> FlashcardDeck:
    """Ayni isimde destek varsa onu kullanir (ad eslesmesi), yoksa kurar."""
    existing = (
        await session.execute(
            select(FlashcardDeck)
            .join(Entity, Entity.id == FlashcardDeck.id)
            .where(Entity.title == title)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    entity = await create_entity(
        session, type=FlashcardDeck.ENTITY_TYPE, title=title, search_text=title
    )
    deck = FlashcardDeck(id=entity.id)
    session.add(deck)
    await session.flush()
    return deck


async def import_cards(
    session: AsyncSession, content: bytes, filename: str, deck_name: str | None
) -> dict:
    """Ic aktarim. `deck_name` verilirse hedef destek adi olur (ve kazandigi icin
    apkg icindeki destek adini ezer); verilmezse apkg destek adi / varsayilan ad
    kullanilir. Ayni isimli destek varsa YENISI KURULMAZ, mevcuda eklenir."""
    filename = (filename or "").lower()
    if filename.endswith(".apkg"):
        collection_deck, cards, skipped = _parse_apkg(content)
        deck_name = (deck_name or collection_deck or DEFAULT_IMPORT_DECK).strip()
    else:
        cards, skipped = _parse_text(content)
        deck_name = (deck_name or DEFAULT_IMPORT_DECK).strip()

    deck = await _find_or_create_deck(session, deck_name)
    for front, back in cards:
        entity = await create_entity(
            session, type=FlashcardCard.ENTITY_TYPE, title=front, search_text=back
        )
        session.add(FlashcardCard(id=entity.id, deck_id=deck.id, front=front, back=back))
    await log_event(
        session, verb="flashcard.imported", entity_id=deck.id,
        entity_type=FlashcardDeck.ENTITY_TYPE,
        payload={"deck_id": str(deck.id), "added": len(cards), "skipped": skipped},
    )
    await session.commit()
    return {"deck_id": deck.id, "deck_title": deck_name, "added": len(cards), "skipped": skipped}
