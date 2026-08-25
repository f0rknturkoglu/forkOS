// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MediaSearchComposer, providerCreateBody } from "./MediaSearchComposer";

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

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderComposer(online = true) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MediaSearchComposer online={online} onAdded={vi.fn()} />
    </QueryClientProvider>,
  );
}

describe("MediaSearchComposer", () => {
  let calls: { path: string; method: string; body: unknown }[];
  let posts: number;
  let duplicate: Record<string, unknown>;

  beforeEach(() => {
    calls = [];
    posts = 0;
    duplicate = { detail: "Bu provider kaydı kütüphanede zaten var", existing_id: "media-existing" };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const path = url.pathname + url.search;
      const method = init?.method ?? "GET";
      const body = init?.body ? JSON.parse(String(init.body)) : undefined;
      calls.push({ path, method, body });
      if (path === "/api/media?q=dune&limit=8") return json({ items: [libraryItem], total: 1, next_cursor: null });
      if (path === "/api/media/search/global?q=dune") return json({ results: [catalogHit], warnings: [] });
      if (path === "/api/media" && method === "POST") {
        posts += 1;
        return posts === 1
          ? json({ ...libraryItem, id: "media-dune", title: "Dune", kind: "movie" }, 201)
          : json(duplicate, 409);
      }
      return json({ items: [], total: 0, next_cursor: null });
    }));
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("does not search globally for a one-character term", async () => {
    vi.useFakeTimers();
    renderComposer();
    fireEvent.change(screen.getByRole("searchbox", { name: "Tüm medyada ara" }), { target: { value: "d" } });
    await vi.advanceTimersByTimeAsync(250);
    expect(calls.some(({ path }) => path.startsWith("/api/media/search/global"))).toBe(false);
  });

  it("searches library and catalog after a two-character debounce, then adds provider hits", async () => {
    const user = userEvent.setup();
    renderComposer();

    await user.type(screen.getByRole("searchbox", { name: "Tüm medyada ara" }), "dune");
    await new Promise((resolve) => setTimeout(resolve, 250));
    await screen.findByRole("heading", { name: "Kütüphanende" });
    await screen.findByRole("heading", { name: "Katalog sonuçları" });
    const headings = screen.getAllByRole("heading", { level: 3 });
    expect(headings.map((node) => node.textContent)).toEqual(["Dune: Prophecy", "Dune"]);
    expect(screen.getByText("Film")).toBeTruthy();
    expect(screen.getByText("tmdb")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    const post = calls.find(({ path, method }) => path === "/api/media" && method === "POST");
    expect(post?.body).toMatchObject({
      source: "provider",
      title: "Dune",
      kind: "movie",
      provider: "tmdb",
      provider_id: "movie:99",
      provider_ids: { tmdb: "99" },
      cover_url: "https://image/dune.jpg",
    });
  });

  it("opens the existing item after a duplicate provider response", async () => {
    const user = userEvent.setup();
    renderComposer();
    await user.type(screen.getByRole("searchbox", { name: "Tüm medyada ara" }), "dune");
    await new Promise((resolve) => setTimeout(resolve, 250));
    await screen.findByRole("button", { name: "Dune kütüphaneye ekle" });

    await user.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    await user.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    expect((await screen.findByRole("link", { name: "Kütüphanede aç" })).getAttribute("href"))
      .toBe("#/media/media-existing");
  });

  it("falls back to a title focus link when a duplicate omits its existing ID", async () => {
    duplicate = { detail: "Bu provider kaydı kütüphanede zaten var" };
    const user = userEvent.setup();
    renderComposer();
    await user.type(screen.getByRole("searchbox", { name: "Tüm medyada ara" }), "dune");
    await new Promise((resolve) => setTimeout(resolve, 250));
    await screen.findByRole("button", { name: "Dune kütüphaneye ekle" });

    await user.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    await user.click(screen.getByRole("button", { name: "Dune kütüphaneye ekle" }));
    expect((await screen.findByRole("link", { name: "Kütüphanede aç" })).getAttribute("href"))
      .toBe("#/media?focus=Dune");
  });

  it("disables provider adds while offline", async () => {
    const user = userEvent.setup();
    renderComposer(false);
    await user.type(screen.getByRole("searchbox", { name: "Tüm medyada ara" }), "dune");
    await new Promise((resolve) => setTimeout(resolve, 250));
    expect((await screen.findByRole("button", { name: "Dune kütüphaneye ekle" }) as HTMLButtonElement).disabled)
      .toBe(true);
  });

  it("converts provider metadata to the canonical media create request", () => {
    expect(providerCreateBody(catalogHit)).toEqual({
      source: "provider", title: "Dune", kind: "movie", provider: "tmdb", provider_id: "movie:99",
      provider_ids: { tmdb: "99" }, summary: "Arrakis", total: 1, progress_measure: "item",
      cover_url: "https://image/dune.jpg", backdrop_url: null, meta: { tmdb_type: "movie" },
    });
  });
});
