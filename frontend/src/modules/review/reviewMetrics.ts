import type { ReviewPreview } from "@/core/types";

export function reviewMetricRows(stats: ReviewPreview["stats"]): [string, string | number][] {
  return [
    ["Tamamlanan", stats.todos.completed],
    ["Odak", `${stats.focus.minutes} dk`],
    ["Odak", stats.focus.sessions],
    ["Aktif gün", stats.focus.active_days],
    // Kart tekrari da donemin emegidir; degerlendirmede gorunur.
    ["Kart tekrarı", stats.flashcards.reviewed],
  ];
}
