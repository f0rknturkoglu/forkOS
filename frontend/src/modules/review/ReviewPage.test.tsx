// @vitest-environment jsdom
/**
 * ReviewPage tek sayfa akışı: zorunlu sihirbaz/öncelik yok, not opsiyonel,
 * açık görevler olduğu gibi kalır ve kaydedilmiş dönem yeniden yazılmaz.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DailyReviewPage, MonthlyReviewPage, YearlyReviewPage } from "./ReviewPage";

const routeHarness = vi.hoisted(() => ({ period: "" }));

vi.mock("@/core/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), put: vi.fn() },
  qs: (params: Record<string, string | number>) =>
    `?${new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)]))}`,
}));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/app/router", () => ({
  navigate: vi.fn(),
  useHashRoute: () => ({ params: new URLSearchParams(routeHarness.period ? `period=${routeHarness.period}` : "") }),
}));

import { api } from "@/core/api";
import { navigate } from "@/app/router";
import { todayKey } from "@/lib/date";
import type { ReviewPreview } from "@/core/types";

const apiGet = vi.mocked(api.get);
const apiPost = vi.mocked(api.post);

interface HistoryRow {
  id: string;
  kind: string;
  period_start: string;
  period_end: string;
  stats: unknown;
  note: string | null;
}

const preview: ReviewPreview = {
  kind: "daily",
  period_start: todayKey(),
  period_end: todayKey(),
  completed_todos: [{ id: "t1", title: "Bitirilen görev", completed_at: "2026-08-31T14:00:00Z" }],
  unfinished_todos: [
    { id: "u1", title: "Açık görev 1", due_at: "2026-09-01T12:00:00Z", priority: 3 },
    { id: "u2", title: "Açık görev 2", due_at: null, priority: 1 },
  ],
  stats: {
    todos: { completed: 1, created: 3, dropped: 0, overdue_now: 1 },
    focus: {
      minutes: 45,
      sessions: 1,
      longest_session: 45,
      interrupted: 0,
      active_days: 1,
      best_day: null,
      best_day_minutes: 45,
    },
    topics: [],
    habits: {},
    capture: { notes: 0, bookmarks: 0, rss_read: 0 },
    applications: {
      discovered: 0,
      shortlisted: 0,
      prepared: 0,
      applied: 0,
      interview: 0,
      offer: 0,
      rejected: 0,
      upcoming_deadlines: 0,
      career_prep: 0,
    },
    study: { minutes_by_area: {} },
    flashcards: { reviewed: 42, decks: { Almanca: 42 } },
    github: { commits: 0, repos: {} },
  },
};

let history: HistoryRow[] = [];

function renderPage(Page = DailyReviewPage) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <Page />
    </QueryClientProvider>,
  );
  return client;
}

describe("ReviewPage tek sayfa akışı", () => {
  beforeEach(() => {
    routeHarness.period = "";
    history = [];
    apiGet.mockReset();
    apiGet.mockImplementation(async (path: string) => {
      if (path.startsWith("/reviews/preview")) return preview;
      if (path.startsWith("/reviews")) return history;
      return {};
    });
    apiPost.mockReset();
    apiPost.mockResolvedValue({});
    vi.mocked(navigate).mockReset();
  });
  afterEach(cleanup);

  it("tek sayfada dört sinyal ve kapanış bölümlerini gösterir, adım sihirbazı yoktur", async () => {
    renderPage();

    expect(await screen.findByText("Tamamlanan iş")).toBeTruthy();
    expect(screen.getByText("Odak süresi")).toBeTruthy();
    expect(screen.getByText("Aktif gün")).toBeTruthy();
    expect(screen.getByText("Devreden açık görev")).toBeTruthy();

    expect(screen.getByText("Neler oldu?")).toBeTruthy();
    expect(screen.getByText("Açık kalanlar")).toBeTruthy();
    expect(screen.getByText("Kendi notum")).toBeTruthy();
    expect(screen.queryByRole("navigation", { name: "Değerlendirme adımları" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Öncelikleri seç" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Görevlere git/ }));
    expect(navigate).toHaveBeenCalledWith("/todos");
  });

  it("not ve karar olmadan kaydeder", async () => {
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /Değerlendirmeyi kaydet/ }));

    // Karar verilmemiş ve not yazılmamış: gövdede ikisi de yok, kayıt yine olur.
    await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/reviews", { kind: "daily", period_start: todayKey() }));
  });

  it("devretme opsiyoneldir: işaretlenirse gönderilir, not ile birlikte", async () => {
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /Taşı veya bırak/ }));
    fireEvent.click(screen.getAllByRole("button", { name: "Devret" })[0]);
    fireEvent.change(screen.getByPlaceholderText("Dönem hakkında kısa bir not"), {
      target: { value: "Yarına taşındı" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Değerlendirmeyi kaydet/ }));

    await waitFor(() =>
      expect(apiPost).toHaveBeenCalledWith("/reviews", {
        kind: "daily",
        period_start: todayKey(),
        note: "Yarına taşındı",
        decisions: { carry_over: ["u1"], drop: [] },
      }),
    );
  });

  it("kaydedilmiş dönemde kaydetme kapanır ve kayıtlı not görünür", async () => {
    history = [
      {
        id: "r1",
        kind: "daily",
        period_start: todayKey(),
        period_end: todayKey(),
        stats: preview.stats,
        note: "Günü erken kapattım.",
      },
    ];
    renderPage();

    expect(await screen.findByDisplayValue("Günü erken kapattım.")).toBeTruthy();
    expect(screen.getByText("Bu dönemin değerlendirmesi kaydedildi")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Değerlendirmeyi kaydet/ })).toBeNull();

    fireEvent.change(screen.getByPlaceholderText("Dönem hakkında kısa bir not"), {
      target: { value: "Düzeltilmiş not" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Notu kaydet" }));
    await waitFor(() => expect(api.patch).toHaveBeenCalledWith("/reviews/r1", { note: "Düzeltilmiş not" }));
  });

  it("eski geçmiş kaydıyla değişimi gösterir", async () => {
    // Eski kayıtta yalnız iki alan var: eksik alanlar karşılaştırılmaz.
    history = [
      {
        id: "old",
        kind: "daily",
        period_start: "2020-01-06",
        period_end: "2020-01-06",
        stats: { todos: { completed: 4 }, focus: { minutes: 45 } },
        note: null,
      },
    ];
    renderPage();

    expect(await screen.findByText("Önemli değişiklik")).toBeTruthy();
    expect(screen.getByText("-3")).toBeTruthy();
    expect(screen.getByText("değişmedi")).toBeTruthy();
  });

  it("aylık ve yıllık dönemleri URL ile açar; önceki dönem bağlantısı üretir", async () => {
    routeHarness.period = "2026-03-01";
    renderPage(MonthlyReviewPage);
    expect(await screen.findByText("Aylık değerlendirme")).toBeTruthy();
    expect(apiGet).toHaveBeenCalledWith(expect.stringContaining("kind=monthly"));
    fireEvent.click(screen.getByRole("button", { name: /Önceki dönem/ }));
    expect(navigate).toHaveBeenCalledWith("/review/monthly?period=2026-02-01");
    cleanup();
    renderPage(YearlyReviewPage);
    expect(await screen.findByText("Yıllık değerlendirme")).toBeTruthy();
  });

  it("kaydedilmiş dönemin sayısını canlı preview yerine snapshot'tan okur", async () => {
    history = [
      {
        id: "snap",
        kind: "daily",
        period_start: todayKey(),
        period_end: todayKey(),
        stats: { ...preview.stats, todos: { ...preview.stats.todos, completed: 999 } },
        note: null,
      },
    ];
    renderPage();
    expect(await screen.findByText("999")).toBeTruthy();
  });
});
