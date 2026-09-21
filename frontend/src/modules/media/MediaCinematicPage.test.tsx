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
  {
    id: "movie-1",
    title: "Arrival",
    kind: "movie",
    status: "in_progress",
    progress: 2,
    total: 10,
    progress_measure: "item",
    provider: "tmdb",
    provider_id: "movie:329865",
    provider_ids: { tmdb: "329865" },
  },
  {
    id: "book-1",
    title: "Dune",
    kind: "book",
    status: "planned",
    progress: 0,
    total: 500,
    progress_measure: "page",
    provider: "openlibrary",
    provider_id: "/works/OL893415W",
    provider_ids: {},
  },
  {
    id: "anime-1",
    title: "Monster",
    kind: "anime",
    status: "completed",
    progress: 74,
    total: 74,
    progress_measure: "episode",
    provider: "anilist",
    provider_id: "19",
    provider_ids: { anilist: "19" },
  },
  {
    id: "game-1",
    title: "Disco Elysium",
    kind: "game",
    status: "paused",
    progress: 4,
    total: 20,
    progress_measure: "hour",
    provider: "rawg",
    provider_id: "3212",
    provider_ids: { rawg: "3212" },
  },
].map((item) => ({
  archived_at: null,
  backdrop_path: null,
  backdrop_url: null,
  cover_path: null,
  cover_url: null,
  created_at: "2026-08-20T10:00:00Z",
  favorite: false,
  finished_at: null,
  last_synced_at: null,
  meta: {},
  monitored: false,
  notes: null,
  owned: false,
  ownership: {},
  release_date: null,
  review: null,
  score: null,
  started_at: null,
  summary: null,
  updated_at: "2026-08-20T10:00:00Z",
  ...item,
}));

type FetchCall = { body: unknown; method: string; path: string };
let calls: FetchCall[];
let libraryShouldFail: boolean;

function json(value: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function responseFor(path: string, method: string): Response {
  if (path === "/api/media?status=in_progress&limit=6" && method === "GET")
    return json({ items: [items[0]], total: 1, next_cursor: null });
  if (path.startsWith("/api/media?") && method === "GET") {
    if (path.includes("kind=book")) return json({ items: [items[1]], total: 1, next_cursor: null });
    return json({ items, total: items.length, next_cursor: null });
  }
  if (path === "/api/media" && method === "GET") {
    if (libraryShouldFail) return json({ detail: "library unavailable" }, 500);
    return json({ items, total: items.length, next_cursor: null });
  }
  if (path === "/api/media/movie-1/consumptions" && method === "POST") return json({ id: "consumption-1" }, 201);
  if (path === "/api/media/movie-1" && method === "DELETE") return json(null, 204);
  if (path.startsWith("/api/media/collections")) return json([]);
  if (path.startsWith("/api/media/providers")) return json([]);
  if (path.startsWith("/api/media/search")) return json({ results: [], warnings: [], cached: false });
  if (path === "/api/sources/sync?scope=media")
    return json({ active: null, last_completed: null, running: [], sources: [] });
  if (path.startsWith("/api/entities")) return json([]);
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
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "11111111-1111-4111-8111-111111111111") });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = new URL(String(input), "http://localhost");
        const method = init?.method ?? "GET";
        const body = init?.body ? JSON.parse(String(init.body)) : undefined;
        const path = url.pathname + url.search;
        calls.push({ body, method, path });
        return responseFor(path, method);
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("composes the compact library header without the metrics strip or a second search box", async () => {
    const { container } = renderPage();

    expect(screen.getByRole("heading", { name: "Kütüphane" })).toBeTruthy();
    expect(screen.getByText("Medya")).toBeTruthy();
    expect(screen.getByRole("searchbox", { name: "Kütüphanede ara" })).toBeTruthy();
    expect(screen.queryByRole("searchbox", { name: "Tüm medyada ara" })).toBeNull();
    expect(screen.queryByRole("searchbox", { name: "Provider'da ara" })).toBeNull();
    expect(container.querySelector("[data-media-metrics]")).toBeNull();
    expect(screen.queryByText("Toplam")).toBeNull();
    expect(screen.getByRole("button", { name: "Medya ekle" })).toBeTruthy();
    expect(await screen.findByText("4 kayıt · 1 devam ediyor")).toBeTruthy();

    await waitFor(() => expect(container.querySelectorAll("[data-media-poster]")).toHaveLength(4));
    expect(container.querySelector("[data-media-grid]")).toBeTruthy();
    expect(container.querySelector("details[data-media-sync]")?.hasAttribute("open")).toBe(false);

    // Kaynak durumu ana içeriğin altında kalır.
    const grid = container.querySelector("[data-media-grid]");
    const sync = container.querySelector("[data-media-sync]");
    if (!grid || !sync) throw new Error("grid veya kaynak özeti yok");
    expect(grid.compareDocumentPosition(sync) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    await userEvent.setup().click(screen.getByRole("button", { name: "Arrival işlemleri" }));
    const menu = screen.getByRole("menu", { name: "Arrival işlemleri menüsü" });
    expect(within(menu).getByRole("menuitem", { name: "TMDB ↗" })).toBeTruthy();
    expect(within(menu).getByRole("menuitem", { name: "Koleksiyona ekle" })).toBeTruthy();
    expect(within(menu).getByRole("menuitem", { name: "Çöpe taşı" })).toBeTruthy();
  });

  it("kayıtlı görünüm yüzeyi sunmaz ve bilinmeyen ?saved bağlantısında çökmez", async () => {
    location.hash = "#/media?saved=bilinmeyen";
    renderPage();

    // Eski `?saved=` bağlantısı yok sayılır: kütüphane normal akışta yüklenir.
    await waitFor(() => expect(calls.some((call) => call.path === "/api/media")).toBe(true));
    expect((await screen.findAllByText("Arrival")).length).toBeGreaterThan(0);
    // Saved-view soyutlaması arayüzden tamamen çıktı.
    expect(screen.queryByRole("button", { name: "Kayıtlı görünümler" })).toBeNull();
    expect(calls.some((call) => call.path.startsWith("/api/views"))).toBe(false);
  });

  it("moves every quick filter into the URL and requests it from the library", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findAllByText("Arrival");

    await user.click(screen.getByRole("button", { name: "Tamamlandı" }));
    await waitFor(() => expect(location.hash).toContain("status=completed"));
    await waitFor(() => expect(calls.some(({ path }) => path.includes("status=completed"))).toBe(true));

    await user.click(screen.getByRole("button", { name: "Kitap" }));
    await waitFor(() => expect(location.hash).toContain("kind=book"));
    await waitFor(() => expect(calls.some(({ path }) => path.startsWith("/api/media?kind=book"))).toBe(true));
    expect(location.hash).toContain("status=completed");
    // Tür seçilince durum cipleri türün dilini konuşur.
    expect(screen.getByRole("button", { name: "Okundu" })).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Filtreleri temizle" }));
    await waitFor(() => expect(location.hash).toBe("#/media"));
  });

  it("posts append-only quick progress with a fresh UUID and invalidates the media families", async () => {
    const user = userEvent.setup();
    const { invalidate } = renderPage();
    await user.click(await screen.findByRole("button", { name: "Arrival işlemleri" }));
    await user.click(await screen.findByRole("menuitem", { name: "Arrival için +1 kayıt" }));

    await waitFor(() =>
      expect(calls).toContainEqual({
        path: "/api/media/movie-1/consumptions",
        method: "POST",
        body: { action: "quick", amount: 1, client_uuid: "11111111-1111-4111-8111-111111111111", measure: "item" },
      }),
    );
    const invalidated = invalidate.mock.calls.map(([filters]) => (filters as { queryKey: string[] }).queryKey);
    expect(invalidated).toEqual(
      expect.arrayContaining([["media"], ["media-detail"], ["media-stats"], ["media-dashboard"], ["today-agenda"]]),
    );
  });

  it("falls back to the poster skeleton while the first page loads", async () => {
    let resolveLibrary: ((response: Response) => void) | null = null;
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const path = url.pathname + url.search;
      if (path === "/api/media" && (init?.method ?? "GET") === "GET") {
        return new Promise<Response>((resolve) => {
          resolveLibrary = resolve;
        });
      }
      return responseFor(path, init?.method ?? "GET");
    });
    vi.stubGlobal("fetch", fetchMock);
    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <MediaPage />
          <DialogHost />
        </ToastProvider>
      </QueryClientProvider>,
    );

    const loading = await screen.findByRole("status", { name: "Kütüphane yükleniyor" });
    expect(loading.querySelectorAll("[data-media-poster-skeleton]")).toHaveLength(6);
    (resolveLibrary as ((response: Response) => void) | null)?.(
      json({ items, total: items.length, next_cursor: null }),
    );
    await waitFor(() => expect(document.querySelectorAll("[data-media-poster]")).toHaveLength(4));
  });

  it("keeps the previous grid mounted while a refetch is in flight", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(document.querySelectorAll("[data-media-poster]")).toHaveLength(4));

    await user.click(screen.getByRole("button", { name: "Kitap" }));

    await waitFor(() => expect(location.hash).toContain("kind=book"));
    await waitFor(() => expect(document.querySelectorAll("[data-media-poster]")).toHaveLength(1));
    expect(document.querySelector("[data-media-grid]")).toBeTruthy();
  });

  it("renders a retryable library error", async () => {
    const user = userEvent.setup();
    libraryShouldFail = true;
    renderPage();

    const retry = await screen.findByRole("button", { name: "Kütüphaneyi yeniden dene" });
    libraryShouldFail = false;
    await user.click(retry);

    expect(await screen.findByText("Dune")).toBeTruthy();
  });
});
