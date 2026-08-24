// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentType } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "@/modules";
import { DialogHost } from "@/core/dialog";
import { allRoutes, allTodayWidgets } from "@/core/registry";
import { ToastProvider } from "@/core/ui";
import { MediaPage } from "./MediaPage";

type FetchCall = { body: unknown; method: string; path: string };

const mediaItem = {
  archived_at: null,
  backdrop_path: null,
  backdrop_url: "https://images.example.test/dune-backdrop.jpg",
  cover_path: "dune.webp",
  cover_url: "https://images.example.test/dune.jpg",
  created_at: "2026-08-20T10:00:00Z",
  favorite: false,
  finished_at: null,
  id: "media-1",
  kind: "show",
  last_synced_at: "2026-08-23T10:00:00Z",
  meta: { tags: ["bilim kurgu"] },
  monitored: true,
  notes: "İkinci sezon",
  owned: true,
  ownership: { format: "digital" },
  progress: 3,
  progress_measure: "episode",
  provider: "tmdb",
  provider_id: "tv:42",
  provider_ids: { tmdb: "42" },
  release_date: "2026-01-01",
  review: "Güçlü bir sezon.",
  score: 8,
  started_at: "2026-08-01T10:00:00Z",
  status: "in_progress",
  summary: "Bir bilim kurgu dizisi.",
  title: "Dune: Prophecy",
  total: 8,
  updated_at: "2026-08-23T10:00:00Z",
};

const collection = {
  id: "collection-1",
  title: "Favoriler",
  description: "Yeniden dönülecekler",
  color: "#1F5FD0",
  position: 0,
  created_at: "2026-08-20T10:00:00Z",
  updated_at: "2026-08-20T10:00:00Z",
};

const units = [
  {
    id: "unit-1", media_id: "media-1", parent_id: null, title: "Birinci bölüm",
    unit_type: "episode", number: 1, duration_min: 48,
    release_at: "2026-08-01T10:00:00Z", progress_total: 1,
    progress_measure: "episode", provider: "tmdb", provider_id: "ep-1",
    provider_ids: {}, cover_url: null, cover_path: null, meta: {}, children: [],
    created_at: "2026-08-01T10:00:00Z", updated_at: "2026-08-01T10:00:00Z",
  },
  {
    id: "unit-2", media_id: "media-1", parent_id: null, title: "İkinci bölüm",
    unit_type: "episode", number: 2, duration_min: 51,
    release_at: "2026-08-08T10:00:00Z", progress_total: 1,
    progress_measure: "episode", provider: "tmdb", provider_id: "ep-2",
    provider_ids: {}, cover_url: null, cover_path: null, meta: {}, children: [],
    created_at: "2026-08-08T10:00:00Z", updated_at: "2026-08-08T10:00:00Z",
  },
];

const consumption = {
  id: "consumption-1", media_id: "media-1", cycle_id: "cycle-1",
  unit_id: "unit-2", client_uuid: "11111111-1111-4111-8111-111111111111",
  action: "complete_unit", measure: "episode", amount: 1, progress_after: 3,
  occurred_at: "2026-08-22T10:00:00Z", duration_min: 51, note: null, meta: {},
  created_at: "2026-08-22T10:00:00Z",
};

const cycle = {
  id: "cycle-1", media_id: "media-1", ordinal: 1, status: "completed",
  started_at: "2026-08-01T10:00:00Z", completed_at: "2026-08-22T10:00:00Z",
  last_caught_up_at: null, score: 8, notes: null,
  created_at: "2026-08-01T10:00:00Z", updated_at: "2026-08-22T10:00:00Z",
};

function json(value: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function defaultResponse(path: string, method: string): Response {
  if (path.startsWith("/api/media/providers")) return json([{
    id: "tmdb", kinds: ["movie", "show"], ready: true, missing_settings: [],
    last_run_at: "2026-08-23T10:00:00Z", last_status: "ok", last_error: null,
    capabilities: { search: true, details: true, units: true, upcoming: true, cache_artwork: true, requires_settings: ["media.tmdb_key"] },
  }]);
  if (path.startsWith("/api/sources/sync")) return json({ active: null, last_completed: null, running: [], sources: [] });
  if (path.startsWith("/api/media/dashboard")) return json({
    continue_items: [mediaItem], upcoming: units.slice(0, 1),
    recent_consumptions: [consumption],
    stats: { total: 1, in_progress: 1, completed: 0, planned: 0, by_kind: { show: 1 }, total_duration_min: 51, scored_count: 1, average_score: 8 },
  });
  if (path.startsWith("/api/media/upcoming")) return json(units);
  if (path.startsWith("/api/media/stats")) return json({ total: 1, in_progress: 1, completed: 0, planned: 0, by_kind: { show: 1 }, total_duration_min: 51, scored_count: 1, average_score: 8 });
  if (path.startsWith("/api/media/collections")) return method === "POST" ? json(collection, 201) : method === "PATCH" ? json({ ...collection, title: "Bilim kurgu" }) : method === "DELETE" ? json(null, 204) : json([collection]);
  if (path === "/api/media/media-1") return json({ item: mediaItem, units, cycles: [cycle], consumptions: [consumption], collections: [collection] });
  if (path.startsWith("/api/media/search")) return json([{
    provider: "tmdb", provider_id: "movie:99", title: "Dune", subtitle: "Film",
    summary: "Arrakis", total: 1, progress_measure: "item", cover: null,
    backdrop: null, cover_url: "https://images.example.test/dune-film.jpg",
    backdrop_url: null, year: 2021, provider_ids: { tmdb: "99" },
    meta: { tmdb_type: "movie" }, metadata: { provider: "tmdb", provider_id: "movie:99" },
  }]);
  if (path === "/api/media" && method === "POST") return json(mediaItem, 201);
  if (path.startsWith("/api/media") && method !== "GET") return method === "DELETE" ? json(null, 204) : json(consumption, 201);
  if (path.startsWith("/api/media")) return json({ items: [mediaItem], total: 2, next_cursor: "next-1" });
  if (path.startsWith("/api/today/agenda")) return json({
    auto_suggestions: true, day: "2026-08-23",
    timed: [], checklist: [], completed: [],
    suggestions: { todos: [], rss: [], media: [{
      action: "log_media", children: [], completed: false, context_only: false,
      cover_url: "/api/media/assets/dune.webp", duration_min: null, feed_title: null,
      id: "media-1", kind: "media", media_kind: "show", media_status: "in_progress",
      parent_id: null, progress_label: "3 / 8 bölüm", project_title: null,
      read_only: false, recur: null, slot_id: null, source: "suggestion",
      starts_at: null, title: "Dune: Prophecy", url: null,
    }] },
  });
  if (path.startsWith("/api/plan")) return method === "POST" ? json({ id: "slot-1" }, 201) : json([]);
  return json({});
}

let calls: FetchCall[];
let responder: (path: string, method: string) => Response | Promise<Response>;

function installFetch() {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = new URL(String(input), "http://localhost").pathname + new URL(String(input), "http://localhost").search;
    const method = init?.method ?? "GET";
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ body, method, path });
    return responder(path, method);
  }));
}

function renderView(path: string, Component: ComponentType = MediaPage) {
  location.hash = path;
  fireEvent(window, new HashChangeEvent("hashchange"));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <Component />
        <DialogHost />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("responsive media frontend", () => {
  beforeEach(() => {
    calls = [];
    responder = (path, method) => defaultResponse(path, method);
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: { getItem: () => null, setItem: vi.fn(), removeItem: vi.fn() },
    });
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
    installFetch();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("registers the complete media IA including the dynamic detail route and Today widget", () => {
    const paths = allRoutes().filter((route) => route.path.startsWith("/media")).map((route) => route.path);
    expect(paths).toEqual([
      "/media", "/media/library", "/media/collections", "/media/upcoming",
      "/media/stats", "/media/trash", "/media/:id",
    ]);
    expect(allTodayWidgets().some((widget) => widget.component.name === "MediaContinueWidget")).toBe(true);
  });

  it("keeps filters in the URL and requests the next cursor page", async () => {
    const user = userEvent.setup();
    renderView("#/media/library?kind=show&status=in_progress&q=dune&owned=true&sort=title");

    expect(await screen.findByText("Dune: Prophecy")).toBeTruthy();
    await waitFor(() => expect(calls.some((call) => call.path.includes("/api/media?") && call.path.includes("kind=show") && call.path.includes("q=dune") && call.path.includes("owned=true") && call.path.includes("sort=title"))).toBe(true));
    await user.click(screen.getByRole("button", { name: "Daha fazla yükle" }));
    await waitFor(() => expect(calls.some((call) => call.path.includes("cursor=next-1"))).toBe(true));

    const search = screen.getByRole("searchbox", { name: "Kütüphanede ara" });
    await user.clear(search);
    await user.type(search, "arrival");
    await waitFor(() => expect(location.hash).toContain("q=arrival"));
  });

  it("searches a ready provider, creates the discriminated provider body, and explains a duplicate", async () => {
    const user = userEvent.setup();
    let createCount = 0;
    responder = (path, method) => {
      if (path === "/api/media" && method === "POST") {
        createCount += 1;
        return createCount === 1 ? json(mediaItem, 201) : json({ detail: "Bu provider kaydı kütüphanede zaten var" }, 409);
      }
      return defaultResponse(path, method);
    };
    renderView("#/media/library");

    await user.click(await screen.findByRole("button", { name: "Medya ekle" }));
    await user.type(screen.getByRole("searchbox", { name: "Provider'da ara" }), "Dune");
    await user.click(screen.getByRole("button", { name: "Ara" }));
    expect(await screen.findByText("Dune", { selector: "h3" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    await waitFor(() => expect(calls.some((call) => call.method === "POST" && call.path === "/api/media" && (call.body as { source?: string }).source === "provider")).toBe(true));

    await user.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    expect(await screen.findByText("Bu kayıt kütüphanende zaten var.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Kütüphanede bul" }).getAttribute("href")).toContain("#/media/library?q=Dune");
  });

  it("sends quick, set, finish, unit, cycle and collection membership mutations", async () => {
    const user = userEvent.setup();
    renderView("#/media/media-1");
    expect(await screen.findByRole("heading", { name: "Dune: Prophecy" })).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Sonraki bölüm" }));
    await user.clear(screen.getByRole("spinbutton", { name: "İlerleme değeri" }));
    await user.type(screen.getByRole("spinbutton", { name: "İlerleme değeri" }), "5");
    await user.click(screen.getByRole("button", { name: "İlerlemeyi ayarla" }));
    await user.click(screen.getByRole("button", { name: "Tamamlandı olarak işaretle" }));
    await user.click(screen.getByRole("button", { name: "Birinci bölümü tamamla" }));
    await user.click(screen.getByRole("button", { name: "İkinci bölümün tamamlamasını geri al" }));
    await user.click(screen.getByRole("button", { name: "Yeni tur başlat" }));
    await user.click(screen.getByRole("button", { name: "Favoriler koleksiyonundan çıkar" }));

    await waitFor(() => {
      const consumptionBodies = calls.filter((call) => call.path === "/api/media/media-1/consumptions").map((call) => call.body as { action: string; client_uuid?: string });
      expect(consumptionBodies.map((body) => body.action)).toEqual(expect.arrayContaining(["quick", "set", "finish", "complete_unit", "uncomplete_unit"]));
      expect(consumptionBodies.every((body) => Boolean(body.client_uuid))).toBe(true);
      expect(new Set(consumptionBodies.map((body) => body.client_uuid)).size).toBe(consumptionBodies.length);
      expect(calls.some((call) => call.path === "/api/media/media-1/cycles" && call.method === "POST")).toBe(true);
      expect(calls.some((call) => call.path === "/api/media/collections/collection-1/items/media-1" && call.method === "DELETE")).toBe(true);
    });
  });

  it("creates, renames and confirm-deletes collections", async () => {
    const user = userEvent.setup();
    renderView("#/media/collections");
    expect(await screen.findByText("Favoriler")).toBeTruthy();
    await user.type(screen.getByRole("textbox", { name: "Koleksiyon adı" }), "Hafta sonu");
    await user.click(screen.getByRole("button", { name: "Koleksiyon oluştur" }));
    await user.click(screen.getByRole("button", { name: "Favoriler koleksiyonunu düzenle" }));
    const rename = screen.getByRole("textbox", { name: "Koleksiyon adını düzenle" });
    await user.clear(rename);
    await user.type(rename, "Bilim kurgu");
    await user.click(screen.getByRole("button", { name: "Koleksiyon değişikliklerini kaydet" }));
    await user.click(screen.getByRole("button", { name: "Favoriler koleksiyonunu sil" }));
    await user.click(await screen.findByRole("button", { name: "Koleksiyonu sil" }));
    await waitFor(() => expect(calls.map((call) => `${call.method} ${call.path}`)).toEqual(expect.arrayContaining([
      "POST /api/media/collections", "PATCH /api/media/collections/collection-1", "DELETE /api/media/collections/collection-1",
    ])));
  });

  it("restores trash rows and permanently deletes only after confirmation", async () => {
    const user = userEvent.setup();
    responder = (path, method) => path.startsWith("/api/media?") && method === "GET"
      ? json({ items: [{ ...mediaItem, archived_at: "2026-08-23T10:00:00Z" }], total: 1, next_cursor: null })
      : defaultResponse(path, method);
    renderView("#/media/trash");
    expect(await screen.findByText("Dune: Prophecy")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Dune: Prophecy kaydını geri yükle" }));
    await user.click(screen.getByRole("button", { name: "Dune: Prophecy kaydını kalıcı sil" }));
    expect(await screen.findByText("Bu işlem geri alınamaz.")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Kalıcı sil" }));
    await waitFor(() => expect(calls.map((call) => `${call.method} ${call.path}`)).toEqual(expect.arrayContaining([
      "POST /api/media/media-1/restore", "DELETE /api/media/media-1/permanent",
    ])));
  });

  it("opens mobile filters as a dismissible sheet and disables every write offline", async () => {
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: false });
    const user = userEvent.setup();
    renderView("#/media/library");
    const add = await screen.findByRole("button", { name: "Medya ekle" });
    expect(add.hasAttribute("disabled")).toBe(true);
    await user.click(screen.getByRole("button", { name: "Filtreleri aç" }));
    expect(screen.getByRole("dialog", { name: "Kütüphane filtreleri" })).toBeTruthy();
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Kütüphane filtreleri" })).toBeNull());

    renderView("#/media/media-1");
    expect((await screen.findByRole("button", { name: "Sonraki bölüm" })).hasAttribute("disabled")).toBe(true);
    expect(document.querySelector("[data-mobile-media-actions]")).toBeTruthy();
  });

  it("renders composed loading, retryable error and useful empty library states", async () => {
    let resolveLibrary: ((response: Response) => void) | null = null;
    responder = (path, method) => {
      if (path.startsWith("/api/media") && !path.includes("providers") && method === "GET") {
        return new Promise<Response>((resolve) => { resolveLibrary = resolve; });
      }
      return defaultResponse(path, method);
    };
    const first = renderView("#/media/library");
    expect(await screen.findByRole("status", { name: "Kütüphane yükleniyor" })).toBeTruthy();
    resolveLibrary?.(json({ items: [], total: 0, next_cursor: null }));
    expect(await screen.findByText("Kütüphanen boş")).toBeTruthy();
    first.unmount();

    let attempts = 0;
    responder = (path, method) => {
      if (path.startsWith("/api/media") && !path.includes("providers") && method === "GET") {
        attempts += 1;
        return attempts === 1 ? json({ detail: "boom" }, 500) : json({ items: [], total: 0, next_cursor: null });
      }
      return defaultResponse(path, method);
    };
    renderView("#/media/library");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Kütüphaneyi yeniden dene" }));
    expect(await screen.findByText("Kütüphanen boş")).toBeTruthy();
  });

  it("renders the Today continuation widget and plans an unplanned media row", async () => {
    const user = userEvent.setup();
    const Widget = allTodayWidgets().find((entry) => entry.component.name === "MediaContinueWidget")?.component;
    expect(Widget).toBeTruthy();
    renderView("#/", Widget);
    expect(await screen.findByText("Dune: Prophecy")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Dune: Prophecy kaydını bugüne ekle" }));
    await waitFor(() => expect(calls.some((call) => call.method === "POST" && call.path === "/api/plan" && (call.body as { entity_id?: string }).entity_id === "media-1")).toBe(true));
    expect(screen.getByRole("link", { name: "Dune: Prophecy ayrıntısını aç" }).getAttribute("href")).toBe("#/media/media-1");
  });
});
