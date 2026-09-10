import { api, qs } from "@/core/api";
import type { FlashcardCard, FlashcardDeck, ImportResult, ReviewResult } from "./types";

export const listDecks = (linkedTo?: string) =>
  api.get<FlashcardDeck[]>(`/flashcard/decks${linkedTo ? qs({ linked_to: linkedTo }) : ""}`);
export const createDeck = (title: string) => api.post<FlashcardDeck>("/flashcard/decks", { title });
export const renameDeck = (id: string, title: string) => api.patch<FlashcardDeck>(`/flashcard/decks/${id}`, { title });
export const deleteDeck = (id: string) => api.del(`/flashcard/decks/${id}`);

/** `due`: tekrar sirasi (once vadesi gelen, sonra yeni; her biri 40 kart). */
export const listCards = (deckId: string, options: { due?: boolean; onlyLapses?: boolean; q?: string } = {}) =>
  api.get<FlashcardCard[]>(
    `/flashcard/decks/${deckId}/cards${qs({
      due: options.due ? 1 : undefined,
      only_lapses: options.onlyLapses ? 1 : undefined,
      q: options.q || undefined,
    })}`,
  );

export const addCard = (deckId: string, front: string, back: string, reversible = false) =>
  api.post<FlashcardCard>(`/flashcard/decks/${deckId}/cards`, { front, back, reversible });

/** Desteler genelinde en cok unutulan kartlar (cram kuyrugu). */
export const missedCards = (limit = 30) => api.get<FlashcardCard[]>(`/flashcard/cram/missed${qs({ limit })}`);

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
