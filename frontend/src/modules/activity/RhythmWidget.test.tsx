// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiGet = vi.fn();
vi.mock("@/core/api", () => ({
  api: { get: (...args: unknown[]) => apiGet(...args) },
}));

import { RhythmWidget } from "./RhythmWidget";

function renderWidget() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  return render(
    <QueryClientProvider client={client}>
      <RhythmWidget />
    </QueryClientProvider>,
  );
}

function summaryBody() {
  return {
    counters: {
      pomodoros: { today: 2, week: 9, total: 120 },
      todos: { today: 3, week: 18, total: 400 },
      bookmarks: { today: 1, week: 5, total: 80 },
      notes: { today: 0, week: 2, total: 45 },
      rss_read: { today: 4, week: 30, total: 900 },
      reviews: { today: 0, week: 0, total: 12 },
      courses: { today: 0, week: 1, total: 7 },
    },
    applications: { today: 1, week: 3, total: 22 },
    streak: { current: 5, longest: 14 },
  };
}

function monthlyBody() {
  return [
    { month: "2026-03", pomodoros: 0, todos: 0, bookmarks: 0, notes: 0, rss_read: 0, reviews: 0, applications: 0 },
    { month: "2026-04", pomodoros: 0, todos: 0, bookmarks: 0, notes: 0, rss_read: 0, reviews: 0, applications: 0 },
    { month: "2026-05", pomodoros: 0, todos: 0, bookmarks: 0, notes: 0, rss_read: 0, reviews: 0, applications: 0 },
    { month: "2026-06", pomodoros: 0, todos: 0, bookmarks: 0, notes: 0, rss_read: 0, reviews: 0, applications: 0 },
    { month: "2026-07", pomodoros: 0, todos: 0, bookmarks: 0, notes: 0, rss_read: 0, reviews: 0, applications: 0 },
    { month: "2026-08", pomodoros: 42, todos: 30, bookmarks: 6, notes: 8, rss_read: 60, reviews: 2, applications: 4 },
  ];
}

beforeEach(() => {
  vi.clearAllMocks();
  apiGet.mockImplementation((path: string) => {
    if (path.startsWith("/statistics/summary")) return Promise.resolve(summaryBody());
    if (path.startsWith("/statistics/monthly")) return Promise.resolve(monthlyBody());
    return Promise.reject(new Error(`beklenmeyen çağrı: ${path}`));
  });
});

describe("RhythmWidget", () => {
  it("sayac kartlarini ve seri rozetini gosterir", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText("bugün · Odak")).toBeTruthy());
    expect(screen.getByText("2")).toBeTruthy(); // bugün pomodoro
    expect(screen.getByText("bugün · Başvuru")).toBeTruthy();
    expect(screen.getByText("5 gün seri")).toBeTruthy();
  });

  it("aylik grafigi toplam hareketle cizer", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByRole("img", { name: /ayların toplam hareketi/i })).toBeTruthy());
    expect(screen.getByText("Ağu '26")).toBeTruthy();
  });

  it("veri yokken bos durum gosterir", async () => {
    apiGet.mockImplementation((path: string) => {
      if (path.startsWith("/statistics/summary")) {
        return Promise.resolve({
          counters: { pomodoros: { today: 0, week: 0, total: 0 } },
          applications: { today: 0, week: 0, total: 0 },
          streak: { current: 0, longest: 0 },
        });
      }
      return Promise.resolve([]);
    });
    renderWidget();
    await waitFor(() => expect(screen.getByText(/Henüz veri yok/)).toBeTruthy());
  });
});
