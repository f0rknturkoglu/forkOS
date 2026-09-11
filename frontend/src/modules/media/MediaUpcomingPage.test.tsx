// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { todayKey } from "@/lib/date";
import { MediaUpcomingPage } from "./MediaUpcomingPage";

const TMDB_URL = "https://image.tmdb.org/t/p/w342/dune.jpg";

function isoInDays(days: number): string {
  return new Date(Date.now() + days * 86_400_000).toISOString();
}

const entries = [
  {
    entry_type: "unit",
    entity_id: "unit-1",
    media_id: "media-1",
    media_title: "Dune: Prophecy",
    title: "Bölüm 4",
    kind: "show",
    provider: "tmdb",
    release_at: isoInDays(0),
    cover_url: TMDB_URL,
    monitored: true,
    unit_type: "episode",
    number: 4,
  },
  {
    entry_type: "item",
    entity_id: "media-2",
    media_id: "media-2",
    media_title: "Dune: Part Three",
    title: "Dune: Part Three",
    kind: "movie",
    provider: "tmdb",
    release_at: isoInDays(3),
    cover_url: null,
    monitored: false,
    unit_type: null,
    number: null,
  },
  {
    entry_type: "item",
    entity_id: "media-3",
    media_id: "media-3",
    media_title: "Rüzgarın Adı",
    title: "Rüzgarın Adı",
    kind: "book",
    provider: "openlibrary",
    release_at: isoInDays(20),
    cover_url: null,
    monitored: false,
    unit_type: null,
    number: null,
  },
  {
    entry_type: "item",
    entity_id: "media-4",
    media_id: "media-4",
    media_title: "Uzak Diyar",
    title: "Uzak Diyar",
    kind: "movie",
    provider: "tmdb",
    release_at: isoInDays(120),
    cover_url: null,
    monitored: false,
    unit_type: null,
    number: null,
  },
];

const providers = [
  {
    id: "tmdb",
    kinds: ["movie", "show"],
    ready: true,
    missing_settings: [],
    last_run_at: "2026-08-23T10:00:00Z",
    last_status: "ok",
    last_error: null,
    state: "ok",
    capabilities: {
      search: true,
      details: true,
      units: true,
      upcoming: true,
      cache_artwork: true,
      requires_settings: [],
    },
  },
];

type FetchCall = { body: Record<string, unknown>; method: string; url: string };

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MediaUpcomingPage />
    </QueryClientProvider>,
  );
}

describe("media upcoming page", () => {
  let calls: FetchCall[];
  let upcoming: { entries: unknown[]; total: number };
  let providerRows: unknown[];
  let monitoredTotal: number;
  let upcomingStatus: number;

  beforeEach(() => {
    calls = [];
    upcoming = { entries, total: entries.length };
    providerRows = providers;
    monitoredTotal = 2;
    upcomingStatus = 200;
    location.hash = "/media/upcoming";
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: { getItem: () => null, setItem: vi.fn(), removeItem: vi.fn() },
    });
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        calls.push({
          body: init?.body ? JSON.parse(String(init.body)) : {},
          method: init?.method ?? "GET",
          url,
        });
        if (url.startsWith("/api/media/upcoming")) {
          return new Response(JSON.stringify(upcomingStatus === 200 ? upcoming : { detail: "boom" }), {
            status: upcomingStatus,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (url.startsWith("/api/media/providers")) {
          return new Response(JSON.stringify(providerRows), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (url.startsWith("/api/media?")) {
          return new Response(JSON.stringify({ items: [], total: monitoredTotal, next_cursor: null }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { "Content-Type": "application/json" } });
      }),
    );
  });

  afterEach(() => {
    cleanup();
    location.hash = "";
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("requests the default window and groups releases by local date", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Bugün" })).toBeTruthy();
    expect(calls.map((call) => call.url)).toContain("/api/media/upcoming?days=30");
    expect(screen.getByRole("heading", { name: "Bu hafta" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Bu ay" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Daha sonra" })).toBeTruthy();

    expect(screen.getByText(/^Bugün ·/)).toBeTruthy();
    expect(screen.getByText(/^3 gün sonra ·/)).toBeTruthy();

    const unitRow = screen.getByRole("link", { name: "Dune: Prophecy kaydını aç" }).closest("li");
    expect(unitRow).not.toBeNull();
    expect(within(unitRow as HTMLElement).getByText(/^Bölüm 4 · #4 bölüm$/)).toBeTruthy();
    expect(within(unitRow as HTMLElement).getByText("Takip ediliyor")).toBeTruthy();
  });

  it("drives the request from URL filters and keeps chip selections in the URL", async () => {
    const user = userEvent.setup();
    location.hash = "/media/upcoming?days=7&kind=show&provider=tmdb";
    renderPage();

    expect(await screen.findByRole("heading", { name: "Bugün" })).toBeTruthy();
    expect(calls.map((call) => call.url)).toContain("/api/media/upcoming?days=7&kind=show&provider=tmdb");
    expect(screen.getByRole("button", { name: "7 gün" }).getAttribute("aria-pressed")).toBe("true");

    await user.click(screen.getByRole("button", { name: "90 gün" }));
    await waitFor(() => expect(location.hash).toBe("#/media/upcoming?days=90&kind=show&provider=tmdb"));
  });

  it("plans the media for today and toggles monitoring", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByRole("heading", { name: "Bugün" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Dune: Prophecy kaydını bugüne ekle" }));
    await waitFor(() =>
      expect(calls).toContainEqual({
        body: { entity_id: "media-1", day: todayKey() },
        method: "POST",
        url: "/api/plan",
      }),
    );

    await user.click(screen.getByRole("button", { name: "Dune: Prophecy takibini kapat" }));
    await waitFor(() =>
      expect(calls).toContainEqual({
        body: { monitored: false },
        method: "PATCH",
        url: "/api/media/media-1",
      }),
    );
    await user.click(screen.getByRole("button", { name: "Dune: Part Three takibini aç" }));
    await waitFor(() =>
      expect(calls).toContainEqual({
        body: { monitored: true },
        method: "PATCH",
        url: "/api/media/media-2",
      }),
    );
  });

  it("explains that nothing is monitored when the library has no followed media", async () => {
    upcoming = { entries: [], total: 0 };
    monitoredTotal = 0;
    renderPage();

    expect(
      await screen.findByText('Takip edilen medya yok. Bir kaydı açıp "Yeni yayınları takip et"i aç.'),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Kütüphaneyi aç" })).toBeTruthy();
  });

  it("explains that providers were never scanned", async () => {
    upcoming = { entries: [], total: 0 };
    providerRows = [
      {
        ...providers[0],
        state: "never_run",
        last_status: null,
        last_run_at: null,
      },
    ];
    renderPage();

    expect(await screen.findByText('Sağlayıcı henüz taranmadı; "Şimdi tara" ile başlat.')).toBeTruthy();
  });

  it("reports an empty window when media is monitored but nothing releases soon", async () => {
    upcoming = { entries: [], total: 0 };
    renderPage();

    expect(await screen.findByText("Önümüzdeki 30 gün içinde yayın yok.")).toBeTruthy();
  });

  it("surfaces a retryable error and the offline note", async () => {
    upcomingStatus = 500;
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: false });
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("Yayınlar alınamadı: boom")).toBeTruthy();
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.getByText("Çevrimdışısın — yayınlar salt okunur.")).toBeTruthy();

    upcomingStatus = 200;
    await user.click(screen.getByRole("button", { name: "Yeniden dene" }));
    await waitFor(() => expect(calls.filter((call) => call.url.startsWith("/api/media/upcoming")).length).toBe(2));
  });
});
