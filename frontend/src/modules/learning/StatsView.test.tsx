// @vitest-environment jsdom
/**
 * Istatistik gorunumu (Faz 11): aralik secimi (URL), metrikler, alan/konu
 * kirilimlari ve "veri yok" durumu.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { components } from "@/generated/api-schema";
import { StatsView } from "./StatsView";

type StudyStats = components["schemas"]["StudyStatsOut"];

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  navigate: vi.fn(),
  onOpenTopic: vi.fn(),
  routeParams: "",
}));

vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return { ...actual, api: { ...actual.api, get: harness.apiGet } };
});
vi.mock("@/app/router", () => ({
  useHashRoute: () => ({ path: "/learning", params: new URLSearchParams(harness.routeParams) }),
  navigate: (path: string) => harness.navigate(path),
}));

const STATS: StudyStats = {
  focus_minutes: 205,
  focus_sessions: 6,
  topics_done: 4,
  topics_started: 9,
  resources_done: 12,
  reviews_done: 31,
  active_days: 5,
  streak_days: 3,
  by_area: [
    { area_id: "a1", title: "Matematik", minutes: 120 },
    { area_id: "a2", title: "Fizik", minutes: 85 },
  ],
  by_topic: [{ topic_id: "t1", title: "Türev", minutes: 120 }],
  planned_minutes: 300,
  actual_minutes: 205,
  courses: { total: 3, done: 1, in_progress: 2 },
  flashcards_reviewed: 40,
  confidence_delta: 5,
};

function renderView() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <StatsView onOpenTopic={harness.onOpenTopic} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  harness.apiGet.mockReset().mockImplementation(async () => STATS);
  harness.navigate.mockReset();
  harness.onOpenTopic.mockReset();
  harness.routeParams = "";
});
afterEach(cleanup);

describe("StatsView", () => {
  it("varsayilan aralik 'week' ile metrikleri yazar", async () => {
    renderView();

    const focusCell = (await screen.findByText("Odak süresi")).parentElement;
    expect(focusCell?.textContent).toContain("3 sa 25 dk");
    expect(screen.getByText("Öğrenilen konu")).toBeTruthy();
    expect(screen.getByText("Aktif gün")).toBeTruthy();
    expect(harness.apiGet).toHaveBeenCalledWith("/study/stats?range=week");
    // Alan kirilimi sayilari metin olarak da gorunur.
    const areaRow = screen.getByText("Matematik").closest("li");
    expect(areaRow?.textContent).toContain("120 dk");
  });

  it("aralik cipleri URL'e yazar ve yeni aralikla sorgular", async () => {
    renderView();
    await screen.findByRole("button", { name: "Bu hafta" });

    fireEvent.click(screen.getByRole("button", { name: "Bu ay" }));
    expect(harness.navigate).toHaveBeenCalledWith("/learning?view=stats&range=month");

    cleanup();
    harness.routeParams = "view=stats&range=month";
    renderView();
    expect(await screen.findByRole("button", { name: "Bu ay" })).toBeTruthy();
    expect(harness.apiGet).toHaveBeenCalledWith("/study/stats?range=month");
  });

  it("konu kirilimindan konuyu acar", async () => {
    renderView();
    fireEvent.click(await screen.findByRole("button", { name: /Türev/ }));
    expect(harness.onOpenTopic).toHaveBeenCalledWith("t1");
  });

  it("plan/gercek ve kurs ozetini gosterir", async () => {
    renderView();
    await screen.findByText("Planlanan ve gerçekleşen");
    expect(screen.getByText("5 sa")).toBeTruthy(); // planlanan 300 dk
    expect(screen.getByText("Planın %68'i")).toBeTruthy();
    expect(screen.getByText("Devam ediyor")).toBeTruthy();
    expect(screen.getByText("Değerlendirmeyi aç").closest("a")?.getAttribute("href")).toBe("#/review/weekly");
  });

  it("aralikta veri yoksa vanity metrik uretmez", async () => {
    harness.apiGet.mockImplementation(async () => ({
      focus_minutes: 0,
      focus_sessions: 0,
      topics_done: 0,
      topics_started: 0,
      resources_done: 0,
      reviews_done: 0,
      active_days: 0,
      streak_days: 0,
      by_area: [],
      by_topic: [],
      planned_minutes: 0,
      actual_minutes: 0,
      courses: { total: 0, done: 0, in_progress: 0 },
      flashcards_reviewed: 0,
      confidence_delta: 0,
    }));
    renderView();

    expect(await screen.findByText("Bu aralıkta veri yok")).toBeTruthy();
    expect(screen.queryByText("Odak süresi")).toBeNull();
  });
});
