// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MediaStatsPage } from "./MediaStatsPage";

const dashboard = {
  continue_items: [],
  upcoming: [],
  recent_consumptions: [],
  stats: {
    total: 2,
    in_progress: 1,
    completed: 1,
    planned: 0,
    by_kind: { show: 1, book: 1 },
    total_duration_min: 90,
    scored_count: 1,
    average_score: 8,
  },
};

const recentRows = [
  {
    id: "consumption-1",
    media_id: "media-1",
    title: "Dune: Prophecy",
    kind: "show",
    action: "finish",
    measure: "episode",
    amount: 5,
    progress_after: 8,
    occurred_at: "2026-09-02T18:30:00Z",
    duration_min: 51,
  },
  {
    id: "consumption-2",
    media_id: "media-2",
    title: "Yabancı",
    kind: "book",
    action: "quick",
    measure: "page",
    amount: 30,
    progress_after: 90,
    occurred_at: "2026-09-01T09:15:00Z",
    duration_min: null,
  },
];

type FetchCall = { body: Record<string, unknown>; method: string; url: string };

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MediaStatsPage />
    </QueryClientProvider>,
  );
}

describe("media stats page recent consumptions", () => {
  let calls: FetchCall[];
  let recentPayload: unknown;

  beforeEach(() => {
    calls = [];
    recentPayload = recentRows;
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: { getItem: () => null, setItem: vi.fn(), removeItem: vi.fn() },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        calls.push({
          body: init?.body ? JSON.parse(String(init.body)) : {},
          method: init?.method ?? "GET",
          url,
        });
        const payload = url.startsWith("/api/media/consumptions/recent") ? recentPayload : dashboard;
        return new Response(JSON.stringify(payload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("loads the global recent list from the dedicated endpoint with a limit", async () => {
    renderPage();
    expect(await screen.findByRole("heading", { name: "Son tüketimler" })).toBeTruthy();
    expect(calls.some((call) => call.url === "/api/media/consumptions/recent?limit=10")).toBe(true);
  });

  it("renders title, kind, action amount and date for every recent consumption", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Son tüketimler" })).toBeTruthy();
    await waitFor(() => expect(screen.getByText("Dune: Prophecy")).toBeTruthy());

    const showLink = screen.getByRole("link", { name: "Dune: Prophecy detayını aç" });
    expect(showLink.getAttribute("href")).toBe("#/media/media-1");
    expect(screen.getByText("Tamamlama")).toBeTruthy();
    expect(screen.getByText("5 episode")).toBeTruthy();
    const showRow = showLink.closest("li");
    expect(showRow).not.toBeNull();
    expect(within(showRow as HTMLElement).getByText("Dizi")).toBeTruthy();

    const bookLink = screen.getByRole("link", { name: "Yabancı detayını aç" });
    expect(bookLink.getAttribute("href")).toBe("#/media/media-2");
    expect(screen.getByText("Hızlı ilerleme")).toBeTruthy();
    expect(screen.getByText("30 page")).toBeTruthy();
    const bookRow = bookLink.closest("li");
    expect(bookRow).not.toBeNull();
    expect(within(bookRow as HTMLElement).getByText("Kitap")).toBeTruthy();

    const times = screen.getAllByRole("time");
    expect(times).toHaveLength(2);
    expect(times[0].getAttribute("dateTime")).toBe("2026-09-02T18:30:00Z");
  });

  it("shows an empty state when there is no consumption history", async () => {
    recentPayload = [];
    renderPage();

    expect(await screen.findByRole("heading", { name: "Son tüketimler" })).toBeTruthy();
    expect(await screen.findByText("Henüz tüketim kaydı yok.")).toBeTruthy();
  });
});
