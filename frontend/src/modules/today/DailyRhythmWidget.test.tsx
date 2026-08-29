// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DailyRhythmWidget } from "./DailyRhythmWidget";

type QueryOptions = { queryKey: readonly unknown[]; queryFn: () => unknown };

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  invalidate: vi.fn(),
  queries: [] as QueryOptions[],
  mutations: [] as { mutationFn?: (variables: never) => unknown; onSuccess?: () => void }[],
  reviewEvents: [] as { occurred_at: string; verb: string }[],
}));

vi.mock("@/core/api", () => ({
  api: { get: harness.apiGet, patch: harness.apiPatch, post: vi.fn(), del: vi.fn(), put: vi.fn() },
  qs: vi.fn(() => ""),
}));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/app/router", () => ({ navigate: vi.fn() }));
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn((options: { mutationFn?: (variables: never) => unknown; onSuccess?: () => void }) => {
    harness.mutations.push(options);
    return { isPending: false, mutate: (variables: never) => void options.mutationFn?.(variables) };
  }),
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
              : [];
    return { data };
  }),
}));

describe("DailyRhythmWidget (Faz 25)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    harness.apiGet.mockReset();
    harness.apiPatch.mockReset();
    harness.invalidate.mockReset();
    harness.queries.length = 0;
    harness.mutations.length = 0;
    harness.reviewEvents = [];
  });
  afterEach(() => vi.useRealTimers());

  it("sabah: gelen kutusu + ilk 3 planli + ilk odak aksiyonu", () => {
    vi.setSystemTime(new Date("2026-08-29T06:00:00Z")); // Istanbul 09:00
    const markup = renderToStaticMarkup(<DailyRhythmWidget />);
    expect(markup).toContain("Günün ritmi");
    expect(markup).toContain("Sabah");
    expect(markup).toContain("Gelen kutusunda");
    expect(markup).toContain("Rapor");
    expect(markup).toContain("İlk odağı başlat");
  });

  it("gun icinde: aktif pomodoro 'Odak devam ediyor' gosterir", () => {
    vi.setSystemTime(new Date("2026-08-29T12:00:00Z")); // Istanbul 15:00
    const markup = renderToStaticMarkup(<DailyRhythmWidget />);
    expect(markup).toContain("Gün içinde");
    expect(markup).toContain("Odak devam ediyor — aç");
    expect(markup).toContain("Sıradaki");
  });

  it("aksam: degerlendirme durumu + yarina tasi butonu PATCH /plan/{id} yapar", async () => {
    vi.setSystemTime(new Date("2026-08-29T17:30:00Z")); // Istanbul 20:30
    const markup = renderToStaticMarkup(<DailyRhythmWidget />);
    expect(markup).toContain("Akşam");
    expect(markup).toContain("Gün sonu değerlendirmesi bekliyor");
    expect(markup).toContain("Yarına taşı");

    const carry = harness.mutations[0];
    await carry?.mutationFn?.(undefined as never);
    // Iki planli gorev yarina (2026-08-30) tasinir.
    expect(harness.apiPatch).toHaveBeenCalledWith("/plan/s1", { day: "2026-08-30" });
    expect(harness.apiPatch).toHaveBeenCalledWith("/plan/s2", { day: "2026-08-30" });
    carry?.onSuccess?.();
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
