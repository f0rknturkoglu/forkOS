import { describe, expect, it } from "vitest";
import type { ReviewPreview } from "@/core/types";
import { reviewChangeRows, reviewMetricRows } from "./reviewMetrics";

const stats = {
  todos: { completed: 4, created: 6, dropped: 1, overdue_now: 1 },
  focus: {
    minutes: 50,
    sessions: 2,
    interrupted: 1,
    active_days: 2,
    best_day: "2026-08-24",
    best_day_minutes: 30,
    longest_session: 30,
  },
  topics: [{ topic: "forkOS", minutes: 50 }],
  habits: { "Su iç": 2, "Eski yürüyüş": 1 },
  capture: { bookmarks: 3, rss_read: 1, notes: 1 },
  applications: {
    discovered: 0,
    shortlisted: 0,
    prepared: 0,
    applied: 0,
    interview: 0,
    offer: 0,
    rejected: 0,
    upcoming_deadlines: 0,
    career_prep: 0,
  },
  study: { minutes_by_area: {} },
  flashcards: { reviewed: 120, decks: { Almanca: 120 } },
  github: { commits: 2, repos: { forkOS: 2 } },
} satisfies ReviewPreview["stats"];

const preview: ReviewPreview = {
  kind: "weekly",
  period_start: "2026-08-24",
  period_end: "2026-08-30",
  stats,
  completed_todos: [],
  unfinished_todos: [
    { id: "u1", title: "Açık görev 1", priority: 2, due_at: null },
    { id: "u2", title: "Açık görev 2", priority: 3, due_at: null },
  ],
};

describe("dönem özeti", () => {
  it("en fazla dört üst düzey sinyal gösterir ve açık yükü görevlere bağlar", () => {
    expect(reviewMetricRows(preview)).toEqual([
      { label: "Tamamlanan iş", value: 4 },
      { label: "Odak süresi", value: "50 dk", hint: "2 seans" },
      { label: "Aktif gün", value: 2 },
      { label: "Devreden açık görev", value: 2, href: "#/todos" },
    ]);
  });
});

describe("önceki döneme göre değişim", () => {
  it("ölçülmemiş alanı sıfır saymaz, satırı atlar", () => {
    // Eski kayıtta `focus.active_days` ve `flashcards.reviewed` yok: bunlar
    // karşılaştırmaya girmez, uydurulmuş bir "-120" gösterilmez.
    expect(reviewChangeRows(stats, { todos: { completed: 3 }, focus: { minutes: 50 } })).toEqual([
      ["Tamamlanan iş", "+1"],
      ["Odak süresi", "değişmedi"],
    ]);
  });

  it("değişimi birimle ve işaretle yazar", () => {
    const previous = { todos: { completed: 9 }, focus: { minutes: 20, active_days: 2 }, flashcards: { reviewed: 120 } };
    expect(reviewChangeRows(stats, previous)).toEqual([
      ["Tamamlanan iş", "-5"],
      ["Odak süresi", "+30 dk"],
      ["Aktif gün", "değişmedi"],
      ["Kart tekrarı", "değişmedi"],
    ]);
  });
});
