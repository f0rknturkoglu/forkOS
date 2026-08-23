import { describe, expect, it } from "vitest";
import type { ReviewPreview } from "@/core/types";
import { reviewMetricRows } from "./reviewMetrics";

describe("review metrics", () => {
  it("presents recurring and legacy completions as routines", () => {
    const stats = {
      todos: { completed: 4, created: 1, dropped: 0, overdue_now: 0 },
      focus: { minutes: 50, sessions: 2, interrupted: 0 },
      topics: [],
      habits: { "Su iç": 2, "Eski yürüyüş": 1 },
      capture: { bookmarks: 3, rss_read: 1 },
    } satisfies ReviewPreview["stats"];

    expect(reviewMetricRows(stats)).toEqual([
      ["Tamamlanan", 4],
      ["Odak", "50 dk"],
      ["Rutin", 3],
      ["Yakalanan", 3],
    ]);
  });
});
