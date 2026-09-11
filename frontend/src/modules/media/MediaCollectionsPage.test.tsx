// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DialogHost } from "@/core/dialog";
import { ToastProvider } from "@/core/ui";
import { MediaCollectionsPage } from "./MediaCollectionsPage";

type FetchCall = { body: unknown; method: string; path: string };

const favorites = {
  id: "collection-1",
  title: "Favoriler",
  description: "Yeniden dönülecekler",
  color: "#1f5fd0",
  position: 0,
  item_count: 12,
  covers: ["/api/media/assets/dune.webp", "https://covers.example.test/solaris.jpg"],
  created_at: "2026-08-20T10:00:00Z",
  updated_at: "2026-08-20T10:00:00Z",
};

const emptyShelf = {
  id: "collection-2",
  title: "Boş raf",
  description: null,
  color: null,
  position: 1,
  item_count: 0,
  covers: [],
  created_at: null,
  updated_at: null,
};

function json(value: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

let calls: FetchCall[];
let responder: (path: string, method: string) => Response;

function installFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const path = url.pathname + url.search;
      const method = init?.method ?? "GET";
      calls.push({ body: init?.body ? JSON.parse(String(init.body)) : undefined, method, path });
      return responder(path, method);
    }),
  );
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MediaCollectionsPage />
        <DialogHost />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("MediaCollectionsPage", () => {
  beforeEach(() => {
    calls = [];
    responder = () => json([favorites, emptyShelf]);
    installFetch();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders cover mosaics, record counts and the detail link per collection", async () => {
    const { container } = renderPage();

    const link = await screen.findByRole("link", { name: "Favoriler koleksiyonunu aç" });
    expect(link.getAttribute("href")).toBe("#/media/collections/collection-1");

    // Yerel asset doğrudan, uzak kapak yerel önbellek üzerinden servis edilir (gizlilik).
    const sources = [...link.querySelectorAll("img")].map((image) => image.getAttribute("src"));
    expect(sources).toEqual([
      "/api/media/assets/dune.webp",
      `/api/media/artwork/proxy?url=${encodeURIComponent("https://covers.example.test/solaris.jpg")}`,
    ]);

    expect(screen.getByText(/^12 kayıt · /)).toBeTruthy();
    expect(screen.getByText("0 kayıt")).toBeTruthy();
    expect(screen.getByText("Yeniden dönülecekler")).toBeTruthy();

    // Kapaksız koleksiyon yer tutucuya düşer: toplam görsel sayısı yalnızca ilk kartın kapakları.
    expect(container.querySelectorAll("img")).toHaveLength(2);

    const dot = link.querySelector<HTMLElement>("span[aria-hidden='true'][style]");
    expect(dot?.style.background).toBe("rgb(31, 95, 208)");
  });

  it("deletes a collection only after a confirmation that keeps the records", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: "Favoriler koleksiyonunu sil" }));
    expect(await screen.findByText(/koleksiyon üyelikleri silinecek; kayıtlar kalır/)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Koleksiyonu sil" }));

    await waitFor(() =>
      expect(calls.map((call) => `${call.method} ${call.path}`)).toContain(
        "DELETE /api/media/collections/collection-1",
      ),
    );
  });

  it("shows a clean empty state without smart-collection hints", async () => {
    responder = () => json([]);
    renderPage();

    expect(await screen.findByText("Henüz koleksiyon yok.")).toBeTruthy();
    expect(screen.queryByText(/Akıllı koleksiyon/)).toBeNull();
  });
});
