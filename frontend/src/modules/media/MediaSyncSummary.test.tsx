// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MediaSyncSummary } from "./MediaSyncSummary";

const providers = [
  {
    id: "tmdb", kinds: ["movie", "show"], ready: true, missing_settings: [],
    last_run_at: "2026-08-25T07:30:00.000Z", last_status: "ok", last_error: null, items_found: 12,
    capabilities: { search: true, details: true, units: true, upcoming: true, cache_artwork: true, requires_settings: [] },
  },
  {
    id: "anilist", kinds: ["anime", "manga"], ready: true, missing_settings: [],
    last_run_at: "2026-08-25T07:20:00.000Z", last_status: "ok", last_error: null, items_found: 3,
    capabilities: { search: true, details: true, units: true, upcoming: true, cache_artwork: false, requires_settings: [] },
  },
  {
    id: "openlibrary", kinds: ["book"], ready: true, missing_settings: [],
    last_run_at: "2026-08-25T07:00:00.000Z", last_status: "empty", last_error: null, items_found: 0,
    capabilities: { search: true, details: true, units: false, upcoming: false, cache_artwork: true, requires_settings: [] },
  },
  {
    id: "itunes", kinds: ["music", "podcast"], ready: true, missing_settings: [],
    last_run_at: "2026-08-25T06:30:00.000Z", last_status: "ok", last_error: null, items_found: 8,
    capabilities: { search: true, details: true, units: false, upcoming: false, cache_artwork: false, requires_settings: [] },
  },
  {
    id: "igdb", kinds: ["game"], ready: true, missing_settings: [],
    last_run_at: "2026-08-25T06:00:00.000Z", last_status: "ok", last_error: null, items_found: 5,
    capabilities: { search: true, details: true, units: false, upcoming: true, cache_artwork: true, requires_settings: [] },
  },
  {
    id: "kitsu", kinds: ["anime"], ready: true, missing_settings: ["media.kitsu_key"],
    last_run_at: "2026-08-25T05:00:00.000Z", last_status: "error", last_error: "API anahtarı reddedildi", items_found: 0,
    capabilities: { search: true, details: true, units: true, upcoming: false, cache_artwork: false, requires_settings: ["media.kitsu_key"] },
  },
];

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

function renderSummary(online = true) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const view = render(
    <QueryClientProvider client={client}>
      <MediaSyncSummary online={online} />
    </QueryClientProvider>,
  );
  return { ...view, client };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => { resolve = next; });
  return { promise, resolve };
}

describe("MediaSyncSummary", () => {
  let calls: { method: string; path: string }[];
  let responder: (path: string, method: string) => Response | Promise<Response>;

  beforeEach(() => {
    vi.spyOn(Date, "now").mockReturnValue(new Date("2026-08-25T08:00:00.000Z").getTime());
    calls = [];
    responder = (path, method) => {
      if (path === "/api/media/providers") return json(providers);
      if (path === "/api/sources/sync?scope=media") return json({ active: null, last_completed: null, running: [], sources: [] });
      if (path === "/api/media/sync" && method === "POST") return json({ queued: 6 });
      return json({ detail: "unexpected request" }, 404);
    };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const path = url.pathname + url.search;
      const method = init?.method ?? "GET";
      calls.push({ path, method });
      return responder(path, method);
    }));
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("summarizes provider health and reveals textual provider details", async () => {
    const { container } = renderSummary();

    expect(await screen.findByText("6 kaynak")).toBeTruthy();
    expect(screen.getByText("4 sağlıklı")).toBeTruthy();
    expect(screen.getByText("son çekim 30 dk önce")).toBeTruthy();

    const details = container.querySelector("details[data-media-sync]") as HTMLDetailsElement;
    expect(details.open).toBe(false);
    fireEvent.click(screen.getByText("Kaynak ayrıntıları"));

    expect(details.open).toBe(true);
    expect(screen.getByText("TMDB")).toBeTruthy();
    expect(screen.getByText("Film · Dizi")).toBeTruthy();
    expect(screen.getByText("12 kayıt bulundu")).toBeTruthy();
    expect(within(screen.getByText("OpenLibrary").closest("li")!).getByText("0 kayıt bulundu")).toBeTruthy();
    expect(screen.getByText("boş")).toBeTruthy();
    expect(screen.getByText("Son hata: API anahtarı reddedildi")).toBeTruthy();
    expect(screen.getByText("Eksik ayar: media.kitsu_key")).toBeTruthy();
  });

  it("blocks duplicate pending syncs and invalidates each affected query family", async () => {
    const pending = deferred<Response>();
    responder = (path, method) => {
      if (path === "/api/media/providers") return json(providers);
      if (path === "/api/sources/sync?scope=media") return json({ active: null, last_completed: null, running: [], sources: [] });
      if (path === "/api/media/sync" && method === "POST") return pending.promise;
      return json({}, 404);
    };
    const { client } = renderSummary();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    fireEvent.click(await screen.findByText("Kaynak ayrıntıları"));
    const sync = screen.getByRole("button", { name: "Şimdi tara" }) as HTMLButtonElement;
    fireEvent.click(sync);
    expect(await screen.findByRole("button", { name: "Şimdi tara" })).toBe(sync);
    expect(sync.disabled).toBe(true);
    fireEvent.click(sync);
    expect(calls.filter((call) => call.path === "/api/media/sync" && call.method === "POST")).toHaveLength(1);

    pending.resolve(json({ queued: 6 }));
    await act(async () => {});
    const keys = invalidate.mock.calls.map(([filters]) => filters?.queryKey);
    expect(keys).toContainEqual(["media-providers"]);
    expect(keys).toContainEqual(["source-sync"]);
    expect(keys).toContainEqual(["media"]);
  });

  it("prevents offline sync writes", async () => {
    renderSummary(false);
    fireEvent.click(await screen.findByText("Kaynak ayrıntıları"));
    expect((screen.getByRole("button", { name: "Şimdi tara" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("makes provider loading and sync failures visible with retry controls", async () => {
    let providerGets = 0;
    responder = (path, method) => {
      if (path === "/api/media/providers") {
        providerGets += 1;
        return providerGets === 1 ? json({ detail: "sağlayıcılar kapalı" }, 500) : json(providers);
      }
      if (path === "/api/sources/sync?scope=media") return json({ active: null, last_completed: null, running: [], sources: [] });
      if (path === "/api/media/sync" && method === "POST") return json({ detail: "kuyruk kapalı" }, 500);
      return json({}, 404);
    };
    renderSummary();

    expect((await screen.findByRole("alert")).textContent).toContain("sağlayıcılar kapalı");
    expect(screen.queryByText("sağlıklı")).toBeNull();
    const details = document.querySelector("details[data-media-sync]") as HTMLDetailsElement;
    expect(details.open).toBe(true);
    fireEvent.click(screen.getByText("Kaynak ayrıntıları"));
    await act(async () => { details.dispatchEvent(new Event("toggle")); });
    expect(details.open).toBe(false);
    expect(details.querySelector("svg")?.className.baseVal).not.toContain("rotate-180");

    fireEvent.click(screen.getByText("Kaynak ayrıntıları"));
    expect(details.open).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Yeniden dene" }));
    expect(await screen.findByText("6 kaynak")).toBeTruthy();

    fireEvent.click(screen.getByText("Kaynak ayrıntıları"));
    fireEvent.click(screen.getByRole("button", { name: "Şimdi tara" }));
    expect((await screen.findByRole("alert")).textContent).toContain("kuyruk kapalı");
    expect((screen.getByRole("button", { name: "Şimdi tara" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("keeps provider diagnostics fully readable", async () => {
    const longError = "Sağlayıcının ayrıntılı yanıtı: geçici ağ geçidi hatası nedeniyle katalog bağlantısı kurulamadı.";
    const longSetting = "media.providers.kitsu.credentials.api_key";
    responder = (path) => path === "/api/media/providers"
      ? json([{ ...providers[5], last_error: longError, missing_settings: [longSetting] }])
      : json({ active: null, last_completed: null, running: [], sources: [] });
    renderSummary();
    await screen.findByText("1 kaynak");
    fireEvent.click(screen.getByText("Kaynak ayrıntıları"));

    const error = screen.getByText(`Son hata: ${longError}`);
    const setting = screen.getByText(`Eksik ayar: ${longSetting}`);
    expect(error.className).toContain("break-words");
    expect(error.className).not.toContain("truncate");
    expect(setting.className).toContain("break-words");
    expect(setting.getAttribute("title")).toBe(`Eksik ayar: ${longSetting}`);
  });
});
