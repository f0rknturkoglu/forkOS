import { api, qs } from "@/core/api";
import type { FlashcardCard, FlashcardDeck, ImportResult, ReviewResult } from "./types";

export const listDecks = () => api.get<FlashcardDeck[]>("/flashcard/decks");
export const createDeck = (title: string) => api.post<FlashcardDeck>("/flashcard/decks", { title });
export const renameDeck = (id: string, title: string) => api.patch<FlashcardDeck>(`/flashcard/decks/${id}`, { title });
export const deleteDeck = (id: string) => api.del(`/flashcard/decks/${id}`);

/** `due` true: tekrar sirasi (once vadesi gelen, sonra yeni; her biri 40 kart). */
export const listCards = (deckId: string, due = false) =>
  api.get<FlashcardCard[]>(`/flashcard/decks/${deckId}/cards${due ? "?due=1" : ""}`);

export const addCard = (deckId: string, front: string, back: string) =>
  api.post<FlashcardCard>(`/flashcard/decks/${deckId}/cards`, { front, back });

export const patchCard = (cardId: string, patch: { front?: string; back?: string; suspended?: boolean }) =>
  api.patch<FlashcardCard>(`/flashcard/cards/${cardId}`, patch);

export const deleteCard = (cardId: string) => api.del(`/flashcard/cards/${cardId}`);

export const reviewCard = (cardId: string, grade: number) =>
  api.post<ReviewResult>(`/flashcard/cards/${cardId}/review`, { grade });

/** .apkg/.csv ic aktarim; `deck` verilirse hedef destek adi. */
export const importDeck = (file: File, deck?: string) => {
  const path = deck ? `/flashcard/import${qs({ deck })}` : "/flashcard/import";
  return api.upload<ImportResult>(path, file);
};
