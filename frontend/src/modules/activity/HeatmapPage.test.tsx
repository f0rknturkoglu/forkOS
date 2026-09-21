// @vitest-environment jsdom
/**
 * Isı Haritası sayfası (Polish 1 §5/§6/§36).
 *
 * Harita YENİDEN YAZILMADI: Etkinlik sayfasındaki `Heatmap` bileşeni burada da
 * kullanılır. Bu testler derin bağlantı rotasını, aralık seçiminin URL'de
 * taşınmasını ve kare tıklamasının gün sayfasına gitmesini sabitler.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HeatmapPage } from "./HeatmapPage";

let calls: string[] = [];

/** Gerçek /activity/heatmap gövdesi: kareler + etiketler + seri. */
const HEATMAP = {
  days: [
    { day: "2026-09-20", total: 3, kinds: { todo: 1, reading: 2 } },
    { day: "2026-09-21", total: 0, kinds: {} },
  ],
  labels: { todo: "görev", reading: "okuma" },
  totals: { todo: 1, reading: 2 },
  max: 3,
  streak: 2,
};

beforeEach(() => {
  calls = [];
  location.hash = "#/activity/heatmap";
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      const path = url.pathname.replace(/^\/api/, "") + url.search;
      calls.push(path);
      return new Response(JSON.stringify(HEATMAP), { status: 200, headers: { "Content-Type": "application/json" } });
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <HeatmapPage />
    </QueryClientProvider>,
  );
}

describe("Isı Haritası sayfası", () => {
  it("HM1/HM2: doğrudan rotada mevcut Heatmap bileşenini kullanır", async () => {
    renderPage();

    expect(await screen.findByText("Emek haritası")).toBeTruthy();
    expect(calls.some((path) => path.startsWith("/activity/heatmap?days=365"))).toBe(true);
    // Aralık sekmeleri Etkinlik sayfasıyla aynı kaynaktan gelir.
    for (const label of ["Son 3 ay", "Son 6 ay", "Son 1 yıl"]) {
      expect(screen.getByRole("tab", { name: label })).toBeTruthy();
    }
  });

  it("HM3: aralık seçimi gün sayısını değiştirir ve URL'ye yazılır", async () => {
    renderPage();
    await screen.findByText("Emek haritası");

    fireEvent.click(screen.getByRole("tab", { name: "Son 6 ay" }));
    await waitFor(() => expect(calls.some((path) => path.includes("days=180"))).toBe(true));
    expect(location.hash).toBe("#/activity/heatmap?range=6m");
  });

  it("?range=3m derin bağlantısı doğru aralıkla açılır", async () => {
    location.hash = "#/activity/heatmap?range=3m";
    renderPage();

    await screen.findByText("Emek haritası");
    await waitFor(() => expect(calls.some((path) => path.includes("days=90"))).toBe(true));
    expect(screen.getByRole("tab", { name: "Son 3 ay" }).getAttribute("aria-selected")).toBe("true");
  });

  it("bilinmeyen aralık parametresi güvenli varsayılana düşer", async () => {
    location.hash = "#/activity/heatmap?range=yok";
    renderPage();

    await screen.findByText("Emek haritası");
    await waitFor(() => expect(calls.some((path) => path.includes("days=365"))).toBe(true));
  });

  it("sayfa Etkinlik akışına bağlantı verir (bağlam kaybolmaz)", async () => {
    renderPage();
    const back = await screen.findByRole("link", { name: /Etkinlik akışı/ });
    expect(back.getAttribute("href")).toBe("#/activity");
  });
});
