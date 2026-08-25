// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MediaSyncSummary } from "./MediaSyncSummary";

const providers = [
  {
    id: "tmdb", kinds: ["movie", "show"], ready: true, missing_settings: [],
    last_run_at: "2026-08-25T07:30:00.000Z", last_status: "ok", last_error: null,
    capabilities: { search: true, details: true, units: true, upcoming: true, cache_artwork: true, requires_settings: [] },
  },
  {
    id: "anilist", kinds: ["anime", "manga"], ready: true, missing_settings: [],
    last_run_at: "2026-08-25T07:20:00.000Z", last_status: "ok", last_error: null,
    capabilities: { search: true, details: true, units: true, upcoming: true, cache_artwork: false, requires_settings: [] },
  },
  {
    id: "openlibrary", kinds: ["book"], ready: true, missing_settings: [],
    last_run_at: "2026-08-25T07:00:00.000Z", last_status: "empty", last_error: null,
    capabilities: { search: true, details: true, units: false, upcoming: false, cache_artwork: true, requires_settings: [] },
  },
  {
    id: "itunes", kinds: ["music", "podcast"], ready: true, missing_settings: [],
    last_run_at: "2026-08-25T06:30:00.000Z", last_status: "ok", last_error: null,
    capabilities: { search: true, details: true, units: false, upcoming: false, cache_artwork: false, requires_settings: [] },
  },
  {
    id: "igdb", kinds: ["game"], ready: true, missing_settings: [],
    last_run_at: "2026-08-25T06:00:00.000Z", last_status: "ok", last_error: null,
    capabilities: { search: true, details: true, units: false, upcoming: true, cache_artwork: true, requires_settings: [] },
  },
  {
    id: "kitsu", kinds: ["anime"], ready: true, missing_settings: ["media.kitsu_key"],
    last_run_at: "2026-08-25T05:00:00.000Z", last_status: "error", last_error: "API anahtarı reddedildi",
    capabilities: { search: true, details: true, units: true, upcoming: false, cache_artwork: false, requires_settings: ["media.kitsu_key"] },
  },
];

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

function renderSummary(online = true) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MediaSyncSummary online={online} />
    </QueryClientProvider>,
  );
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
    expect(screen.getByText("5 sağlıklı")).toBeTruthy();
    expect(screen.getByText("son çekim 30 dk önce")).toBeTruthy();

    const details = container.querySelector("details[data-media-sync]") as HTMLDetailsElement;
    expect(details.open).toBe(false);
    fireEvent.click(screen.getByText("Kaynak ayrıntıları"));

    expect(details.open).toBe(true);
    expect(screen.getByText("TMDB")).toBeTruthy();
    expect(screen.getByText("Film · Dizi")).toBeTruthy();
    expect(screen.getByText("boş")).toBeTruthy();
    expect(screen.getByText("Son hata: API anahtarı reddedildi")).toBeTruthy();
    expect(screen.getByText("Eksik ayar: media.kitsu_key")).toBeTruthy();
  });

  it("queues all providers from the disclosure and prevents offline writes", async () => {
    renderSummary();
    fireEvent.click(await screen.findByText("Kaynak ayrıntıları"));
    fireEvent.click(screen.getByRole("button", { name: "Şimdi tara" }));
    await act(async () => {});
    expect(calls).toContainEqual({ path: "/api/media/sync", method: "POST" });

    cleanup();
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
    fireEvent.click(screen.getByRole("button", { name: "Yeniden dene" }));
    expect(await screen.findByText("6 kaynak")).toBeTruthy();

    fireEvent.click(screen.getByText("Kaynak ayrıntıları"));
    fireEvent.click(screen.getByRole("button", { name: "Şimdi tara" }));
    expect((await screen.findByRole("alert")).textContent).toContain("kuyruk kapalı");
    expect((screen.getByRole("button", { name: "Şimdi tara" }) as HTMLButtonElement).disabled).toBe(false);
  });
});
