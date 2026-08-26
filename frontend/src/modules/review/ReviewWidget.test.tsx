// @vitest-environment jsdom
/**
 * Faz 10: ReviewWidget haftalik giris noktasi. Nav'da gizlenen review
 * modulunun ASIL giris yeri bu widget -- hafta donumu hatirlatmasi test edilir.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ReviewWidget } from "./ReviewWidget";

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
vi.mock("@/app/router", () => ({ navigate: vi.fn() }));

import { api } from "@/core/api";

const apiGet = vi.mocked(api.get);

/** Yerel hafta basi (Pazartesi) anahtari -- backend period_start ile ayni. */
function mondayKey(): string {
  const now = new Date();
  const day = now.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(now);
  monday.setDate(now.getDate() + diff);
  return monday.toLocaleDateString("sv-SE");
}

function renderWidget() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ReviewWidget />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiGet.mockReset();
  apiGet.mockImplementation(async (path: string) => {
    if (path.startsWith("/activity")) return [];
    if (path.startsWith("/reviews")) return [];
    return {};
  });
});
afterEach(cleanup);

describe("ReviewWidget haftalik giris", () => {
  it("gunluk ve haftalik butonlarini gosterir, ikisi de acilir", async () => {
    renderWidget();
    expect(await screen.findByText("Günlük değerlendirme")).toBeTruthy();
    expect(screen.getByText("Haftalık değerlendirme")).toBeTruthy();
  });

  it("bu hafta yapildiysa tek satira iner", async () => {
    apiGet.mockImplementation(async (path: string) => {
      if (path.startsWith("/activity")) return [];
      if (path.startsWith("/reviews")) {
        return [{ id: "r1", kind: "weekly", period_start: mondayKey(), period_end: mondayKey() }];
      }
      return {};
    });
    renderWidget();
    expect(await screen.findByText("Haftalık değerlendirmeyi yaptın.")).toBeTruthy();
    expect(screen.queryByText("Haftalık değerlendirme hazır")).toBeNull();
  });
});
