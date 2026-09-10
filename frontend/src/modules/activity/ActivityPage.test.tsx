// @vitest-environment jsdom

/**
 * Etkinlik & Ritim sayfasi: dort katmanin sozlesmesi.
 *
 * 1) ritim seridi (streak/odak/gorev/okuma/basvuru),
 * 2) aralik secici heatmap'i dogru gun sayisiyla cagirir,
 * 3) aylik barlar kirilim tooltip'i tasir,
 * 4) kategori filtresi + arama + "daha fazla yukle" sunucu parametrelerine yansir,
 * ayrica eski davranis: kaydedilmis degerlendirmeler listelenir.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { ActivityPage } from "./ActivityPage";

vi.mock("@/core/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), del: vi.fn(), patch: vi.fn(), put: vi.fn() },
  qs: (params: Record<string, unknown>) => {
    const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
    return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
  },
}));

import { api } from "@/core/api";

const apiGet = vi.mocked(api.get);

const SUMMARY = {
  counters: {
    pomodoros: { today: 3, week: 11, total: 200 },
    todos: { today: 4, week: 12, total: 300 },
    bookmarks: { today: 1, week: 4, total: 60 },
    rss_read: { today: 6, week: 20, total: 800 },
  },
  applications: { today: 2, week: 5, total: 31 },
  streak: { current: 7, longest: 21 },
};

const MONTHLY = [
  { month: "2026-07", pomodoros: 0, todos: 0, bookmarks: 0, notes: 0, rss_read: 0, reviews: 0, applications: 0 },
  {
    month: "2026-08",
    pomodoros: 40,
    todos: 30,
    bookmarks: 6,
    notes: 8,
    rss_read: 60,
    reviews: 2,
    applications: 4,
  },
];

function feedItem(id: number, verb: string, title: string) {
  return {
    id,
    entity_id: `00000000-0000-0000-0000-0000000000${String(id).padStart(2, "0")}`,
    entity_type: "todo",
    verb,
    payload: { title },
    occurred_at: new Date().toISOString(),
  };
}

function feed(count: number) {
  return Array.from({ length: count }, (_, index) => feedItem(index + 1, "todo.completed", `Görev ${index + 1}`));
}

function heatmapBody() {
  return {
    days: [{ day: new Date().toISOString().slice(0, 10), total: 3, kinds: { task: 3 } }],
    labels: { task: "görev" },
    totals: { task: 3 },
    total: 3,
    active_days: 1,
    best_day: null,
    streak: 7,
  };
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <ActivityPage />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

/** Verilen URL'lerle cagrilan istekler: path + query birlikte. */
const requested = (fragment: string) =>
  apiGet.mock.calls.map(([path]) => String(path)).filter((p) => p.includes(fragment));

beforeEach(() => {
  apiGet.mockReset();
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: { getItem: () => null } });
  apiGet.mockImplementation(async (path: string) => {
    if (path.startsWith("/statistics/summary")) return SUMMARY;
    if (path.startsWith("/statistics/monthly")) return MONTHLY;
    if (path.startsWith("/pomodoro/stats")) return { minutes: 150, sessions: 3, interrupted: 1 };
    if (path.startsWith("/activity/heatmap")) return heatmapBody();
    if (path.startsWith("/activity/day")) return { day: "", events: [], kinds: {}, labels: {}, total: 0, other: 0 };
    if (path.startsWith("/activity")) return feed(50);
    if (path.startsWith("/sources/health")) return [];
    if (path.startsWith("/reviews")) {
      return [{ id: "r1", kind: "weekly", period_start: "2026-08-17", period_end: "2026-08-23", note: "iyi haftaydı" }];
    }
    throw new Error(`beklenmeyen çağrı: ${path}`);
  });
});

afterEach(cleanup);

describe("Etkinlik & Ritim — ritim şeridi", () => {
  it("seri, odak, görev, okuma ve başvuru metriklerini gösterir", async () => {
    renderPage();

    await waitFor(() => expect(screen.getByText("7 gün")).toBeTruthy());
    expect(screen.getByText("rekor 21 gün")).toBeTruthy();
    expect(screen.getByText("150 dk")).toBeTruthy();
    expect(screen.getByText("3 seans · 1 kesinti")).toBeTruthy();
    expect(screen.getByText("Bu hafta 12", { exact: false })).toBeTruthy();
    // Okunan = rss_read.today + bookmarks.today = 6 + 1
    expect(screen.getByText("7")).toBeTruthy();
    expect(screen.getByText("toplam 31")).toBeTruthy();
  });
});

describe("Etkinlik & Ritim — harita aralığı", () => {
  it("aralık seçicisi heatmap'i seçilen gün sayısıyla çağırır", async () => {
    renderPage();
    await waitFor(() => expect(requested("/activity/heatmap")).toHaveLength(1));
    expect(requested("/activity/heatmap")[0]).toContain("days=365");

    fireEvent.click(screen.getByRole("tab", { name: "Son 3 ay" }));

    await waitFor(() => expect(requested("/activity/heatmap").some((path) => path.includes("days=90"))).toBe(true));
  });
});

describe("Etkinlik & Ritim — aylık trend", () => {
  it("barlar odak/görev/okuma/başvuru kırılımını tooltip'te taşır", async () => {
    const { container } = renderPage();

    await waitFor(() => expect(screen.getByText("Ağu '26")).toBeTruthy());
    const bar = container.querySelector<HTMLElement>('[title*="Ağu \'26"]');
    expect(bar?.getAttribute("title")).toContain("odak 40");
    expect(bar?.getAttribute("title")).toContain("görev 30");
    expect(bar?.getAttribute("title")).toContain("okuma 66");
    expect(bar?.getAttribute("title")).toContain("başvuru 4");
  });
});

describe("Etkinlik & Ritim — canlı akış", () => {
  it("kategori çipi ve arama sunucu parametrelerine yansır", async () => {
    renderPage();
    await waitFor(() => expect(requested("/activity?")).toHaveLength(1));

    fireEvent.click(screen.getByRole("tab", { name: "Görevler" }));
    await waitFor(() =>
      expect(requested("/activity?").some((path) => path.includes("category=task") && path.includes("limit=50"))).toBe(
        true,
      ),
    );

    fireEvent.change(screen.getByLabelText("Hareketlerde ara"), { target: { value: "arkeoloji" } });
    await waitFor(() => expect(requested("/activity?").some((path) => path.includes("q=arkeoloji"))).toBe(true), {
      timeout: 2000,
    });
  });

  it("dolu sayfa sonunda daha fazla yükle limit'i büyütür", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByRole("button", { name: "Daha fazla yükle" })).toBeTruthy());

    fireEvent.click(screen.getByRole("button", { name: "Daha fazla yükle" }));

    await waitFor(() => expect(requested("/activity?").some((path) => path.includes("limit=100"))).toBe(true));
  });

  it("uyarı filtresi yalnızca uyarı fiillerini gösterir", async () => {
    apiGet.mockImplementation(async (path: string) => {
      if (path.startsWith("/statistics/summary")) return SUMMARY;
      if (path.startsWith("/statistics/monthly")) return MONTHLY;
      if (path.startsWith("/pomodoro/stats")) return { minutes: 0, sessions: 0, interrupted: 0 };
      if (path.startsWith("/activity/heatmap")) return heatmapBody();
      if (path.startsWith("/activity?")) {
        return [
          feedItem(1, "todo.completed", "Normal görev"),
          { ...feedItem(2, "rss.feed_failed", "Bozuk besleme"), payload: { message: "zaman aşımı" } },
        ];
      }
      if (path.startsWith("/sources/health")) return [];
      return [];
    });
    renderPage();

    await waitFor(() => expect(screen.getByText(/Normal görev/)).toBeTruthy());
    expect(screen.getByText(/zaman aşımı/)).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Sadece Uyarılar" }));

    // Once uyari satirinin GELDIGINI bekle, sonra digerinin gittigini dogrula:
    // ters sirada beklersek "yokluk" yukleme sirasinda da dogru cikar.
    await waitFor(() => expect(screen.getByText(/zaman aşımı/)).toBeTruthy());
    expect(screen.queryByText(/Normal görev/)).toBeNull();
  });

  it("kaydedilmiş değerlendirmeleri listeler (eski davranış)", async () => {
    renderPage();

    expect(await screen.findByText("Değerlendirmeler")).toBeTruthy();
    expect(screen.getByText("Haftalık")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Haftalık/ }).getAttribute("href")).toBe("#/review/weekly");
  });
});
