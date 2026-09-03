// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { FlashcardPage } from "./FlashcardPage";

vi.mock("@/lib/hooks", () => ({
  useOnline: () => true,
  useDebounced: (value: string) => value,
}));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/core/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    del: vi.fn(),
    upload: vi.fn(),
  },
  qs: (values: Record<string, string>) => {
    const query = new URLSearchParams(values).toString();
    return query ? `?${query}` : "";
  },
}));

import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";

const apiGet = vi.mocked(api.get);
const apiPost = vi.mocked(api.post);

const deck = {
  id: "deck-1",
  title: "Almanca",
  card_count: 1,
  due_count: 1,
  new_count: 0,
  created_at: "2026-09-01T00:00:00Z",
};
const card = {
  id: "card-1",
  deck_id: "deck-1",
  front: "Haus",
  back: "Ev",
  interval_days: 0,
  ease: 2.5,
  due_at: null,
  reps: 0,
  lapses: 0,
  suspended: false,
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <FlashcardPage />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiGet.mockImplementation(async (path: string) => {
    if (path === "/flashcard/decks") return [deck];
    if (path.startsWith("/flashcard/decks/deck-1/cards")) return [card];
    if (path.startsWith("/entities/")) return [];
    if (path.startsWith("/search")) return {};
    return [];
  });
  apiPost.mockImplementation(async (path: string, body?: unknown) => {
    if (path === "/flashcard/decks") return deck;
    if (path.includes("/review")) return { due_at: "2026-09-02T00:00:00Z", interval_days: 1 };
    if (path.includes("/cards")) return card;
    return {};
  });
});

afterEach(cleanup);

describe("FlashcardPage", () => {
  it("destek listeler, yenisini olusturur ve tazeler", async () => {
    renderPage();

    expect(await screen.findByText("Almanca")).toBeTruthy();
    // Destek satirinda sayaclar (1 tekrar / 1 kart).
    expect(screen.getByText("1 tekrar")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Yeni destek adı"), { target: { value: "İspanyolca" } });
    fireEvent.click(screen.getByRole("button", { name: /Oluştur/ }));

    await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/flashcard/decks", { title: "İspanyolca" }));
    expect(invalidateAfter).toHaveBeenCalledWith("flashcard.write");
  });

  it("destegi acar ve kart ekler", async () => {
    renderPage();

    fireEvent.click(await screen.findByText("Almanca"));

    expect(await screen.findByLabelText("Kart ön yüzü")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Kart ön yüzü"), { target: { value: "Apfel" } });
    fireEvent.change(screen.getByLabelText("Kart arka yüzü"), { target: { value: "Elma" } });
    fireEvent.click(screen.getByRole("button", { name: /Ekle/ }));

    await waitFor(() =>
      expect(apiPost).toHaveBeenCalledWith("/flashcard/decks/deck-1/cards", {
        front: "Apfel",
        back: "Elma",
      }),
    );
  });

  it("tekrar oturumu: karti cevirir, derece gonderir, ozetle biter", async () => {
    renderPage();

    fireEvent.click(await screen.findByText("Almanca"));
    // Kart listesi yuklenene kadar buton disabled -- liste gorununce tiklanabilir.
    await screen.findByText("Haus");
    fireEvent.click(screen.getByRole("button", { name: /Tekrar başlat/ }));

    // On yuz gorunur; cevrilince derece butonlari cikar.
    expect(await screen.findByText("Haus")).toBeTruthy();
    expect(screen.getByText(/Çevirmek için/)).toBeTruthy();
    fireEvent.click(screen.getByText("Haus"));
    expect(await screen.findByText("Ev")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /İyi/ }));

    await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/flashcard/cards/card-1/review", { grade: 2 }));
    // Tek kartli kuyruk bitince ozet.
    expect(await screen.findByText(/1 kart tekrar edildi/)).toBeTruthy();
  });

  it("kuyruk bosken oturum 'sirasi yok' der", async () => {
    apiGet.mockImplementation(async (path: string) => {
      if (path === "/flashcard/decks") return [deck];
      // Yonetim listesinde kart var ama tekrar kuyrugu (due=1) bos.
      if (path === "/flashcard/decks/deck-1/cards") return [card];
      if (path === "/flashcard/decks/deck-1/cards?due=1") return [];
      if (path.startsWith("/entities/")) return [];
      return {};
    });
    renderPage();

    fireEvent.click(await screen.findByText("Almanca"));
    await screen.findByText("Haus");
    fireEvent.click(screen.getByRole("button", { name: /Tekrar başlat/ }));

    expect(await screen.findByText(/Sırada kart yok/)).toBeTruthy();
  });
});
