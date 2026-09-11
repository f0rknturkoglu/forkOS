// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MediaStatsPage } from "./MediaStatsPage";

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

const dashboard = {
  continue_items: [],
  upcoming: [],
  recent_consumptions: recentRows,
  stats: {
    total: 6,
    in_progress: 1,
    completed: 4,
    planned: 1,
    by_kind: { book: 1, movie: 5 },
    by_measure: { page: 320, episode: 12, minute: 90, item: 4 },
    total_duration_min: 205,
    pomodoro_minutes: 50,
    scored_count: 3,
    average_score: 8.666666666666666,
    score_distribution: { "7": 1, "9": 2 },
    conversion: { planned: 5, started: 3, completed: 2 },
    active_days: 6,
    busiest_day: { day: "2026-09-04", count: 6 },
    completed_in_range: 2,
  },
};

type FetchCall = { method: string; url: string };

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

describe("media stats page", () => {
  let calls: FetchCall[];
  let payload: unknown;

  beforeEach(() => {
    calls = [];
    payload = dashboard;
    location.hash = "/media/stats";
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: { getItem: () => null, setItem: vi.fn(), removeItem: vi.fn() },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        calls.push({ method: init?.method ?? "GET", url: String(input) });
        return new Response(JSON.stringify(payload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
  });

  afterEach(() => {
    cleanup();
    location.hash = "";
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("reads stats, continuations, upcoming and recent rows from the single dashboard request", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Son tüketimler" })).toBeTruthy();
    expect(calls.map((call) => call.url)).toEqual(["/api/media/dashboard?range=all&recent_limit=20"]);
    expect(calls.some((call) => call.url.startsWith("/media/stats"))).toBe(false);
    expect(calls.some((call) => call.url.includes("/consumptions/recent"))).toBe(false);
  });

  it("drives the dashboard request from the range in the URL", async () => {
    location.hash = "/media/stats?range=month";
    renderPage();

    expect(await screen.findByRole("heading", { name: "Son tüketimler" })).toBeTruthy();
    expect(calls.map((call) => call.url)).toEqual(["/api/media/dashboard?range=month&recent_limit=20"]);
    expect(screen.getByRole("button", { name: "Bu ay" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("keeps the selected range in the URL", async () => {
    const user = userEvent.setup();
    renderPage();
    expect(await screen.findByRole("heading", { name: "Son tüketimler" })).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Bu yıl" }));
    await waitFor(() => expect(location.hash).toBe("#/media/stats?range=year"));

    await user.click(screen.getByRole("button", { name: "Tüm zamanlar" }));
    await waitFor(() => expect(location.hash).toBe("#/media/stats"));
  });

  it("rounds the average score to a single decimal", async () => {
    renderPage();

    expect(await screen.findByText("8.7 / 10")).toBeTruthy();
    expect(screen.queryByText("8.666666666666666 / 10")).toBeNull();
    expect(screen.getByText("3 kayıt puanlandı")).toBeTruthy();
  });

  it("lists every measure on its own row instead of merging them", async () => {
    renderPage();
    expect(await screen.findByText("Okunan sayfa")).toBeTruthy();

    const rows = [
      ["Okunan sayfa", 320],
      ["İzlenen bölüm", 12],
      ["Dinlenen dakika", 90],
      ["Oynanan kayıt", 4],
    ] as const;
    for (const [label, value] of rows) {
      const row = screen.getByText(label).closest("li");
      expect(row).not.toBeNull();
      expect(within(row as HTMLElement).getByText(String(value))).toBeTruthy();
    }
    expect(screen.queryByText("426")).toBeNull();
  });

  it("renders the kind distribution sorted with an accessible text summary", async () => {
    renderPage();
    expect(await screen.findByRole("heading", { name: "Tür dağılımı" })).toBeTruthy();

    const summary = "Film 5 · Kitap 1";
    expect(screen.getByText(summary)).toBeTruthy();
    const chart = screen.getByRole("img", { name: `Tür dağılımı: ${summary}` });
    const bars = within(chart).getAllByRole("listitem");
    expect(within(bars[0]).getByText("Film")).toBeTruthy();
    expect(within(bars[0]).getByText("5")).toBeTruthy();
  });

  it("renders the planned to started to completed funnel with numbers", async () => {
    renderPage();
    expect(await screen.findByRole("heading", { name: "Dönüşüm" })).toBeTruthy();

    const summary = "Planlandı 5 · Başlandı 3 · Tamamlandı 2";
    expect(screen.getByText(summary)).toBeTruthy();
    const funnel = screen.getByRole("img", { name: `Dönüşüm: ${summary}` });
    expect(within(funnel).getByText("Planlandı")).toBeTruthy();
    expect(within(funnel).getByText("Tamamlandı")).toBeTruthy();
  });

  it("renders the 1-10 score histogram and the media rhythm summary", async () => {
    renderPage();
    expect(await screen.findByRole("heading", { name: "Puan dağılımı" })).toBeTruthy();

    const histogram = screen.getByRole("img", { name: /^Puan dağılımı:/ });
    expect(histogram.getAttribute("aria-label")).toBe(
      "Puan dağılımı: 1 puan 0 · 2 puan 0 · 3 puan 0 · 4 puan 0 · 5 puan 0 · 6 puan 0 · 7 puan 1 · 8 puan 0 · 9 puan 2 · 10 puan 0",
    );
    expect(screen.getByText((content) => content.startsWith("1 puan 0 · 2 puan 0"))).toBeTruthy();
    expect(screen.getByText("Bu aralıkta 6 gün medya tükettin.")).toBeTruthy();
    expect(screen.getByText("En aktif gün: 4 Eylül · 6 kayıt")).toBeTruthy();
  });

  it("renders recent consumptions with Turkish measure and action labels", async () => {
    renderPage();
    expect(await screen.findByRole("heading", { name: "Son tüketimler" })).toBeTruthy();

    expect(screen.getByText("Tamamlama")).toBeTruthy();
    expect(screen.getByText("5 bölüm")).toBeTruthy();
    expect(screen.getByText("Hızlı ilerleme")).toBeTruthy();
    expect(screen.getByText("30 sayfa")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Dune: Prophecy detayını aç" }).getAttribute("href")).toBe(
      "#/media/media-1",
    );
  });

  it("shows an empty state when there is no consumption history", async () => {
    payload = { ...dashboard, recent_consumptions: [] };
    renderPage();

    expect(await screen.findByRole("heading", { name: "Son tüketimler" })).toBeTruthy();
    expect(await screen.findByText("Henüz tüketim kaydı yok.")).toBeTruthy();
  });
});
