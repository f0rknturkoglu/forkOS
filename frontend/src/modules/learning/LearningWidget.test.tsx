// @vitest-environment jsdom
/**
 * Faz 12: birlesik widget -- devam eden kurs + tekrar bekleyen konu tek kutuda.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LearningWidget } from "./LearningWidget";

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
    if (path === "/courses") {
      return [
        { id: "c1", title: "Lineer Cebir", status: "in_progress", progress_pct: 40 },
        { id: "c2", title: "Biten kurs", status: "done", progress_pct: 100 },
      ];
    }
    if (path.startsWith("/study/stale")) {
      return [{ id: "t1", title: "Türev", status: "in_progress", last_studied_at: "2026-08-01T10:00:00Z" }];
    }
    return {};
  });
});
afterEach(cleanup);

describe("LearningWidget birlesik (Faz 12)", () => {
  it("devam eden kurslari ve tekrar bekleyen konulari tek listede gosterir", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <LearningWidget />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Lineer Cebir")).toBeTruthy();
    expect(screen.getByText("%40")).toBeTruthy();
    // Biten kurs gizli; stale konu listede.
    expect(screen.queryByText("Biten kurs")).toBeNull();
    expect(screen.getByText("Türev")).toBeTruthy();
  });
});
