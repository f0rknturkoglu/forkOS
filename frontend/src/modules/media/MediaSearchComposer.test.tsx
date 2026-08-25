// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MediaSearchComposer, providerCreateBody } from "./MediaSearchComposer";

const KINDS = ["movie", "show", "anime", "manga", "book", "audiobook", "podcast", "music", "game"];
const libraryItem = {
  id: "media-prophecy", title: "Dune: Prophecy", kind: "show", status: "in_progress",
  progress: 3, total: 8, score: null, notes: null, started_at: null, finished_at: null,
  meta: {}, summary: null, release_date: null, progress_measure: "episode", review: null,
  favorite: false, owned: false, ownership: {}, monitored: false, provider: "tmdb",
  provider_id: "tv:42", provider_ids: { tmdb: "42" }, cover_url: null, cover_path: null,
  backdrop_url: null, backdrop_path: null, last_synced_at: null, created_at: null,
  updated_at: null, archived_at: null,
};
const catalogHit = {
  kind: "movie", provider: "tmdb", provider_id: "movie:99", title: "Dune",
  subtitle: "2021 filmi", summary: "Arrakis", total: 1, progress_measure: "item",
  cover: null, backdrop: null, cover_url: "https://image/dune.jpg", backdrop_url: null,
  year: 2021, provider_ids: { tmdb: "99" }, meta: { tmdb_type: "movie" }, metadata: { ignored: true },
};
const sameIdDifferentKind = { ...catalogHit, kind: "show", title: "Dune: Sisterhood" };
const foundationHit = { ...catalogHit, provider_id: "movie:42", title: "Foundation" };

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => { resolve = next; });
  return { promise, resolve };
}

function renderComposer(online = true) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MediaSearchComposer online={online} onAdded={vi.fn()} />
    </QueryClientProvider>,
  );
}

describe("MediaSearchComposer", () => {
  let calls: { path: string; method: string; body: unknown }[];
  let responder: (path: string, method: string) => Response | Promise<Response>;
  let posts: number;
  let duplicate: Record<string, unknown>;

  async function search(term: string) {
    fireEvent.change(screen.getByRole("searchbox", { name: "Tüm medyada ara" }), { target: { value: term } });
    await act(async () => { await vi.advanceTimersByTimeAsync(250); });
    await act(async () => { await vi.advanceTimersByTimeAsync(0); });
  }

  beforeEach(() => {
    vi.useFakeTimers();
    calls = [];
    posts = 0;
    duplicate = { detail: "Bu provider kaydı kütüphanede zaten var", existing_id: "media-existing" };
    responder = (path, method) => {
      if (path === "/api/media?q=dune&limit=8") return json({ items: [libraryItem], total: 1, next_cursor: null });
      if (path === "/api/media/search/global?q=dune") return json({ results: [catalogHit], warnings: [] });
      if (path === "/api/media?q=foundation&limit=8") return json({ items: [], total: 0, next_cursor: null });
      if (path === "/api/media/search/global?q=foundation") return json({ results: [foundationHit], warnings: [] });
      if (path === "/api/media" && method === "POST") {
        posts += 1;
        return posts === 1 ? json({ ...libraryItem, id: "media-dune", title: "Dune", kind: "movie" }, 201) : json(duplicate, 409);
      }
      return json({ items: [], total: 0, next_cursor: null });
    };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const path = url.pathname + url.search;
      const method = init?.method ?? "GET";
      const body = init?.body ? JSON.parse(String(init.body)) : undefined;
      calls.push({ path, method, body });
      return responder(path, method);
    }));
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("does not search globally for a one-character term", async () => {
    renderComposer();
    await search("d");
    expect(calls.some(({ path }) => path.startsWith("/api/media/search/global"))).toBe(false);
  });

  it("searches library and catalog after the 250ms boundary, then adds provider hits", async () => {
    renderComposer();
    await search("dune");
    expect(screen.getByRole("heading", { name: "Kütüphanende" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Katalog sonuçları" })).toBeTruthy();
    expect(screen.getAllByRole("heading", { level: 3 }).map((node) => node.textContent)).toEqual(["Dune: Prophecy", "Dune"]);
    expect(screen.getByText("Film")).toBeTruthy();
    expect(screen.getByText("tmdb")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    await act(async () => {});
    expect(calls.find(({ path, method }) => path === "/api/media" && method === "POST")?.body).toMatchObject({
      source: "provider", title: "Dune", kind: "movie", provider: "tmdb", provider_id: "movie:99",
      provider_ids: { tmdb: "99" }, cover_url: "https://image/dune.jpg",
    });
  });

  it("keeps cross-kind provider IDs as separate stable catalog rows", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    responder = (path, method) => path === "/api/media/search/global?q=dune"
      ? json({ results: [catalogHit, sameIdDifferentKind], warnings: [] })
      : path === "/api/media?q=dune&limit=8" ? json({ items: [], total: 0, next_cursor: null }) : json({}, method === "POST" ? 201 : 200);
    renderComposer();
    await search("dune");
    expect(screen.getAllByRole("heading", { level: 3 }).map((node) => node.textContent)).toEqual(["Dune", "Dune: Sisterhood"]);
    expect(consoleError.mock.calls.some(([message]) => String(message).includes("same key"))).toBe(false);
    consoleError.mockRestore();
  });

  it("keeps catalog results visible when the library query fails", async () => {
    responder = (path) => path === "/api/media?q=dune&limit=8"
      ? json({ detail: "library unavailable" }, 500)
      : path === "/api/media/search/global?q=dune" ? json({ results: [catalogHit], warnings: [] }) : json({});
    renderComposer();
    await search("dune");
    expect(screen.getByRole("alert").textContent).toContain("Kütüphane");
    expect(screen.getByRole("heading", { level: 3, name: "Dune" })).toBeTruthy();
  });

  it("keeps library results visible when the catalog query fails", async () => {
    responder = (path) => path === "/api/media?q=dune&limit=8"
      ? json({ items: [libraryItem], total: 1, next_cursor: null })
      : path === "/api/media/search/global?q=dune" ? json({ detail: "catalog unavailable" }, 500) : json({});
    renderComposer();
    await search("dune");
    expect(screen.getByRole("alert").textContent).toContain("Katalog");
    expect(screen.getByRole("heading", { level: 3, name: "Dune: Prophecy" })).toBeTruthy();
  });

  it("announces non-409 add failures", async () => {
    responder = (path, method) => path === "/api/media?q=dune&limit=8"
      ? json({ items: [], total: 0, next_cursor: null })
      : path === "/api/media/search/global?q=dune" ? json({ results: [catalogHit], warnings: [] })
      : path === "/api/media" && method === "POST" ? json({ detail: "write unavailable" }, 500) : json({});
    renderComposer();
    await search("dune");
    fireEvent.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    await act(async () => {});
    expect(screen.getByRole("alert").textContent).toContain("Eklenemedi");
  });

  it("opens the existing item after a duplicate provider response", async () => {
    renderComposer();
    await search("dune");
    fireEvent.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    await act(async () => {});
    fireEvent.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    await act(async () => {});
    expect(screen.getByRole("status").textContent).toContain("Kütüphanede aç");
    expect(screen.getByRole("link", { name: "Kütüphanede aç" }).getAttribute("href")).toBe("#/media/media-existing");
  });

  it("falls back to the library instead of treating a duplicate title as an item ID", async () => {
    duplicate = { detail: "Bu provider kaydı kütüphanede zaten var" };
    renderComposer();
    await search("dune");
    fireEvent.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    await act(async () => {});
    fireEvent.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    await act(async () => {});
    expect(screen.getByRole("link", { name: "Kütüphanede aç" }).getAttribute("href")).toBe("#/media");
  });

  it("does not show an older in-flight duplicate below a newer search term", async () => {
    const pending = deferred<Response>();
    responder = (path, method) => path === "/api/media?q=dune&limit=8"
      ? json({ items: [], total: 0, next_cursor: null })
      : path === "/api/media/search/global?q=dune" ? json({ results: [catalogHit], warnings: [] })
      : path === "/api/media?q=foundation&limit=8" ? json({ items: [], total: 0, next_cursor: null })
      : path === "/api/media/search/global?q=foundation" ? json({ results: [foundationHit], warnings: [] })
      : path === "/api/media" && method === "POST" ? pending.promise : json({});
    renderComposer();
    await search("dune");
    fireEvent.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    await search("foundation");
    pending.resolve(json({ detail: "Bu provider kaydı kütüphanede zaten var", existing_id: "media-existing" }, 409));
    await act(async () => {});
    expect(screen.queryByRole("link", { name: "Kütüphanede aç" })).toBeNull();
    expect(screen.getByRole("heading", { level: 3, name: "Foundation" })).toBeTruthy();
  });

  it("does not show an older non-conflict add error below a newer search term", async () => {
    const pending = deferred<Response>();
    responder = (path, method) => path === "/api/media?q=dune&limit=8"
      ? json({ items: [], total: 0, next_cursor: null })
      : path === "/api/media/search/global?q=dune" ? json({ results: [catalogHit], warnings: [] })
      : path === "/api/media?q=foundation&limit=8" ? json({ items: [], total: 0, next_cursor: null })
      : path === "/api/media/search/global?q=foundation" ? json({ results: [foundationHit], warnings: [] })
      : path === "/api/media" && method === "POST" ? pending.promise : json({});
    renderComposer();
    await search("dune");
    fireEvent.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    await search("foundation");
    pending.resolve(json({ detail: "write unavailable" }, 500));
    await act(async () => {});
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByRole("heading", { level: 3, name: "Foundation" })).toBeTruthy();
  });

  it("only links to Settings when every media kind is unavailable", async () => {
    responder = (path) => path === "/api/media?q=dune&limit=8"
      ? json({ items: [], total: 0, next_cursor: null })
      : path === "/api/media/search/global?q=dune" ? json({ results: [], warnings: [{ provider: "tmdb", kind: "movie", message: "TMDB kapalı" }] }) : json({});
    renderComposer();
    await search("dune");
    expect(screen.getByRole("status").textContent).toContain("TMDB kapalı");
    expect(screen.queryByRole("link", { name: "Medya bağlantılarını aç" })).toBeNull();
  });

  it("links to Settings after every media kind reports unavailable", async () => {
    responder = (path) => path === "/api/media?q=dune&limit=8"
      ? json({ items: [], total: 0, next_cursor: null })
      : path === "/api/media/search/global?q=dune"
        ? json({ results: [], warnings: KINDS.map((kind) => ({ provider: "test", kind, message: `${kind} kapalı` })) }) : json({});
    renderComposer();
    await search("dune");
    expect(screen.getByRole("link", { name: "Medya bağlantılarını aç" }).getAttribute("href"))
      .toBe("#/settings?section=media-links");
  });

  it("disables provider adds while offline", async () => {
    renderComposer(false);
    await search("dune");
    expect((screen.getByRole("button", { name: "Dune kütüphaneye ekle" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("converts provider metadata to the canonical media create request", () => {
    expect(providerCreateBody(catalogHit)).toEqual({
      source: "provider", title: "Dune", kind: "movie", provider: "tmdb", provider_id: "movie:99",
      provider_ids: { tmdb: "99" }, summary: "Arrakis", total: 1, progress_measure: "item",
      cover_url: "https://image/dune.jpg", backdrop_url: null, meta: { tmdb_type: "movie" },
    });
  });
});
