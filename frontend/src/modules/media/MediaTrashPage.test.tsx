// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DialogHost } from "@/core/dialog";
import type { MediaItem } from "@/core/types";
import { MediaTrashPage } from "./MediaTrashPage";

const trashed = {
  id: "media-1",
  title: "Whitebeard Pirates: Çok Uzun Bir Kayıt Başlığı",
  kind: "anime",
  status: "dropped",
  favorite: false,
  monitored: false,
  owned: false,
  provider: null,
  meta: { source: "rawg" },
  cover_path: "/api/media/assets/one-piece.webp",
  cover_url: null,
  archived_at: "2026-08-25T10:00:00Z",
} satisfies MediaItem;

type FetchCall = { method: string; url: string };

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MediaTrashPage />
      <DialogHost />
    </QueryClientProvider>,
  );
}

describe("media trash page", () => {
  let calls: FetchCall[];
  let items: MediaItem[];
  let permanentStatus: number;

  beforeEach(() => {
    calls = [];
    items = [trashed];
    permanentStatus = 204;
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: { getItem: () => null, setItem: vi.fn(), removeItem: vi.fn() },
    });
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        calls.push({ method: init?.method ?? "GET", url });
        if (init?.method === "DELETE") {
          return new Response(permanentStatus === 204 ? null : JSON.stringify({ detail: "Önce çöpe taşınmalı" }), {
            status: permanentStatus,
            headers: { "Content-Type": "application/json" },
          });
        }
        return new Response(JSON.stringify({ items, total: items.length, next_cursor: null }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders a compact row with cover, kind, legacy provider and archive date", async () => {
    renderPage();

    expect(await screen.findByText(trashed.title)).toBeTruthy();
    expect(calls[0].url).toBe("/api/media?trashed=true");
    // Kucuk kapak (40x56) ve basligin tasmamasi icin truncate + title.
    const img = (await screen.findByAltText("")) as HTMLImageElement;
    expect(new URL(img.src).pathname).toBe("/api/media/assets/one-piece.webp");
    expect(img.className).toContain("h-14");
    expect(img.className).toContain("w-10");
    const title = screen.getByText(trashed.title);
    expect(title.className).toContain("truncate");
    expect(title.getAttribute("title")).toBe(trashed.title);

    const row = title.closest("li") as HTMLElement;
    expect(within(row).getByText("Anime")).toBeTruthy();
    expect(within(row).getByText("RAWG")).toBeTruthy();
    expect(
      within(row).getByText(
        new Date(trashed.archived_at as string).toLocaleDateString("tr-TR", {
          day: "numeric",
          month: "long",
          year: "numeric",
        }),
      ),
    ).toBeTruthy();
  });

  it("restores a row without repeating the media title in the visible label", async () => {
    const user = userEvent.setup();
    renderPage();

    const restore = await screen.findByRole("button", { name: `${trashed.title} kaydını geri yükle` });
    expect(restore.textContent?.trim()).toBe("Geri yükle");
    await user.click(restore);
    await waitFor(() => expect(calls).toContainEqual({ method: "POST", url: "/api/media/media-1/restore" }));
  });

  it("permanently deletes only through a confirmation that names the record", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: `${trashed.title} kaydını kalıcı sil` }));
    expect(await screen.findByText("Bu işlem geri alınamaz.")).toBeTruthy();
    expect(screen.getAllByText(trashed.title).length).toBeGreaterThan(1);

    await user.click(screen.getByRole("button", { name: "Vazgeç" }));
    expect(calls.some((call) => call.method === "DELETE")).toBe(false);

    await user.click(screen.getByRole("button", { name: `${trashed.title} kaydını kalıcı sil` }));
    await user.click(await screen.findByRole("button", { name: "Kalıcı sil" }));
    await waitFor(() => expect(calls).toContainEqual({ method: "DELETE", url: "/api/media/media-1/permanent" }));
  });

  it("reports a permanent delete failure as an alert", async () => {
    permanentStatus = 409;
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: `${trashed.title} kaydını kalıcı sil` }));
    await user.click(await screen.findByRole("button", { name: "Kalıcı sil" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Kalıcı silinemedi: Önce çöpe taşınmalı");
  });

  it("shows the empty state when the trash is empty", async () => {
    items = [];
    renderPage();

    expect(await screen.findByText("Çöp kutusu boş.")).toBeTruthy();
  });
});
