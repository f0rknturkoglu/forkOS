import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ReviewWidget } from "./ReviewWidget";

type QueryOptions = { queryKey: readonly unknown[]; queryFn: () => unknown };

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  events: [] as { occurred_at: string; verb: string }[],
  queries: [] as QueryOptions[],
}));

vi.mock("@/core/api", () => ({ api: { get: harness.apiGet } }));
vi.mock("@/app/router", () => ({ navigate: vi.fn() }));
vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    const key = String(options.queryKey[0]);
    return { data: key.includes("activity") ? harness.events : [] };
  }),
}));

describe("ReviewWidget app gunu kontrolu (Faz 14)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    harness.apiGet.mockReset();
    harness.events = [];
    harness.queries.length = 0;
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("event app gununde tamamlandiysa 'Bugunu degerlendirdin' gosterir", () => {
    // Istanbul 2026-01-15 00:30 -- tarayici/UTC gunu hala 2026-01-14.
    vi.setSystemTime(new Date("2026-01-14T21:40:00Z"));
    harness.events = [{ occurred_at: "2026-01-14T21:30:00Z", verb: "review.completed" }];

    const markup = renderToStaticMarkup(<ReviewWidget />);

    expect(markup).toContain("Bugünü değerlendirdin.");
  });

  it("event onceki app gununde tamamlandiysa hatirlatma hala gorunur", () => {
    // Istanbul 2026-01-15 00:40; event dune (Istanbul 2026-01-14 23:50).
    vi.setSystemTime(new Date("2026-01-14T21:50:00Z"));
    harness.events = [{ occurred_at: "2026-01-14T20:50:00Z", verb: "review.completed" }];

    const markup = renderToStaticMarkup(<ReviewWidget />);

    expect(markup).not.toContain("Bugünü değerlendirdin.");
    // Istanbul 00:50 -> aksam dilimi: gunu kapatma cagrisi gorunur.
    expect(markup).toContain("Günü kapat — bugünü değerlendir");
  });
});
