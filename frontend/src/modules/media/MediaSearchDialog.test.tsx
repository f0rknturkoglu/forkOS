// @vitest-environment jsdom

/**
 * Katalog arama diyalogu sozlesmesi: modal katmani, ilk odak, Escape ile
 * kapanma ve ekleme sonrasi toast + "Aç" aksiyonu.
 */

import { QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { queryClient } from "@/core/queryClient";
import { MediaSearchDialog } from "./MediaSearchDialog";

const libraryItem = {
  id: "media-existing",
  title: "Dune",
  kind: "movie",
  status: "planned",
  progress: 0,
  total: 1,
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
  provider_id: "movie:99",
  provider_ids: { tmdb: "99" },
  cover_url: null,
  cover_path: null,
  backdrop_url: null,
  backdrop_path: null,
  last_synced_at: null,
  created_at: null,
  updated_at: null,
  archived_at: null,
};

const catalogHit = {
  kind: "movie",
  provider: "tmdb",
  provider_id: "movie:99",
  title: "Dune",
  subtitle: null,
  summary: null,
  total: 1,
  progress_measure: "item",
  cover: null,
  backdrop: null,
  cover_url: null,
  backdrop_url: null,
  year: 2021,
  provider_ids: { tmdb: "99" },
  meta: {},
  metadata: {},
};

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

describe("MediaSearchDialog", () => {
  let calls: string[];
  let onClose: () => void;

  function renderDialog(open = true, initialKind?: string) {
    return render(
      <QueryClientProvider client={queryClient()}>
        <ToastProvider>
          <MediaSearchDialog open={open} onClose={onClose} initialKind={initialKind} />
        </ToastProvider>
      </QueryClientProvider>,
    );
  }

  async function flush() {
    for (let round = 0; round < 3; round += 1) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
    }
  }

  beforeEach(() => {
    vi.useFakeTimers();
    queryClient().clear();
    queryClient().setDefaultOptions({ queries: { retry: false, staleTime: 0 } });
    calls = [];
    onClose = vi.fn();
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
    location.hash = "#/media";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = new URL(String(input), "http://localhost");
        const path = url.pathname + url.search;
        calls.push(path);
        if (path === "/api/media?q=dune&limit=8") return json({ items: [libraryItem], total: 1, next_cursor: null });
        if (path === "/api/media/search/global?q=dune&limit=8")
          return json({ results: [catalogHit], warnings: [], cached: false });
        if (path === "/api/media/collections") return json([]);
        if (path === "/api/media" && init?.method === "POST") return json({ ...libraryItem, id: "media-dune" }, 201);
        return json({}, 404);
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("kapalıyken hiçbir şey çizmez ve istek atmaz", () => {
    renderDialog(false);

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(calls).toEqual([]);
  });

  it("açılınca modal başlığını çizer, kapsam sekmelerini sunar ve aramaya odaklanır", () => {
    renderDialog();

    expect(screen.getByRole("dialog", { name: "Katalogda ara" })).toBeTruthy();
    expect(screen.getByRole("tablist", { name: "Katalog kapsamı" })).toBeTruthy();
    expect(document.activeElement).toBe(screen.getByRole("searchbox", { name: "Katalogda ara" }));
  });

  it("Escape ile kapanır", async () => {
    renderDialog();
    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).toHaveBeenCalled();
  });

  it("ekleme sonrası kapanır ve Aç aksiyonlu toast gösterir", async () => {
    renderDialog();
    fireEvent.change(screen.getByRole("searchbox", { name: "Katalogda ara" }), { target: { value: "dune" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    await flush();

    fireEvent.click(screen.getByRole("button", { name: "Dune kaydını ekle" }));
    fireEvent.click(screen.getByRole("button", { name: "Dune kaydını kütüphaneye ekle" }));
    await flush();

    expect(onClose).toHaveBeenCalled();
    expect(screen.getByText("Kütüphaneye eklendi")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Aç" }));
    expect(location.hash).toBe("#/media/media-dune");
  });
});
