// @vitest-environment jsdom

/**
 * Etkinlik sayfasi: uc katmanin sozlesmesi.
 *
 * 1) Ritim: seri/odak/gorev/okuma/basvuru seridi,
 * 2) Harita: aralik secici YALNIZ haritayi etkiler (gun sayisiyla cagirir),
 * 3) Trend: aylik barlar kirilim tooltip'i tasir,
 * 4) Hareket akisi: alan filtresi + arama SUNUCU parametrelerine yansir,
 *    uyarilar da sunucudan suzulur (istemci sayfayi suzmez),
 * ayrica kaynak sagligi BURADA degildir (sahibi Ayarlar) ve gecmis
 * degerlendirmeler katlanmis durur.
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

function dayKey(offset: number): string {
  const date = new Date();
  date.setDate(date.getDate() - offset);
  return date.toISOString().slice(0, 10);
}

function feedItem(id: number, verb: string, title: string, extra: Record<string, unknown> = {}) {
  return {
    id,
    entity_id: `00000000-0000-0000-0000-0000000000${String(id).padStart(2, "0")}`,
    entity_type: "todo",
    verb,
    payload: { title },
    occurred_at: `${dayKey(0)}T09:30:00+00:00`,
    is_alert: false,
    ...extra,
  };
}

/** Iki gun: gruplama ve "tumunu ac" kontrolu bunun uzerinde calisir. */
function feed(count: number) {
  return Array.from({ length: count }, (_, index) =>
    feedItem(
      index + 1,
      "todo.completed",
      `Görev ${index + 1}`,
      index < count / 2 ? {} : { occurred_at: `${dayKey(1)}T18:00:00+00:00` },
    ),
  );
}

function heatmapBody() {
  return {
    days: [{ day: dayKey(0), total: 3, kinds: { task: 3 } }],
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
    if (path.startsWith("/activity?")) return feed(50);
    if (path.startsWith("/sources/health")) return [];
    throw new Error(`beklenmeyen çağrı: ${path}`);
  });
});

afterEach(cleanup);

describe("Etkinlik — ritim şeridi", () => {
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

describe("Etkinlik — harita", () => {
  it("aralık seçicisi yalnız haritayı seçilen gün sayısıyla çağırır", async () => {
    renderPage();
    await waitFor(() => expect(requested("/activity/heatmap")).toHaveLength(1));
    expect(requested("/activity/heatmap")[0]).toContain("days=365");

    const feedBefore = requested("/activity?").length;
    const trendBefore = requested("/statistics/monthly").length;

    fireEvent.click(screen.getByRole("tab", { name: "Son 3 ay" }));

    await waitFor(() => expect(requested("/activity/heatmap").some((path) => path.includes("days=90"))).toBe(true));
    // Aralik sayfa filtresi degil: akis ve trend istekleri degismez.
    expect(requested("/activity?")).toHaveLength(feedBefore);
    expect(requested("/statistics/monthly")).toHaveLength(trendBefore);
  });
});

describe("Etkinlik — trend", () => {
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

describe("Etkinlik — hareket akışı", () => {
  it("alan filtresi ve arama sunucu parametrelerine yansır", async () => {
    renderPage();
    await waitFor(() => expect(requested("/activity?")).toHaveLength(1));
    expect(requested("/activity?")[0]).toContain("filter=all");

    fireEvent.click(screen.getByRole("tab", { name: "Görevler" }));
    await waitFor(() =>
      expect(requested("/activity?").some((path) => path.includes("filter=tasks") && path.includes("limit=50"))).toBe(
        true,
      ),
    );

    fireEvent.change(screen.getByLabelText("Hareketlerde ara"), { target: { value: "arkeoloji" } });
    await waitFor(() => expect(requested("/activity?").some((path) => path.includes("q=arkeoloji"))).toBe(true), {
      timeout: 2000,
    });
  });

  it("uyarı filtresi sunucudan gelir: istemci ilk sayfayı süzmez", async () => {
    apiGet.mockImplementation(async (path: string) => {
      if (path.startsWith("/statistics/summary")) return SUMMARY;
      if (path.startsWith("/statistics/monthly")) return MONTHLY;
      if (path.startsWith("/pomodoro/stats")) return { minutes: 0, sessions: 0, interrupted: 0 };
      if (path.startsWith("/activity/heatmap")) return heatmapBody();
      if (path.startsWith("/activity?")) {
        // Sunucu suzulmus pencereyi doner; gelen satirlar OLDUGU GIBI cizilir.
        return [
          feedItem(1, "rss.feed_failed", "Bozuk besleme", { payload: { message: "zaman aşımı" }, is_alert: true }),
        ];
      }
      if (path.startsWith("/sources/health")) return [];
      return [];
    });
    const { container } = renderPage();

    fireEvent.click(await screen.findByRole("tab", { name: "Uyarılar" }));

    await waitFor(() => expect(requested("/activity?").some((path) => path.includes("filter=alerts"))).toBe(true));
    await waitFor(() => expect(screen.getByText(/zaman aşımı/)).toBeTruthy());
    // Istemci tarafli suzme kalinti birakmadi: uyari satiri uyari renginde.
    await waitFor(() => expect(container.querySelector(".text-warn")).toBeTruthy());
  });

  it("gün grupları aç/kapat ile yönetilir", async () => {
    const { container } = renderPage();

    await waitFor(() => expect(container.querySelectorAll("[data-activity-day]").length).toBe(2));
    // Yalnizca en yeni gun acik gelir.
    await waitFor(() => expect(container.querySelectorAll("[data-activity-day][open]").length).toBe(1));

    fireEvent.click(screen.getByRole("button", { name: /Tümünü aç/ }));
    await waitFor(() => expect(container.querySelectorAll("[data-activity-day][open]").length).toBe(2));

    fireEvent.click(screen.getByRole("button", { name: /Tümünü kapat/ }));
    await waitFor(() => expect(container.querySelectorAll("[data-activity-day][open]").length).toBe(0));
  });

  it("dolu sayfa sonunda daha fazla yükle limit'i büyütür", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByRole("button", { name: "Daha fazla yükle" })).toBeTruthy());

    fireEvent.click(screen.getByRole("button", { name: "Daha fazla yükle" }));

    await waitFor(() => expect(requested("/activity?").some((path) => path.includes("limit=100"))).toBe(true));
  });

  it("kaynak sağlığı Activity'de istenmez (sahibi Ayarlar)", async () => {
    renderPage();
    await waitFor(() => expect(requested("/activity?")).toHaveLength(1));

    expect(requested("/sources/health")).toHaveLength(0);
  });

  it("ham geçmişi ikincil tutar ve Review arşivini kopyalamaz", async () => {
    renderPage();
    await waitFor(() => expect(requested("/activity?")).toHaveLength(1));
    const details = screen.getByText("Detaylı geçmiş").closest("details");
    expect(details?.hasAttribute("open")).toBe(false);
    expect(screen.getByText("Ritim")).toBeTruthy();
    expect(screen.queryByText("Değerlendirme geçmişi")).toBeNull();
    expect(requested("/reviews")).toHaveLength(0);
  });
});
