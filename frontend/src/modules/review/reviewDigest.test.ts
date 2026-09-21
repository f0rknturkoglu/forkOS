import { describe, expect, it } from "vitest";
import type { ReviewPreview } from "@/core/types";
import { buildReviewDigest } from "./reviewDigest";

const preview: ReviewPreview = {
  kind: "weekly",
  period_start: "2026-08-24",
  period_end: "2026-08-30",
  completed_todos: [{ id: "t1", title: "Kapanış raporu", completed_at: "2026-08-25T09:30:00Z" }],
  unfinished_todos: [{ id: "u1", title: "Vergi beyanı", priority: 3, due_at: "2026-09-01T17:00:00Z" }],
  stats: {
    todos: { completed: 1, created: 2, dropped: 0, overdue_now: 0 },
    focus: {
      minutes: 45,
      sessions: 1,
      interrupted: 0,
      active_days: 3,
      best_day: "2026-08-25",
      best_day_minutes: 45,
      longest_session: 45,
    },
    topics: [{ topic: "forkOS", minutes: 45 }],
    habits: {},
    capture: { bookmarks: 0, rss_read: 0, notes: 2 },
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
    flashcards: { reviewed: 12, decks: { Almanca: 12 } },
    github: { commits: 0, repos: {} },
  },
};

describe("ajan için değerlendirme özeti", () => {
  it("dönem, listede kalan işler, odak ve notu tek pakette taşır", () => {
    const digest = buildReviewDigest(preview, "Bu hafta kapanışa odaklandım.");

    expect(digest).toContain("## Dönem\n2026-08-24 → 2026-08-30");
    expect(digest).toContain("## Tamamlanan (1)\n- Kapanış raporu · 2026-08-25T09:30:00Z");
    expect(digest).toContain("## Açık (1)\n- Vergi beyanı · son tarih 2026-09-01");
    expect(digest).toContain("- 45 dk · 1 seans · 3 aktif gün");
    expect(digest).toContain("## Mevcut değerlendirme notu\nBu hafta kapanışa odaklandım.");
  });

  it("gerçekleşmemiş sinyalleri yazmaz, notsuz kayıtta bunu açıkça söyler", () => {
    const digest = buildReviewDigest(preview, "   ");

    expect(digest).toContain("- Kart tekrarı: 12");
    expect(digest).toContain("- Yeni not: 2");
    // GitHub commit 0 ve rutin tamamlama 0: pakette yer kaplamaz.
    expect(digest).not.toContain("GitHub commit");
    expect(digest).not.toContain("Rutin tamamlama");
    expect(digest.endsWith("## Mevcut değerlendirme notu\nNot yok.")).toBe(true);
  });
});
