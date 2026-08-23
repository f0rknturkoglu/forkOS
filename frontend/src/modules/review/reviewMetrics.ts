import type { ReviewPreview } from "@/core/types";

export function reviewMetricRows(
  stats: ReviewPreview["stats"],
): [string, string | number][] {
  const routines = Object.values(stats.habits).reduce((total, count) => total + count, 0);
  return [
    ["Tamamlanan", stats.todos.completed],
    ["Odak", `${stats.focus.minutes} dk`],
    ["Rutin", routines],
    ["Yakalanan", stats.capture.bookmarks],
  ];
}
