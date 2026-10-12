"""Anki benzeri flashcard servisi: SM-2 zamanlama + .apkg/.csv ic aktarim.

Zamanlama (grade: 0=Again, 1=Hard, 2=Good, 3=Easy):

* Yeni kart (due_at NULL): again -> 10 dk, hard/good -> 1 gun, easy -> 4 gun.
* Bilinen kart: interval again x0.5 (min 1), hard x1.2, good x ease,
  easy x ease x 1.3. Ease ayari: again -0.20, hard -0.15, good 0, easy +0.15
  (min 1.3). due_at = bugun (yerel gun basi) + interval.
"""
from __future__ import annotations

import contextlib
import csv
import html
import io
import json
import os
import re
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
                func.count().filter(FlashcardCard.due_at.is_(None), FlashcardCard.suspended.is_(False)).label("new_count"),
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
                    func.count().filter(FlashcardCard.due_at.is_(None), FlashcardCard.suspended.is_(False)),
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


async def create_card(session: AsyncSession, deck_id, data, *, commit: bool = True) -> dict | None:
    """Kart ekler; `reversible` ise tersi de (Arka -> On) ayni desteye girer."""
    if await session.get(FlashcardDeck, deck_id) is None:
        return None
    card = await _add_card(session, deck_id, data.front, data.back, reversible=False)
    if data.reversible and data.back.strip() != data.front.strip():
        await _add_card(session, deck_id, data.back, data.front, reversible=True)
    if commit:
        await session.commit()
    else:
        await session.flush()
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


def _clean_html(text: str) -> str:
    """Anki HTML bicimlendirmesini temizler, Markdown'a donusturur."""
    if not text:
        return ""
    # script ve style etiketlerini icerikleriyle temizle
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # <br> ve blok etiketlerini satir sonuna cevir
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(div|p|h[1-6]|li|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<hr[^>]*>", "\n---\n", text, flags=re.IGNORECASE)
    # Kalin ve italik etiketlerini Markdown'a cevir
    text = re.sub(r"<(b|strong)>(.*?)</\1>", r"**\2**", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<(i|em)>(.*?)</\1>", r"*\2*", text, flags=re.DOTALL | re.IGNORECASE)
    # Kalan tum HTML etiketlerini kaldir
    text = re.sub(r"<[^>]+>", "", text)
    # HTML entity'lerini coz (&nbsp;, &amp; vs.)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    # Fazla bosluk ve bos satirlari normallestir
    lines = [line.strip() for line in text.splitlines()]
    result: list[str] = []
    prev_empty = False
    for line in lines:
        if not line:
            if not prev_empty:
                result.append("")
                prev_empty = True
        else:
            result.append(line)
            prev_empty = False
    return "\n".join(result).strip()


def _render_anki_template(
    tmpl_str: str, field_dict: dict[str, str], is_back: bool = False, cloze_ord: int = 0
) -> str:
    """Anki soru (qfmt) ve cevap (afmt) sablonlarini doldurur."""
    if not tmpl_str:
        return ""
    s = tmpl_str
    if is_back:
        # Anki arka yuzunde {{FrontSide}} ve ayirici <hr id=answer> bulunur;
        # forkOS 3B cevrilen kart kullandigi icin arka yuzde on yuzu tekrarlamiyoruz.
        s = re.sub(r"\{\{FrontSide\}\}", "", s, flags=re.IGNORECASE)
        s = re.sub(r"<hr\s+id=[\'\"]?answer[\'\"]?\s*/?>", "", s, flags=re.IGNORECASE)

    # Kosullu alanlar: {{#Alan}}...{{/Alan}}
    def repl_pos(m: re.Match) -> str:
        f = m.group(1).strip()
        body = m.group(2)
        return body if field_dict.get(f, "").strip() else ""

    s = re.sub(r"\{\{#([^}]+)\}\}(.*?)\{\{/\1\}\}", repl_pos, s, flags=re.DOTALL)

    # Ters kosullu alanlar: {{^Alan}}...{{/Alan}}
    def repl_neg(m: re.Match) -> str:
        f = m.group(1).strip()
        body = m.group(2)
        return "" if field_dict.get(f, "").strip() else body

    s = re.sub(r"\{\{\^([^}]+)\}\}(.*?)\{\{/\1\}\}", repl_neg, s, flags=re.DOTALL)

    # Cloze etiketleri: {{cloze:Alan}}
    def repl_cloze(m: re.Match) -> str:
        f = m.group(1).strip()
        val = field_dict.get(f, "")
        target_c = cloze_ord + 1

        def cloze_sub(cm: re.Match) -> str:
            c_num = int(cm.group(1))
            c_text = cm.group(2)
            c_hint = cm.group(3)
            if not is_back:
                if c_num == target_c:
                    return f"[{c_hint}]" if c_hint else "[...]"
                return c_text
            return f"**{c_text}**" if c_num == target_c else c_text

        return re.sub(r"\{\{c(\d+)::(.*?)(?:::([^}]*))?\}\}", cloze_sub, val)

    s = re.sub(r"\{\{cloze:([^}]+)\}\}", repl_cloze, s, flags=re.IGNORECASE)

    # Standart ve filtreli alanlar: {{Alan}} veya {{filtre:Alan}}
    def repl_field(m: re.Match) -> str:
        inner = m.group(1).strip()
        if ":" in inner:
            inner = inner.split(":", 1)[1].strip()
        return field_dict.get(inner, "")

    s = re.sub(r"\{\{([^}]+)\}\}", repl_field, s)
    return _clean_html(s)


def _parse_apkg(content: bytes) -> tuple[str | None, list[tuple[str, str]], int]:
    """Anki paketinden (.apkg) kartlari cikarir; media dosyalari atlanir.

    Standart Anki 2.0/2.1 (col tablosundaki JSON decks ve models) ile
    testlerdeki duz decks/notes tablolarini destekler.
    Donen: (koleksiyon destek adi, [(front, back)], atlanan satir sayisi).
    """
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = archive.namelist()
            db_name = None
            for candidate in ("collection.anki2", "collection.anki21"):
                if candidate in names:
                    db_name = candidate
                    break
            if not db_name:
                raise ValueError("collection.anki2 bulunamadi (gecerli bir .apkg degil)")
            if archive.getinfo(db_name).file_size > 128_000_000:
                raise ValueError("Anki koleksiyonu 128 MB sınırını aşıyor")
            if "collection.anki21b" in names:
                raise ValueError("Bu paket yeni Anki biçiminde. Anki’den eski sürümlerle uyumlu .apkg olarak dışa aktar.")
            raw = archive.read(db_name)
    except zipfile.BadZipFile as exc:
        raise ValueError("Gecersiz .apkg dosyasi") from exc

    fd, path = tempfile.mkstemp(suffix=".anki2")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            deck_names: dict[int, str] = {}
            models: dict[str, dict] = {}

            # 1. Anki 2.0 / 2.1 standart col tablosu kontrolu
            has_col = (
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='col'"
                ).fetchone()
                is not None
            )
            if has_col:
                col_row = connection.execute("SELECT decks, models FROM col").fetchone()
                if col_row:
                    if col_row[0]:
                        with contextlib.suppress(Exception):
                            decks_data = json.loads(col_row[0])
                            for k, v in decks_data.items():
                                with contextlib.suppress(ValueError, TypeError):
                                    deck_names[int(k)] = v.get("name", "")
                    if col_row[1]:
                        with contextlib.suppress(Exception):
                            models = json.loads(col_row[1])

            # 2. Sentetik test / eski schema fallback (decks tablosu)
            if not deck_names:
                has_decks = (
                    connection.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='decks'"
                    ).fetchone()
                    is not None
                )
                if has_decks:
                    deck_names = dict(connection.execute("SELECT id, name FROM decks").fetchall())

            # 3. notes tablosu: mid var mi yok mu?
            notes_cols = [c[1] for c in connection.execute("PRAGMA table_info(notes)").fetchall()]
            if "mid" in notes_cols:
                notes_rows = connection.execute("SELECT id, mid, flds FROM notes").fetchall()
                notes = {r[0]: {"mid": str(r[1]), "flds": r[2]} for r in notes_rows}
            else:
                notes_rows = connection.execute("SELECT id, flds FROM notes").fetchall()
                notes = {r[0]: {"mid": None, "flds": r[1]} for r in notes_rows}

            # 4. cards tablosu: ord var mi yok mu?
            cards_cols = [c[1] for c in connection.execute("PRAGMA table_info(cards)").fetchall()]
            if "ord" in cards_cols:
                card_rows = connection.execute(
                    "SELECT id, nid, did, ord FROM cards ORDER BY id"
                ).fetchall()
            else:
                card_rows = [
                    (r[0], r[1], r[2], 0)
                    for r in connection.execute("SELECT id, nid, did FROM cards ORDER BY id").fetchall()
                ]
        except sqlite3.Error as exc:
            raise ValueError(f"Gecersiz ya da okunamayan Anki veritabani: {exc}") from exc
        finally:
            connection.close()
    finally:
        os.unlink(path)

    deck_name: str | None = None
    cards: list[tuple[str, str]] = []
    seen_cards: set[tuple[str, str]] = set()
    skipped = 0

    for _cid, nid, did, cord in card_rows:
        ndata = notes.get(nid)
        if not ndata:
            skipped += 1
            continue

        if deck_name is None and did in deck_names:
            name_candidate = deck_names[did].strip()
            if name_candidate and (name_candidate.casefold() != "default" or len(deck_names) == 1):
                deck_name = name_candidate

        raw_flds = ndata.get("flds") or ""
        field_values: list[str] = []

        # JSON array kontrolu (sentetik test formati)
        if raw_flds.startswith("[") and raw_flds.endswith("]"):
            try:
                parsed = json.loads(raw_flds)
                if isinstance(parsed, list):
                    field_values = [str(x) for x in parsed]
            except Exception:
                pass

        if not field_values:
            field_values = raw_flds.split("\x1f")

        mid = ndata.get("mid")
        minfo = models.get(mid) if mid else None
        front = ""
        back = ""

        if minfo:
            fnames = [f.get("name", "") for f in minfo.get("flds", [])]
            fdict = dict(zip(fnames, field_values, strict=False))
            tmpls = minfo.get("tmpls", [])
            tmpl = tmpls[cord] if cord < len(tmpls) else (tmpls[0] if tmpls else None)
            if tmpl:
                front = _render_anki_template(
                    tmpl.get("qfmt", ""), fdict, is_back=False, cloze_ord=cord
                )
                back = _render_anki_template(
                    tmpl.get("afmt", ""), fdict, is_back=True, cloze_ord=cord
                )

        if not front or not back:
            if minfo:
                fnames = [f.get("name", "") for f in minfo.get("flds", [])]
                fdict = dict(zip(fnames, field_values, strict=False))
            else:
                fdict = {}

            def pick_field(
                candidates: tuple[str, ...],
                default_idx: int,
                target_dict: dict[str, str] = fdict,
                target_vals: list[str] = field_values,
            ) -> str:
                for k, v in target_dict.items():
                    if k.casefold() in candidates and v.strip():
                        return v
                if len(target_vals) > default_idx:
                    return target_vals[default_idx]
                return ""

            if not front:
                front = _clean_html(
                    pick_field(("front", "question", "soru", "word", "term", "text"), 0)
                )
            if not back:
                back = _clean_html(
                    pick_field(("back", "answer", "cevap", "meaning", "definition", "translation"), 1)
                )

        if not front or not back:
            skipped += 1
            continue

        pair = (front, back)
        if pair in seen_cards:
            continue
        seen_cards.add(pair)
        cards.append(pair)

    if not deck_name and deck_names:
        for dname in deck_names.values():
            if dname.strip() and dname.strip().casefold() != "default":
                deck_name = dname.strip()
                break
        if not deck_name:
            deck_name = next(iter(deck_names.values()), None)

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
