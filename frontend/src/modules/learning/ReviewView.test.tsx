// @vitest-environment jsdom
/**
 * Tekrar kuyrugu (Faz 10): bolumler, gecikme vurgusu, satirdan konu acma,
 * pomodoro ve SRS derece akisi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { components } from "@/generated/api-schema";
import { ReviewView } from "./ReviewView";

type ReviewTopic = components["schemas"]["ReviewTopicOut"];
type ReviewQueue = components["schemas"]["ReviewQueueOut"];

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  openPomodoro: vi.fn(),
}));

vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return { ...actual, api: { ...actual.api, get: harness.apiGet, post: harness.apiPost } };
});
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/modules/pomodoro/dock", () => ({ openPomodoro: harness.openPomodoro }));

const days = (offset: number) => new Date(Date.now() + offset * 86_400_000).toISOString();

const topic = (over: Partial<ReviewTopic>): ReviewTopic => ({
  id: "t1",
  title: "Türev",
  area_id: "a1",
  area_title: "Matematik",
  status: "in_progress",
  interval_days: 3,
  review_count: 2,
  last_reviewed_at: null,
  last_studied_at: null,
  next_review_at: days(-3),
  mastery: 40,
  confidence: 3,
  ...over,
});

function renderView(onOpenTopic = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ReviewView onOpenTopic={onOpenTopic} />
    </QueryClientProvider>,
  );
  return onOpenTopic;
}

function mockQueue(queue: ReviewQueue) {
  harness.apiGet.mockImplementation(async () => queue);
}

beforeEach(() => {
  harness.apiGet.mockReset();
  harness.apiPost.mockReset().mockResolvedValue({});
  harness.invalidate.mockReset();
  harness.openPomodoro.mockReset();
});
afterEach(cleanup);

describe("ReviewView", () => {
  it("bes bolumu doldurur ve gecikmis tekrari vurgular", async () => {
    mockQueue({
      due_today: [topic({ id: "t-due", title: "Limit" })],
      overdue: [topic({ id: "t-late", title: "İntegral" })],
      upcoming: [topic({ id: "t-next", title: "Seriler", next_review_at: days(5) })],
      new_topics: [topic({ id: "t-new", title: "Vektörler", next_review_at: null, mastery: null })],
      weak: [topic({ id: "t-weak", title: "Matrisler", mastery: 20 })],
    });
    renderView();

    for (const section of [
      "Bugün tekrar edilecekler",
      "Gecikenler",
      "Yaklaşanlar",
      "Yeni öğrenilenler",
      "Zayıf konular",
    ]) {
      expect(await screen.findByText(section)).toBeTruthy();
    }
    const lateRow = screen.getByText("İntegral").closest("li");
    expect(lateRow?.textContent).toContain("3 gün gecikti");
    expect(lateRow?.textContent).toContain(new Date(days(-3)).toLocaleDateString("tr-TR"));
    const nextRow = screen.getByText("Seriler").closest("li");
    expect(nextRow?.textContent).toContain("5 gün sonra");
    // Ustalik hem cubuk hem sayi olarak yazilir.
    expect(screen.getByRole("progressbar", { name: "Ustalık: Matrisler" })).toBeTruthy();
    expect(harness.apiGet).toHaveBeenCalledWith("/study/review?window=14&limit=50");
  });

  it("satir basligi konuyu acar, pomodoro satirdan baslar", async () => {
    mockQueue({ due_today: [topic({})] });
    const onOpenTopic = renderView();

    fireEvent.click(await screen.findByRole("button", { name: /Türev/ }));
    expect(onOpenTopic).toHaveBeenCalledWith("t1");

    fireEvent.click(screen.getByRole("button", { name: /Pomodoro/ }));
    expect(harness.openPomodoro).toHaveBeenCalledWith({ context: "t1", topic: "Türev" });
  });

  it("derece verme SRS ucuna gider ve study.write tazeler", async () => {
    mockQueue({ overdue: [topic({})] });
    renderView();

    fireEvent.click(await screen.findByRole("button", { name: "Tekrar yap" }));
    fireEvent.click(screen.getByRole("button", { name: "Kolay" }));

    await waitFor(() => expect(harness.apiPost).toHaveBeenCalledWith("/study/topics/t1/review", { grade: "easy" }));
    await waitFor(() => expect(harness.invalidate).toHaveBeenCalledWith("study.write"));
  });

  it("bos kuyrukta yonlendirici mesaj gosterir", async () => {
    mockQueue({ due_today: [], overdue: [], upcoming: [], new_topics: [], weak: [] });
    renderView();

    expect(await screen.findByText("Bugün tekrar edilecek konu yok")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Tekrar yap" })).toBeNull();
  });

  it("bugun bos ama yaklasan varsa en yakin tarihi yazar", async () => {
    mockQueue({ upcoming: [topic({ id: "t-next", title: "Seriler", next_review_at: days(4) })] });
    renderView();

    expect(
      await screen.findByText(
        `Bugün tekrar edilecek konu yok. En yakın tekrar: ${new Date(days(4)).toLocaleDateString("tr-TR")}.`,
      ),
    ).toBeTruthy();
  });
});
