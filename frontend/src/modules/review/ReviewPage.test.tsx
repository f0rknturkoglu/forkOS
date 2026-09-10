// @vitest-environment jsdom
/**
 * ReviewPage temel akisi: adim ilerleme, karar state'i, kirli veri ile
 * ileri adim atlamanin engellenmesi ve kayit sonrasi rota guncellemesi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DailyReviewPage } from "./ReviewPage";

vi.mock("@/core/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), put: vi.fn() },
  qs: vi.fn(() => ""),
}));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/app/router", () => ({
  navigate: vi.fn(),
  useHashRoute: () => ({ params: new URLSearchParams() }),
}));

import { api } from "@/core/api";
import { navigate } from "@/app/router";

const apiGet = vi.mocked(api.get);
const apiPost = vi.mocked(api.post);

const preview = {
  kind: "daily",
  period_start: "2026-08-31",
  period_end: "2026-08-31",
  completed_todos: [{ id: "t1", title: "Bitirilen görev", completed_at: "2026-08-31T14:00:00Z", priority: 1 }],
  unfinished_todos: [
    { id: "u1", title: "Açık görev 1", due_at: "2026-09-01", priority: 3 },
    { id: "u2", title: "Açık görev 2", due_at: null, priority: 1 },
  ],
  stats: {
    habits: {},
    capture: { notes: 0, bookmarks: 0, rss_read: 0 },
    focus: {
      minutes: 45,
      sessions: 1,
      longest_session: 45,
      interrupted: 0,
      active_days: 1,
      best_day: null,
      best_day_minutes: 45,
    },
    github: { commits: 0 },
    flashcards: { reviewed: 42, decks: { Almanca: 42 } },
    applications: { updated: 0 },
    study: {},
    todos: { completed: 1 },
    topics: [],
  },
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <DailyReviewPage />
    </QueryClientProvider>,
  );
  return client;
}

describe("ReviewPage temel akis", () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiGet.mockImplementation(async (path: string) => {
      if (path.startsWith("/reviews/preview")) return preview;
      return {};
    });
    apiPost.mockReset();
    vi.mocked(navigate).mockReset();
  });
  afterEach(cleanup);

  it("adimlari ilerletir ve karar state'ini korur", async () => {
    renderPage();

    // Adim 1: Ozet
    expect(await screen.findByRole("button", { name: "Açık işleri değerlendir" })).toBeTruthy();

    // Adim 2: kararlar
    fireEvent.click(screen.getByRole("button", { name: "Açık işleri değerlendir" }));
    expect(screen.getByText("Açık görev 1")).toBeTruthy();
    expect(screen.getByText("2 görev karar bekliyor")).toBeTruthy();

    // Bir gorevi devret -> karar state'i guncellenir.
    const carryButtons = screen.getAllByRole("button", { name: "Devret" });
    fireEvent.click(carryButtons[0]);
    expect(screen.getByText("1 görev karar bekliyor")).toBeTruthy();

    // Karar state'i adim degisiminde kaybolmaz.
    fireEvent.click(screen.getByRole("button", { name: "Öncelikleri seç" }));
    expect(screen.getByPlaceholderText("1. öncelik")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Kararlara dön" }));
    expect(screen.getByText("1 görev karar bekliyor")).toBeTruthy();
  });

  it("kirli veri varken ust ciple ileri atlama engellenir", async () => {
    renderPage();
    await screen.findByRole("button", { name: "Açık işleri değerlendir" });
    fireEvent.click(screen.getByRole("button", { name: "Açık işleri değerlendir" }));

    fireEvent.click(screen.getAllByRole("button", { name: "Devret" })[0]);

    // Geri gitmek serbesttir.
    const stepper = screen.getByRole("navigation", { name: "Değerlendirme adımları" });
    fireEvent.click(within(stepper).getByRole("button", { name: /Özet/ }));

    // Kirliyken ileri atlama: adim state'i korunur (Ozet'te kalir).
    fireEvent.click(within(stepper).getByRole("button", { name: /Öncelikler/ }));
    expect(screen.getByRole("button", { name: "Açık işleri değerlendir" })).toBeTruthy();
    expect(screen.queryByPlaceholderText("1. öncelik")).toBeNull();
  });

  it("kayittan sonra rotayi gunceller ve kapanis ekranini gosterir", async () => {
    apiPost.mockResolvedValue({});
    renderPage();
    await screen.findByRole("button", { name: "Açık işleri değerlendir" });
    fireEvent.click(screen.getByRole("button", { name: "Açık işleri değerlendir" }));
    fireEvent.click(screen.getByRole("button", { name: "Öncelikleri seç" }));

    fireEvent.click(screen.getByRole("button", { name: "Değerlendirmeyi tamamla" }));

    expect(
      await screen.findByText("Kararların plana işlendi; seçtiğin öncelikler yeni haftanın başlangıcına eklendi."),
    ).toBeTruthy();
    expect(navigate).toHaveBeenCalledWith("/review/daily");
  });
});
