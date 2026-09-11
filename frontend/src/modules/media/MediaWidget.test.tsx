// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { todayKey } from "@/lib/date";
import type { MediaItem } from "@/core/types";
import { MediaContinueWidget } from "./MediaWidget";

type FetchCall = { body: Record<string, unknown>; method: string; url: string };

const coverItem = {
  id: "media-1",
  title: "Dune",
  kind: "movie",
  status: "in_progress",
  progress: 0.5,
  total: 1,
  progress_measure: "item",
  // Backend sync._cache_artwork cover_path'i tam "/api/media/assets/<dosya>" yoluyla saklar.
  cover_path: "/api/media/assets/dune.webp",
  cover_url: null,
} as MediaItem;

const page = { items: [coverItem], total: 1, next_cursor: null };

function renderWidget() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MediaContinueWidget />
    </QueryClientProvider>,
  );
}

describe("media continue widget covers", () => {
  let calls: FetchCall[];
  let payload: unknown;

  beforeEach(() => {
    calls = [];
    payload = page;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        calls.push({
          body: init?.body ? JSON.parse(String(init.body)) : {},
          method: init?.method ?? "GET",
          url: String(input),
        });
        return new Response(JSON.stringify(payload), {
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

  it("requests the in-progress widget feed once", async () => {
    renderWidget();
    expect(await screen.findByRole("heading", { name: "Devam eden medya" })).toBeTruthy();
    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe("/api/media?status=in_progress&limit=8");
  });

  it("serves the stored prefixed cover_path through mediaCoverUrl without a double prefix", async () => {
    renderWidget();
    const img = (await screen.findByAltText("")) as HTMLImageElement;
    // Eski ham birleştirme "/api/media/assets//api/media/assets/dune.webp" üretiyordu.
    expect(new URL(img.src).pathname).toBe("/api/media/assets/dune.webp");
    expect(img.src).not.toContain("assets//api");
  });

  it("falls back to cover_url when cover_path is not a safe asset name", async () => {
    payload = {
      ...page,
      items: [
        {
          ...coverItem,
          cover_path: "../remote-evil.webp",
          cover_url: "https://cdn.example.test/dune.jpg",
        },
      ],
    };
    renderWidget();
    const img = (await screen.findByAltText("")) as HTMLImageElement;
    expect(img.src).toBe("https://cdn.example.test/dune.jpg");
  });

  it("falls back to the initial-letter placeholder when no cover exists", async () => {
    payload = { ...page, items: [{ ...coverItem, cover_path: null, cover_url: null }] };
    renderWidget();
    expect(await screen.findByText("D")).toBeTruthy();
    await waitFor(() => expect(screen.queryByAltText("")).toBeNull());
  });

  it("plans the media for today with an explicit day", async () => {
    const user = userEvent.setup();
    renderWidget();

    await user.click(await screen.findByRole("button", { name: "Dune kaydını bugüne ekle" }));
    await waitFor(() =>
      expect(calls).toContainEqual({
        body: { entity_id: "media-1", day: todayKey() },
        method: "POST",
        url: "/api/plan",
      }),
    );
  });

  it("logs a quick +1 consumption with a fresh client uuid", async () => {
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("11111111-1111-4111-8111-111111111111");
    const user = userEvent.setup();
    renderWidget();

    await user.click(await screen.findByRole("button", { name: "Dune için hızlı tüketim kaydet" }));
    await waitFor(() =>
      expect(calls).toContainEqual({
        body: {
          action: "quick",
          amount: 1,
          client_uuid: "11111111-1111-4111-8111-111111111111",
          measure: "item",
        },
        method: "POST",
        url: "/api/media/media-1/consumptions",
      }),
    );
    // Widget ek sorgu acmaz: tek okuma cagrisi in-progress feed'idir.
    expect(calls.filter((call) => call.method === "GET")).toHaveLength(1);
  });
});
