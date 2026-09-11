// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DialogHost } from "@/core/dialog";
import { ToastProvider } from "@/core/ui";
import { MediaCollectionDetailPage } from "./MediaCollectionDetailPage";

type FetchCall = { body: unknown; method: string; path: string };

const collection = {
  id: "collection-1",
  title: "Favoriler",
  description: "Yeniden dönülecekler",
  color: null,
  position: 0,
  item_count: 2,
  covers: [],
  created_at: "2026-08-20T10:00:00Z",
  updated_at: "2026-08-20T10:00:00Z",
};

const dune = {
  id: "media-1",
  title: "Dune",
  kind: "movie",
  status: "in_progress",
  progress: 2,
  total: 10,
  score: null,
  notes: null,
  started_at: null,
  finished_at: null,
  meta: {},
  summary: null,
  release_date: null,
  progress_measure: "item",
  review: null,
  favorite: false,
  owned: false,
  ownership: {},
  monitored: false,
  provider: "tmdb",
  provider_id: "movie:1",
  provider_ids: { tmdb: "1" },
  cover_url: "https://covers.example.test/dune.jpg",
  cover_path: null,
  backdrop_url: null,
  backdrop_path: null,
  last_synced_at: null,
  created_at: null,
  updated_at: null,
  archived_at: null,
};

const solaris = { ...dune, id: "media-2", title: "Solaris", kind: "book", cover_url: null, provider: "openlibrary" };

function json(value: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

let calls: FetchCall[];
let deleted: string[];
let responder: (path: string, method: string) => Response;

function detailResponse(path: string): Response {
  const onFirstPage = !path.includes("cursor=next-1");
  const items = [dune, solaris].filter((item) => !deleted.includes(item.id));
  const page = onFirstPage ? items.slice(0, 1) : items.slice(1);
  return json({ collection, items: page, total: items.length, next_cursor: onFirstPage ? "next-1" : null });
}

function installFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const path = url.pathname + url.search;
      const method = init?.method ?? "GET";
      calls.push({ body: init?.body ? JSON.parse(String(init.body)) : undefined, method, path });
      if (method === "DELETE") {
        deleted.push(path.split("/").pop() ?? "");
        return json(null, 204);
      }
      return responder(path, method);
    }),
  );
}

function renderPage(path = "#/media/collections/collection-1") {
  location.hash = path;
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MediaCollectionDetailPage />
        <DialogHost />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("MediaCollectionDetailPage", () => {
  beforeEach(() => {
    calls = [];
    deleted = [];
    responder = (path) =>
      path.startsWith("/api/media/collections/collection-1?") ? detailResponse(path) : json({ detail: "yok" }, 404);
    installFetch();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("reads the collection from the route and loads its members", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Favoriler" })).toBeTruthy();
    expect(screen.getByText("2 kayıt")).toBeTruthy();
    expect(screen.getByText("Yeniden dönülecekler")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Dune detayını aç" }).getAttribute("href")).toBe("#/media/media-1");
    expect(calls.some((call) => call.path === "/api/media/collections/collection-1?sort=updated&limit=48")).toBe(true);

    // Uzak kapak gizlilik için yerel önbellek üzerinden gelir.
    const cover = screen.getByRole("link", { name: "Dune detayını aç" }).querySelector("img");
    expect(cover?.getAttribute("src")).toBe(
      `/api/media/artwork/proxy?url=${encodeURIComponent("https://covers.example.test/dune.jpg")}`,
    );
  });

  it("removes a member with a labelled button", async () => {
    const user = userEvent.setup();
    renderPage();

    const button = await screen.findByRole("button", { name: "Dune kaydını koleksiyondan çıkar" });
    await user.click(button);

    await waitFor(() =>
      expect(calls.map((call) => `${call.method} ${call.path}`)).toContain(
        "DELETE /api/media/collections/collection-1/items/media-1",
      ),
    );
    await waitFor(() => expect(screen.queryByRole("link", { name: "Dune detayını aç" })).toBeNull());
  });

  it("sends the search term and sort order as list parameters", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByRole("heading", { name: "Favoriler" });
    await user.type(screen.getByRole("textbox", { name: "Koleksiyonda ara" }), "dune");
    await waitFor(() =>
      expect(
        calls.some(
          (call) => call.path.includes("/api/media/collections/collection-1?") && call.path.includes("q=dune"),
        ),
      ).toBe(true),
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Sıralama" }), "title");
    await waitFor(() =>
      expect(calls.some((call) => call.path.includes("q=dune") && call.path.includes("sort=title"))).toBe(true),
    );
  });

  it("loads the next cursor page on demand", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByRole("link", { name: "Dune detayını aç" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Solaris detayını aç" })).toBeNull();

    await user.click(screen.getByRole("button", { name: "Daha fazla yükle" }));

    expect(await screen.findByRole("link", { name: "Solaris detayını aç" })).toBeTruthy();
    await waitFor(() => expect(calls.some((call) => call.path.includes("cursor=next-1"))).toBe(true));
  });

  it("explains a missing collection and links back to the library", async () => {
    responder = () => json({ detail: "bulunamadı" }, 404);
    renderPage("#/media/collections/kayip-koleksiyon");

    expect(await screen.findByText("Koleksiyon bulunamadı")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Koleksiyonlara dön" }).getAttribute("href")).toBe("#/media/collections");
    expect(screen.getByRole("link", { name: "Medya kütüphanesine dön" }).getAttribute("href")).toBe("#/media");
  });
});
