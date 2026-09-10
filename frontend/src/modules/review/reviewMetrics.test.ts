import { describe, expect, it } from "vitest";
import type { ReviewPreview } from "@/core/types";
import { reviewMetricRows } from "./reviewMetrics";

describe("review metrics", () => {
  it("presents the primary weekly outcome and focus metrics", () => {
    const stats = {
      todos: { completed: 4, created: 1, dropped: 0, overdue_now: 0 },
      focus: {
        minutes: 50,
        sessions: 2,
        interrupted: 0,
        active_days: 2,
        best_day: "2026-08-24",
        best_day_minutes: 30,
        longest_session: 25,
      },
      topics: [],
      habits: { "Su iç": 2, "Eski yürüyüş": 1 },
      capture: { bookmarks: 3, rss_read: 1, notes: 1 },
      applications: { discovered: 0, updated: 0 },
      study: { minutes_by_area: {} },
      flashcards: { reviewed: 120, decks: { Almanca: 120 } },
      github: { commits: 0, repos: {} },
    } satisfies ReviewPreview["stats"];

    expect(reviewMetricRows(stats)).toEqual([
      ["Tamamlanan", 4],
      ["Odak", "50 dk"],
      ["Pomodoro", 2],
      ["Aktif gün", 2],
      // Kart tekrari da donemin emegi: haftalik ozette gorunur.
      ["Kart tekrarı", 120],
    ]);
  });
});
