from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.flashcard import service
from app.modules.flashcard.schemas import (
    CardIn,
    CardOut,
    CardPatch,
    CramCardOut,
    DeckIn,
    DeckOut,
    DeckPatch,
    ImportOut,
    ReviewIn,
    ReviewOut,
)

router = APIRouter(tags=["flashcard"])


@router.get("/flashcard/decks", response_model=list[DeckOut])
async def decks(
    linked_to: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Desteler. `linked_to` verilirse yalnizca o kayda bagli olanlar doner
    (not/dokuman -> deste bagi "studies"/"generated_from")."""
    return await service.list_decks(session, linked_to=linked_to)


@router.post("/flashcard/decks", response_model=DeckOut, status_code=201)
async def add_deck(body: DeckIn, session: AsyncSession = Depends(get_session)):
    return await service.create_deck(session, body)


@router.patch("/flashcard/decks/{deck_id}", response_model=DeckOut)
async def patch_deck(
    deck_id: uuid.UUID, body: DeckPatch, session: AsyncSession = Depends(get_session)
):
    result = await service.patch_deck(session, deck_id, body)
    if result is None:
        raise HTTPException(404, "destek bulunamadi")
    return result


@router.delete("/flashcard/decks/{deck_id}", status_code=204)
async def delete_deck(deck_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_deck(session, deck_id):
        raise HTTPException(404, "destek bulunamadi")


@router.get("/flashcard/decks/{deck_id}/cards", response_model=list[CardOut])
async def cards(
    deck_id: uuid.UUID,
    due: bool = False,
    only_lapses: bool = Query(default=False, description="Yalnizca en az bir kez unutulanlar"),
    q: str | None = Query(default=None, max_length=200),
    session: AsyncSession = Depends(get_session),
):
    """?due=1: tekrar sirasi (once vadesi gelen, sonra yeni; her biri 40 kart).

    `only_lapses=1` zayif noktalari suzer (lapses >= 1), `q` on/arka yuzde arar.
    """
    result = await service.list_cards(session, deck_id, due=due, only_lapses=only_lapses, q=q)
    if result is None:
        raise HTTPException(404, "destek bulunamadi")
    return result


@router.post("/flashcard/decks/{deck_id}/cards", response_model=CardOut, status_code=201)
async def add_card(
    deck_id: uuid.UUID, body: CardIn, session: AsyncSession = Depends(get_session)
):
    result = await service.create_card(session, deck_id, body)
    if result is None:
        raise HTTPException(404, "destek bulunamadi")
    return result


@router.patch("/flashcard/cards/{card_id}", response_model=CardOut)
async def patch_card(
    card_id: uuid.UUID, body: CardPatch, session: AsyncSession = Depends(get_session)
):
    result = await service.patch_card(session, card_id, body)
    if result is None:
        raise HTTPException(404, "kart bulunamadi")
    return result


@router.delete("/flashcard/cards/{card_id}", status_code=204)
async def delete_card(card_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_card(session, card_id):
        raise HTTPException(404, "kart bulunamadi")


@router.post("/flashcard/cards/{card_id}/review", response_model=ReviewOut)
async def review(
    card_id: uuid.UUID, body: ReviewIn, session: AsyncSession = Depends(get_session)
):
    result = await service.review_card(session, card_id, body.grade)
    if result is None:
        raise HTTPException(404, "kart bulunamadi")
    return result


@router.get("/flashcard/cram/missed", response_model=list[CramCardOut])
async def cram_missed(
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Desteler genelinde en cok unutulan kartlar (varsayilan 30) -- cram kuyrugu."""
    return await service.missed_cards(session, limit=limit)


@router.post("/flashcard/import", response_model=ImportOut, status_code=201)
async def import_cards(
    file: UploadFile = File(...),
    deck: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Anki .apkg / .csv / .txt ic aktarim. `deck` = hedef destek adi (opsiyonel)."""
    content = await file.read()
    try:
        return await service.import_cards(session, content, file.filename or "", deck)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
