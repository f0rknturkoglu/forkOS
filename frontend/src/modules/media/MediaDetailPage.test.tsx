// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { allRoutes } from "@/core/registry";
import "./index";
import { MediaDetailPage } from "./MediaDetailPage";

const item = {
  archived_at: null,
  backdrop_path: null,
  backdrop_url: null,
  cover_path: null,
  cover_url: "https://images.example.test/dune.jpg",
  created_at: "2026-08-20T10:00:00Z",
  favorite: false,
  finished_at: null,
  id: "media-1",
  kind: "show",
  last_synced_at: "2026-08-23T10:00:00Z",
  meta: { original_title: "Dune: Prophecy" },
  monitored: true,
  notes: "İkinci sezon",
  owned: true,
  ownership: {},
  progress: 3,
  progress_measure: "episode",
  provider: "tmdb",
  provider_id: "tv:42",
  provider_ids: { tmdb: "42" },
  release_date: "2026-01-01",
  review: null,
  score: 8,
  started_at: "2026-08-01T10:00:00Z",
  status: "in_progress",
  summary: "Bir bilim kurgu dizisi.",
  title: "Dune: Prophecy",
  total: 8,
  updated_at: "2026-08-23T10:00:00Z",
};

const detail = { item, units: [], cycles: [], consumptions: [], collections: [] };
type FetchCall = { body: Record<string, unknown>; method: string; path: string };

function renderPage(path = "#/media/media-1") {
  location.hash = path;
  fireEvent(window, new HashChangeEvent("hashchange"));
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MediaDetailPage />
    </QueryClientProvider>,
  );
}

describe("media detail page", () => {
  let calls: FetchCall[];
  let responder: (path: string, method: string) => Response | Promise<Response>;

  beforeEach(() => {
    calls = [];
    responder = (_path, method) => new Response(JSON.stringify(method === "GET" ? detail : item), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: { getItem: () => null, setItem: vi.fn(), removeItem: vi.fn() },
    });
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), "http://localhost").pathname;
      const method = init?.method ?? "GET";
      calls.push({
        body: init?.body ? JSON.parse(String(init.body)) : {},
        method,
        path,
      });
      return responder(path, method);
    }));
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("registers the encoded dynamic detail route after the media index", () => {
    const paths = allRoutes().filter((route) => route.path === "/media" || route.path.startsWith("/media/:"));
    expect(paths.map((route) => route.path)).toEqual(["/media", "/media/:id"]);
  });

  it("loads a readable two-column detail with progress and source actions", async () => {
    renderPage("#/media/media%2Fone");

    expect(await screen.findByRole("heading", { name: "Dune: Prophecy" })).toBeTruthy();
    expect(calls[0].path).toBe("/api/media/media%2Fone");
    expect(screen.getByRole("img", { name: "Dune: Prophecy kapağı" }).className).toContain("w-full");
    expect(screen.getByText("İzleniyor")).toBeTruthy();
    expect(screen.getByText("3 / 8 bölüm")).toBeTruthy();
    expect(screen.getByRole("button", { name: "İlerlemeyi ayarla" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Tamamlandı olarak işaretle" })).toBeTruthy();
    expect(screen.getByText("8 / 10")).toBeTruthy();
    expect(screen.getByText("İkinci sezon")).toBeTruthy();
    expect(screen.getByRole("link", { name: /TMDB/ })).toBeTruthy();
    expect(screen.getByRole("link", { name: /IMDb/ })).toBeTruthy();
  });

  it("patches only score and notes metadata", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });

    expect(screen.queryByRole("spinbutton", { name: "Puan" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Puan ve notu düzenle" }));
    const score = screen.getByRole("spinbutton", { name: "Puan" });
    await user.clear(score);
    await user.type(score, "9");
    const notes = screen.getByRole("textbox", { name: "Notlar" });
    await user.clear(notes);
    await user.type(notes, "Yeni not");
    await user.click(screen.getByRole("button", { name: "Puan ve notu kaydet" }));

    await waitFor(() => expect(calls.some((call) => call.method === "PATCH")).toBe(true));
    const patches = calls.filter((call) => call.method === "PATCH");
    expect(patches).toHaveLength(1);
    expect(patches[0]).toEqual({
      method: "PATCH",
      path: "/api/media/media-1",
      body: { score: 9, notes: "Yeni not" },
    });
    expect(patches.some(({ body }) => "progress" in body || body.status === "completed")).toBe(false);
  });

  it("keeps every detail write disabled offline while still loading the detail", async () => {
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: false });
    renderPage();

    expect(await screen.findByRole("heading", { name: "Dune: Prophecy" })).toBeTruthy();
    expect((screen.getByRole("button", { name: "Sonraki bölüm" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "İlerlemeyi ayarla" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Tamamlandı olarak işaretle" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Puan ve notu düzenle" }) as HTMLButtonElement).disabled).toBe(true);
    expect(calls.some((call) => call.method === "GET")).toBe(true);
    expect(calls.some((call) => call.method !== "GET")).toBe(false);
  });

  it("restores the previous document title after leaving the detail", async () => {
    document.title = "forkOS";
    const view = renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });
    await waitFor(() => expect(document.title).toBe("Dune: Prophecy — forkOS"));

    view.unmount();
    expect(document.title).toBe("forkOS");
  });

  it("retries a terminal detail GET failure", async () => {
    let gets = 0;
    responder = (_path, method) => {
      if (method !== "GET") return new Response(JSON.stringify(item), { status: 200 });
      gets += 1;
      return gets === 1
        ? new Response("detail unavailable", { status: 500 })
        : new Response(JSON.stringify(detail), { status: 200, headers: { "Content-Type": "application/json" } });
    };
    const user = userEvent.setup();
    renderPage();

    expect((await screen.findByRole("alert")).textContent).toContain("detail unavailable");
    await user.click(screen.getByRole("button", { name: "Yeniden dene" }));
    expect(await screen.findByRole("heading", { name: "Dune: Prophecy" })).toBeTruthy();
    expect(gets).toBe(2);
  });

  it("blocks duplicate pending PATCHes and preserves metadata after rejection for retry", async () => {
    let patchCount = 0;
    let rejectPatch!: (response: Response) => void;
    responder = (_path, method) => {
      if (method === "GET") {
        return new Response(JSON.stringify(detail), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      patchCount += 1;
      if (patchCount === 1) return new Promise<Response>((resolve) => { rejectPatch = resolve; });
      return new Response(JSON.stringify(item), { status: 200, headers: { "Content-Type": "application/json" } });
    };
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Dune: Prophecy" });
    await user.click(screen.getByRole("button", { name: "Puan ve notu düzenle" }));
    const score = screen.getByRole("spinbutton", { name: "Puan" }) as HTMLInputElement;
    const notes = screen.getByRole("textbox", { name: "Notlar" }) as HTMLTextAreaElement;
    await user.clear(score);
    await user.type(score, "9");
    await user.clear(notes);
    await user.type(notes, "Retry notu");
    const submit = screen.getByRole("button", { name: "Puan ve notu kaydet" }) as HTMLButtonElement;
    fireEvent.click(submit);
    await waitFor(() => expect(patchCount).toBe(1));
    expect(submit.disabled).toBe(true);
    fireEvent.click(submit);
    expect(patchCount).toBe(1);

    rejectPatch(new Response("metadata rejected", { status: 500 }));
    expect((await screen.findByRole("alert")).textContent).toContain("metadata rejected");
    expect(score.value).toBe("9");
    expect(notes.value).toBe("Retry notu");

    await user.click(submit);
    await waitFor(() => expect(patchCount).toBe(2));
  });
});
