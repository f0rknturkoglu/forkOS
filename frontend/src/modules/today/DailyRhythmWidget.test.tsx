// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DailyRhythmWidget } from "./DailyRhythmWidget";

type QueryOptions = { queryKey: readonly unknown[]; queryFn: () => unknown };

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  queries: [] as QueryOptions[],
  mutations: [] as { mutationFn?: (variables: never) => unknown; onSuccess?: (result?: unknown) => void }[],
  reviewEvents: [] as { occurred_at: string; verb: string }[],
  weeklyReviews: [] as { kind: string; period_start: string }[],
  agenda: null as null | Record<string, unknown>,
  navigate: vi.fn(),
}));

vi.mock("@/core/api", () => ({
  api: { get: harness.apiGet, patch: harness.apiPatch, post: harness.apiPost, del: vi.fn(), put: vi.fn() },
  qs: vi.fn(() => ""),
}));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/app/router", () => ({ navigate: (...args: unknown[]) => harness.navigate(...args) }));
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn(
    (options: { mutationFn?: (variables: never) => unknown; onSuccess?: (result?: unknown) => void }) => {
      harness.mutations.push(options);
      return { isPending: false, mutate: (variables: never) => void options.mutationFn?.(variables) };
    },
  ),
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    const key = String(options.queryKey[0]);
    const data =
      key === "bookmark-stats"
        ? { inbox: 3, unread: 1, saved_today: 0, total: 3, collections: [] }
        : key === "plan"
          ? [
              {
                id: "s1",
                entity_id: "t1",
                entity_type: "todo",
                title: "Rapor",
                day: "2026-08-29",
                start_min: 9 * 60,
                duration_min: 30,
                note: null,
                position: 0,
              },
              {
                id: "s2",
                entity_id: "t2",
                entity_type: "todo",
                title: "E-posta",
                day: "2026-08-29",
                start_min: 11 * 60,
                duration_min: 30,
                note: null,
                position: 0,
              },
            ]
          : key === "pomodoro-active"
            ? {
                id: "p1",
                started_at: "2026-08-29T10:00:00Z",
                ended_at: null,
                planned_min: 50,
                actual_min: null,
                kind: "focus",
              }
            : key === "activity"
              ? harness.reviewEvents
              : key === "today-agenda"
                ? (harness.agenda ?? {
                    day: "2026-08-29",
                    timed: [],
                    checklist: [],
                    completed: [],
                    suggestions: { todos: [], rss: [], media: [] },
                  })
                : key === "reviews"
                  ? harness.weeklyReviews
                  : key === "todos"
                    ? [
                        { id: "t1", title: "Rapor", status: "open", due_at: null },
                        { id: "t2", title: "E-posta", status: "doing", due_at: null },
                      ]
                    : [];
    return { data };
  }),
}));

describe("DailyRhythmWidget (Faz 25)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    harness.apiGet.mockReset();
    harness.apiPatch.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.queries.length = 0;
    harness.mutations.length = 0;
    harness.reviewEvents = [];
    harness.weeklyReviews = [];
    harness.agenda = null;
    harness.navigate.mockReset();
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("sabah: yalnız günün özetini verir, görev listesini tekrarlamaz", () => {
    vi.setSystemTime(new Date("2026-08-29T06:00:00Z")); // Istanbul 09:00
    const markup = renderToStaticMarkup(<DailyRhythmWidget />);
    expect(markup).toContain("Gün özeti");
    expect(markup).toContain("Sabah");
    expect(markup).toContain("2</strong> planlı");
    expect(markup).not.toContain("Rapor");
    expect(markup).not.toContain("İlk odağı başlat");
  });

  it("gün içinde: durum sayıları dışında görev içeriğini tekrar etmez", () => {
    vi.setSystemTime(new Date("2026-08-29T12:00:00Z")); // Istanbul 15:00
    const markup = renderToStaticMarkup(<DailyRhythmWidget />);
    expect(markup).toContain("Gün içinde");
    expect(markup).not.toContain("Odak devam ediyor — aç");
    expect(markup).not.toContain("Sıradaki");
    expect(markup).not.toContain("Rapor");
  });

  it("Pazar/Pazartesi tamamlanmamis haftalik degerlendirmeyi hatirlatir", () => {
    vi.setSystemTime(new Date("2026-08-30T08:00:00Z")); // Pazar, Istanbul 11:00
    const markup = renderToStaticMarkup(<DailyRhythmWidget />);
    expect(markup).toContain("Haftalık değerlendirme bekliyor");
  });

  it("planli gorevle takvim etkinligi cakisirsa uyarir", () => {
    vi.setSystemTime(new Date("2026-08-29T06:00:00Z"));
    harness.agenda = {
      day: "2026-08-29",
      timed: [
        {
          id: "calendar-1",
          kind: "calendar",
          source: "calendar",
          title: "Toplantı",
          starts_at: "2026-08-29T06:15:00Z",
          duration_min: 30,
          completed: false,
          read_only: true,
          context_only: false,
          children: [],
        },
      ],
      checklist: [],
      completed: [],
      suggestions: { todos: [], rss: [], media: [] },
    };
    const markup = renderToStaticMarkup(<DailyRhythmWidget />);
    expect(markup).toContain("1 takvim çakışması");
  });

  it("agenda ve haftalik review endpointlerini app gunuyle sorgular", async () => {
    vi.setSystemTime(new Date("2026-08-29T06:00:00Z"));
    renderToStaticMarkup(<DailyRhythmWidget />);
    await harness.queries.find((query) => query.queryKey[0] === "today-agenda")?.queryFn();
    await harness.queries.find((query) => query.queryKey[0] === "reviews")?.queryFn();
    expect(harness.apiGet).toHaveBeenCalledWith("/today/agenda?day=2026-08-29");
    expect(harness.apiGet).toHaveBeenCalledWith("/reviews?kind=weekly&limit=5");
  });

  it("aksam: degerlendirme durumu + yarina tasi butonu tek istek yapar", async () => {
    vi.setSystemTime(new Date("2026-08-29T17:30:00Z")); // Istanbul 20:30
    const markup = renderToStaticMarkup(<DailyRhythmWidget />);
    expect(markup).toContain("Akşam");
    expect(markup).toContain("Gün sonu değerlendirmesi bekliyor");
    expect(markup).toContain("Yarına taşı");

    const carry = harness.mutations[0];
    harness.apiPost.mockResolvedValueOnce({ moved: 2 });
    await carry?.mutationFn?.(undefined as never);
    // Tek istek, tek transaction (Faz 33): dagilmis PATCH yok.
    expect(harness.apiPost).toHaveBeenCalledWith("/plan/carry-over", {
      day: "2026-08-29",
      target: "2026-08-30",
    });
    expect(harness.apiPatch).not.toHaveBeenCalled();
    carry?.onSuccess?.({ moved: 2 });
    expect(harness.invalidate).toHaveBeenCalledWith("plan.write");
  });

  it("degerlendirme bugun yapildiysa 'Gunu degerlendirdin' gosterir, cagri tekrarlanmaz", () => {
    vi.setSystemTime(new Date("2026-08-29T17:30:00Z")); // Istanbul 20:30
    // Istanbul 20:15'te (dun 17:15Z) tamamlanan review -> bugunun event'i.
    harness.reviewEvents = [{ occurred_at: "2026-08-29T17:15:00Z", verb: "review.completed" }];
    const markup = renderToStaticMarkup(<DailyRhythmWidget />);
    expect(markup).toContain("Günü değerlendirdin");
    expect(markup).not.toContain("Değerlendirmeye git");
  });
});
