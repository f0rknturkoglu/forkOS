// @vitest-environment jsdom
/**
 * "Kaynakları çek" açılır listesi paylaşılan kaynak katmanını kullanır:
 * kendi katalog/koşu/senkronizasyon sorgusu ve kendi yenileme mutasyonu YOKTUR.
 * Seçim, tek yenileme yolu olan `/sources/refresh` + `{source_ids}` gövdesine
 * gider ve satır durumu paylaşılan sözlükten (`runStateView`) okunur.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SourcePicker } from "./SourcePicker";

const harness = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));

vi.mock("@/core/api", () => ({
  api: { get: harness.get, post: harness.post, patch: vi.fn(), del: vi.fn() },
}));
vi.mock("@/app/router", () => ({
  navigate: vi.fn(),
  useHashRoute: () => ({ path: "/", params: new URLSearchParams() }),
}));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true, useInvalidate: () => vi.fn() }));

beforeEach(() => {
  harness.get.mockReset();
  harness.post.mockReset();
  harness.get.mockImplementation(async (path: string) => {
    if (path === "/sources/catalog") {
      return [
        { id: "jobhunter:eures", interval_minutes: 1440, kind: "job", class: "normal", estimated_seconds: 120 },
        { id: "jobhunter:linkedin", interval_minutes: 720, kind: "job", class: "slow_optin", estimated_seconds: 180 },
      ];
    }
    if (path === "/sources/runs") {
      return [
        {
          id: "run-1",
          source: "jobhunter:eures",
          status: "ok",
          items_found: 4,
          error: null,
          error_kind: null,
          started_at: "2026-09-21T08:00:00Z",
          finished_at: "2026-09-21T08:00:09Z",
        },
      ];
    }
    if (path === "/sources/sync") return { active: null, last_completed: null, running: [], sources: [] };
    return [];
  });
});

afterEach(() => cleanup());

function renderPicker() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SourcePicker />
    </QueryClientProvider>,
  );
}

describe("kaynak seçici", () => {
  it("seçilen kaynağı paylaşılan yenileme yolundan çeker", async () => {
    renderPicker();
    fireEvent.click(screen.getByRole("button", { name: /Kaynakları çek/ }));

    const eures = await screen.findByRole("checkbox", { name: /eures/ });
    fireEvent.click(eures);
    fireEvent.click(screen.getByRole("button", { name: "Kaynakları çek (1)" }));

    await waitFor(() =>
      expect(harness.post).toHaveBeenCalledWith("/sources/refresh", { source_ids: ["jobhunter:eures"] }),
    );
  });

  it("satır durumunu paylaşılan sözlükten yazar", async () => {
    renderPicker();
    fireEvent.click(screen.getByRole("button", { name: /Kaynakları çek/ }));

    // Koşu durumu "ok" → "sağlıklı"; etiketler ham enum değildir.
    expect(await screen.findByText("sağlıklı")).toBeTruthy();
    expect(screen.getAllByText(/İş ilanı/).length).toBe(2);
  });
});
