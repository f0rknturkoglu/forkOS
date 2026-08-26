// @vitest-environment jsdom
/**
 * Faz 10: Etkinlik sayfasi kaydedilmis degerlendirmeleri listeler
 * (GET /reviews ucu artik arayuzde kullaniliyor).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ActivityPage } from "./ActivityPage";

vi.mock("@/core/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    del: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
  },
  qs: vi.fn(() => ""),
}));

import { api } from "@/core/api";

const apiGet = vi.mocked(api.get);

beforeEach(() => {
  apiGet.mockReset();
  apiGet.mockImplementation(async (path: string) => {
    if (path === "/activity") return [];
    if (path === "/sources/health") return [];
    if (path.startsWith("/reviews")) {
      return [
        { id: "r1", kind: "weekly", period_start: "2026-08-17", period_end: "2026-08-23", note: "iyi haftaydı" },
        { id: "r2", kind: "daily", period_start: "2026-08-24", period_end: "2026-08-24", note: null },
      ];
    }
    return {};
  });
});
afterEach(cleanup);

describe("ActivityPage gecmis degerlendirmeler", () => {
  it("kaydedilmis review'lari kind + donem etiketiyle listeler", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <ActivityPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Değerlendirmeler")).toBeTruthy();
    expect(screen.getByText("Haftalık")).toBeTruthy();
    expect(screen.getByText("Günlük")).toBeTruthy();
    // Donem etiketi: 17-23 Agustos araligi (reviewLabel)
    expect(screen.getByText(/17 Ağu/)).toBeTruthy();
    expect(screen.getByText("iyi haftaydı")).toBeTruthy();
    // Kayit review rotasina gider.
    const weekly = screen.getByRole("link", { name: /Haftalık/ });
    expect(weekly.getAttribute("href")).toBe("#/review/weekly");
  });
});
