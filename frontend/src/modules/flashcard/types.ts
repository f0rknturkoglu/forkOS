/** Modul ici API tipleri (backend /flashcard uclari). */

export interface FlashcardDeck {
  id: string;
  title: string;
  card_count: number;
  due_count: number;
  new_count: number;
  created_at: string;
}

export interface FlashcardCard {
  id: string;
  deck_id: string;
  front: string;
  back: string;
  interval_days: number;
  ease: number;
  due_at: string | null;
  reps: number;
  lapses: number;
  suspended: boolean;
}

export interface ReviewResult {
  due_at: string;
  interval_days: number;
}

export interface ImportResult {
  deck_id: string;
  deck_title: string;
  added: number;
  skipped: number;
}
