import { queryClient } from "@/core/queryClient";
// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DialogHost } from "@/core/dialog";
import { ToastProvider } from "@/core/ui";
import { MediaPage } from "./MediaPage";

const items = [
  { id: "movie-1", title: "Arrival", kind: "movie", status: "in_progress", progress: 2, total: 10, progress_measure: "item", provider: "tmdb", provider_id: "movie:329865", provider_ids: { tmdb: "329865" } },
  { id: "book-1", title: "Dune", kind: "book", status: "planned", progress: 0, total: 500, progress_measure: "page", provider: "openlibrary", provider_id: "/works/OL893415W", provider_ids: {} },
  { id: "anime-1", title: "Monster", kind: "anime", status: "completed", progress: 74, total: 74, progress_measure: "episode", provider: "anilist", provider_id: "19", provider_ids: { anilist: "19" } },
  { id: "game-1", title: "Disco Elysium", kind: "game", status: "paused", progress: 4, total: 20, progress_measure: "hour", provider: "rawg", provider_id: "3212", provider_ids: { rawg: "3212" } },
].map((item) => ({
  archived_at: null, backdrop_path: null, backdrop_url: null, cover_path: null, cover_url: null,
  created_at: "2026-08-20T10:00:00Z", favorite: false, finished_at: null, last_synced_at: null,
  meta: {}, monitored: false, notes: null, owned: false, ownership: {}, release_date: null,
  review: null, score: null, started_at: null, summary: null, updated_at: "2026-08-20T10:00:00Z",
  ...item,
}));

type FetchCall = { body: unknown; method: string; path: string };
let calls: FetchCall[];
let libraryShouldFail: boolean;
let statsShouldFail: boolean;

function json(value: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function responseFor(path: string, method: string): Response {
  if (path === "/api/media" && method === "GET") {
    if (libraryShouldFail) return json({ detail: "library unavailable" }, 500);
    return json({ items, total: items.length, next_cursor: null });
  }
  if (path.startsWith("/api/media?") && method === "GET") {
    if (path.includes("q=dune")) return json({ items: [items[1]], total: 1, next_cursor: null });
    return json({ items, total: items.length, next_cursor: null });
  }
  if (path === "/api/media/stats") {
    if (statsShouldFail) return json({ detail: "stats unavailable" }, 500);
    return json({ total: 4, in_progress: 1, completed: 1, planned: 1 });
  }
  if (path === "/api/media/search/global?q=dune") return json({
    results: [{
      kind: "movie", provider: "tmdb", provider_id: "movie:438631", title: "Dune: Part One",
      subtitle: "Film", summary: null, total: 1, progress_measure: "item", cover: null,
      backdrop: null, cover_url: null, backdrop_url: null, year: 2021,
      provider_ids: { tmdb: "438631" }, meta: {}, metadata: {},
    }],
    warnings: [],
  });
  if (path === "/api/media/providers") return json([]);
  if (path === "/api/sources/sync?scope=media") return json({ active: null, last_completed: null, running: [], sources: [] });
  if (path === "/api/media/movie-1/consumptions" && method === "POST") return json({ id: "consumption-1" }, 201);
  if (path === "/api/media/movie-1" && method === "DELETE") return json(null, 204);
  return json({});
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const invalidate = vi.spyOn(queryClient(), "invalidateQueries").mockResolvedValue(undefined);
  const view = render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MediaPage />
        <DialogHost />
      </ToastProvider>
    </QueryClientProvider>,
  );
  return { ...view, invalidate };
}

describe("cinematic MediaPage", () => {
  beforeEach(() => {
    location.hash = "#/media";
    calls = [];
    libraryShouldFail = false;
    statsShouldFail = false;
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "11111111-1111-4111-8111-111111111111") });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const method = init?.method ?? "GET";
      const body = init?.body ? JSON.parse(String(init.body)) : undefined;
      const path = url.pathname + url.search;
      calls.push({ body, method, path });
      return responseFor(path, method);
    }));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("composes the cinematic library without legacy inline editing or provider-kind search", async () => {
    const { container } = renderPage();

    expect(screen.getByRole("heading", { name: "Medya" })).toBeTruthy();
    expect(screen.getByRole("searchbox", { name: "Tüm medyada ara" })).toBeTruthy();
    expect(screen.queryByRole("combobox", { name: "Arama türü" })).toBeNull();
    await waitFor(() => expect(container.querySelectorAll("[data-media-poster]")).toHaveLength(4));
    expect(container.querySelector("details[data-media-sync]")?.hasAttribute("open")).toBe(false);
    expect(screen.getByText("Toplam").closest("[data-media-metrics]")).toBeTruthy();
    expect(screen.queryByText("İlerleme / toplam")).toBeNull();
    expect(container.querySelector("[data-media-grid]")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Arrival işlemleri" }));
    const menu = screen.getByRole("menu", { name: "Arrival işlemleri menüsü" });
    expect(within(menu).getByRole("menuitem", { name: "TMDB ↗" })).toBeTruthy();
    expect(within(menu).getByRole("menuitem", { name: "Letterboxd ↗" })).toBeTruthy();
    expect(within(menu).getByRole("menuitem", { name: "Çöpe taşı" })).toBeTruthy();
  });

  it("shows library matches before catalog matches in the global composer", async () => {
    const user = userEvent.setup();
    const { container } = renderPage();
    const search = screen.getByRole("searchbox", { name: "Tüm medyada ara" });
    await user.type(search, "dune");

    const libraryHeading = await screen.findByRole("heading", { name: "Kütüphanende" });
    const catalogHeading = screen.getByRole("heading", { name: "Katalog sonuçları" });
    expect(libraryHeading.compareDocumentPosition(catalogHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(await screen.findByRole("heading", { level: 3, name: "Dune" })).toBeTruthy();
    expect(await screen.findByRole("heading", { level: 3, name: "Dune: Part One" })).toBeTruthy();
    expect(container.querySelector("[data-media-library-controls]")).toBeNull();
    expect(container.querySelector("[data-media-grid]")).toBeNull();

    await user.clear(search);
    await waitFor(() => expect(container.querySelector("[data-media-library-controls]")).toBeTruthy());
    expect(container.querySelector("[data-media-grid]")).toBeTruthy();
  });

  it("posts append-only quick progress with a fresh UUID and invalidates all six families", async () => {
    const user = userEvent.setup();
    const { invalidate } = renderPage();
    await user.click(await screen.findByRole("button", { name: "Arrival ilerlemesini bir artır" }));

    await waitFor(() => expect(calls).toContainEqual({
      path: "/api/media/movie-1/consumptions",
      method: "POST",
      body: { action: "quick", amount: 1, client_uuid: "11111111-1111-4111-8111-111111111111", measure: "item" },
    }));
    expect(invalidate.mock.calls.map(([filters]) => (filters as { queryKey: string[] }).queryKey)).toEqual([
      ["media"], ["media-detail"], ["media-stats"], ["media-dashboard"], ["today-agenda"], ["activity"],
    ]);
  });

  it("keeps kind and status filters local while using them in library requests", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Arrival");
    await user.click(screen.getByRole("button", { name: "Kitap" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Durum filtresi" }), "planned");

    await waitFor(() => expect(calls.some(({ path }) => path === "/api/media?kind=book&status=planned")).toBe(true));
    expect(location.hash).toBe("#/media");
  });

  it("renders retryable library and stats errors", async () => {
    const user = userEvent.setup();
    libraryShouldFail = true;
    statsShouldFail = true;
    renderPage();

    const libraryRetry = await screen.findByRole("button", { name: "Kütüphaneyi yeniden dene" });
    const statsRetry = await screen.findByRole("button", { name: "İstatistikleri yeniden dene" });
    libraryShouldFail = false;
    statsShouldFail = false;
    await user.click(libraryRetry);
    await user.click(statsRetry);
    expect(await screen.findByText("Arrival")).toBeTruthy();
    await waitFor(() => expect(screen.queryByRole("button", { name: "İstatistikleri yeniden dene" })).toBeNull());
  });
});
