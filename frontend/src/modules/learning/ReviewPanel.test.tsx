// @vitest-environment jsdom
/**
 * ReviewPanel — 5 dereceli tekrar, yeni araligin gosterimi, bagli desteler.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { formatTrDate } from "@/lib/date";
import { REVIEW_GRADES, ReviewPanel, dueLabel } from "./ReviewPanel";

const harness = vi.hoisted(() => ({
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  listDecks: vi.fn(),
  addCard: vi.fn(),
  createDeck: vi.fn(),
  deleteDeck: vi.fn(),
  linkEntities: vi.fn(),
}));

vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return { ...actual, api: { post: harness.apiPost } };
});
vi.mock("@/core/invalidation", () => ({ invalidateAfter: (...events: string[]) => harness.invalidate(...events) }));
vi.mock("@/core/links", () => ({ linkEntities: harness.linkEntities }));
vi.mock("@/modules/flashcard/api", () => ({
  listDecks: harness.listDecks,
  addCard: harness.addCard,
  createDeck: harness.createDeck,
  deleteDeck: harness.deleteDeck,
}));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));

const review = {
  due: true,
  ease: 2.5,
  interval_days: 2,
  last_reviewed_at: "2026-09-05T10:00:00Z",
  mastery: 30,
  next_review_at: "2026-09-07T10:00:00Z",
  review_count: 3,
};

function renderPanel(over: Partial<Parameters<typeof ReviewPanel>[0]> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <ReviewPanel topicId="t1" review={review} confidence={4} lastStudiedAt="2026-09-06T10:00:00Z" {...over} />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("dueLabel", () => {
  const now = new Date("2026-09-10T12:00:00Z").getTime();

  it("plan yoksa notr der", () => {
    expect(dueLabel({ due: false, next_review_at: null }, now)).toEqual({
      text: "Tekrar planlanmadı",
      tone: "neutral",
    });
  });

  it("gecikmeyi gun olarak soyler", () => {
    expect(dueLabel({ due: true, next_review_at: "2026-09-07T10:00:00Z" }, now)).toEqual({
      text: "3 gün gecikti",
      tone: "danger",
    });
  });

  it("ayni gun icin 'Bugün tekrar' der", () => {
    expect(dueLabel({ due: true, next_review_at: "2026-09-10T09:00:00Z" }, now)).toEqual({
      text: "Bugün tekrar",
      tone: "warn",
    });
  });

  it("ileri tarihi gun olarak soyler", () => {
    expect(dueLabel({ due: false, next_review_at: "2026-09-15T10:00:00Z" }, now)).toEqual({
      text: "5 gün sonra",
      tone: "ok",
    });
  });
});

describe("ReviewPanel", () => {
  beforeEach(() => {
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.listDecks.mockReset();
    harness.addCard.mockReset();
    harness.createDeck.mockReset();
    harness.linkEntities.mockReset();
    harness.listDecks.mockResolvedValue([
      {
        id: "d1",
        title: "Git kartları",
        card_count: 12,
        due_count: 4,
        new_count: 2,
        created_at: "2026-09-01T10:00:00Z",
      },
    ]);
  });

  afterEach(cleanup);

  it("review blogunu ve gecikme durumunu gosterir", async () => {
    renderPanel();
    expect(await screen.findByText("Tekrar sayısı")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByText("Güven")).toBeTruthy();
    expect(screen.getByText("4/5")).toBeTruthy();
    expect(screen.getByText("%30")).toBeTruthy();
    expect(screen.getByText("3 gün gecikti")).toBeTruthy();
  });

  it("5 derece sunar ve secilen dereceyi POST eder; yeni aralik gosterilir", async () => {
    harness.apiPost.mockResolvedValue({
      ...review,
      interval_days: 4,
      next_review_at: "2026-09-14T10:00:00Z",
      review_count: 4,
    });
    renderPanel();

    const group = await screen.findByRole("radiogroup", { name: "Tekrar derecesi" });
    expect(within(group).getAllByRole("radio")).toHaveLength(REVIEW_GRADES.length);

    fireEvent.click(within(group).getByRole("radio", { name: /^Orta/ }));
    fireEvent.click(screen.getByRole("button", { name: "Tekrarı tamamla" }));

    await waitFor(() => expect(harness.apiPost).toHaveBeenCalledWith("/study/topics/t1/review", { grade: "medium" }));
    const next = await screen.findByRole("status");
    expect(next.textContent).toContain(`Sonraki tekrar: ${formatTrDate("2026-09-14T10:00:00Z")}`);
    expect(next.textContent).toContain("4 gün");
    expect(harness.invalidate).toHaveBeenCalledWith("study.write");
  });

  it("ok tuslariyla derece secilebilir (roving tabindex)", async () => {
    renderPanel();
    const group = await screen.findByRole("radiogroup", { name: "Tekrar derecesi" });
    // Hicbir derece secili degilken ilk ok ilk dereceyi secer.
    fireEvent.keyDown(group, { key: "ArrowRight" });
    expect(
      within(group)
        .getByRole("radio", { name: /^Unuttum/ })
        .getAttribute("aria-checked"),
    ).toBe("true");
    fireEvent.keyDown(group, { key: "ArrowRight" });
    expect(within(group).getByRole("radio", { name: /^Zor/ }).getAttribute("aria-checked")).toBe("true");
  });

  it("bagli desteleri listeler ve kullanici yazimiyla kart ekler", async () => {
    renderPanel();
    const openLink = await screen.findByRole("link", { name: /Deste aç/ });
    expect(openLink.getAttribute("href")).toBe("#/flashcard?deck=d1");
    expect(harness.listDecks).toHaveBeenCalledWith("t1");

    fireEvent.click(screen.getByRole("button", { name: "Kart ekle" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Ön yüz"), { target: { value: "git status" } });
    fireEvent.change(within(dialog).getByLabelText("Arka yüz"), { target: { value: "çalışma ağacı durumu" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kartı ekle" }));

    await waitFor(() => expect(harness.addCard).toHaveBeenCalledWith("d1", "git status", "çalışma ağacı durumu"));
    expect(harness.invalidate).toHaveBeenCalledWith("flashcard.write");
  });

  it("yeni deste olusturup konuya baglar (studies)", async () => {
    harness.createDeck.mockResolvedValue({ id: "d2", title: "Yeni deste" });
    renderPanel();
    fireEvent.click(await screen.findByRole("button", { name: /Yeni deste/ }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Deste adı"), { target: { value: "Yeni deste" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Oluştur" }));

    await waitFor(() => expect(harness.createDeck).toHaveBeenCalledWith("Yeni deste"));
    expect(harness.linkEntities).toHaveBeenCalledWith("d2", "t1", "studies");
  });
});
