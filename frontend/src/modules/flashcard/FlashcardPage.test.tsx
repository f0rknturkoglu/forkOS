// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
  qs: (values: Record<string, string | number | undefined | null>) => {
    const query = new URLSearchParams(
      Object.entries(values)
        .filter(([, value]) => value !== undefined && value !== null && value !== "")
        .map(([key, value]) => [key, String(value)]),
    ).toString();
    return query ? `?${query}` : "";
  },
}));

import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";

const apiGet = vi.mocked(api.get);
const apiPost = vi.mocked(api.post);
const apiPatch = vi.mocked(api.patch);

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
  window.location.hash = "#/flashcard";
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
        reversible: false,
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

describe("FlashcardPage — kart yonetimi ve SRS", () => {
  it("filtre cipleri ve arama sunucu parametrelerine yansir", async () => {
    renderPage();
    fireEvent.click(await screen.findByText("Almanca"));

    fireEvent.click(await screen.findByRole("button", { name: "Zorlandıklarım" }));
    await waitFor(() => expect(apiGet.mock.calls.some(([path]) => String(path).includes("only_lapses=1"))).toBe(true));

    fireEvent.click(screen.getByRole("button", { name: "Tekrar Bekleyenler" }));
    await waitFor(() => expect(apiGet.mock.calls.some(([path]) => String(path).includes("due=1"))).toBe(true));

    fireEvent.change(screen.getByLabelText("Kart ara"), { target: { value: "haus" } });
    await waitFor(() => expect(apiGet.mock.calls.some(([path]) => String(path).includes("q=haus"))).toBe(true));
  });

  it("cift yonlu kart secenegi POST govdesine gider", async () => {
    renderPage();
    fireEvent.click(await screen.findByText("Almanca"));

    fireEvent.change(await screen.findByLabelText("Kart ön yüzü"), { target: { value: "Haus" } });
    fireEvent.change(screen.getByLabelText("Kart arka yüzü"), { target: { value: "Ev" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /Çift yönlü/ }));
    fireEvent.click(screen.getByRole("button", { name: /Ekle/ }));

    await waitFor(() =>
      expect(apiPost).toHaveBeenCalledWith("/flashcard/decks/deck-1/cards", {
        front: "Haus",
        back: "Ev",
        reversible: true,
      }),
    );
  });

  it("kart duzenleme modali PATCH atar ve askiya alma secenegini tasir", async () => {
    renderPage();
    fireEvent.click(await screen.findByText("Almanca"));

    fireEvent.click(await screen.findByRole("button", { name: '"Haus" kartını düzenle' }));
    const dialog = await screen.findByRole("dialog", { name: "Kartı düzenle" });
    fireEvent.change(within(dialog).getByLabelText("Kart arka yüzü"), { target: { value: "Das Haus" } });
    fireEvent.click(within(dialog).getByRole("checkbox", { name: /Askıya al/ }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Kaydet" }));

    await waitFor(() =>
      expect(apiPatch).toHaveBeenCalledWith("/flashcard/cards/card-1", {
        front: "Haus",
        back: "Das Haus",
        suspended: true,
      }),
    );
  });

  it("oturum dereceleri sonraki araligi gosterir, yanlislar tekrar edilebilir", async () => {
    renderPage();
    fireEvent.click(await screen.findByText("Almanca"));
    await screen.findByText("Haus");
    fireEvent.click(screen.getByRole("button", { name: /Tekrar başlat/ }));

    // Yeni kart (due_at null): Yine 10 dk, Zor/Iyi 1 gun, Kolay 4 gun.
    expect(await screen.findByRole("button", { name: /Yine.*10 dk/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Kart sorusu/ }));
    expect(await screen.findByRole("button", { name: /Kolay.*4 gün/ })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Yine/ }));
    await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/flashcard/cards/card-1/review", { grade: 0 }));

    // Oturum bitince tebrik + yanlislari tekrar et butonu.
    expect(await screen.findByText(/1 kart tekrar edildi/)).toBeTruthy();
    expect(screen.getByText(/%0 hatırlandı/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Yanlış yapılan kartları şimdi tekrar et/ }));
    expect(await screen.findByRole("button", { name: /Kart sorusu/ })).toBeTruthy();
  });
});

describe("TodayFlashcardWidget", () => {
  it("vadesi gelen desteleri listeler ve oturumu baslatir", async () => {
    const navigate = vi.fn();
    vi.doMock("@/app/router", () => ({ navigate, useHashRoute: () => ({ path: "/", params: new URLSearchParams() }) }));
    const { TodayFlashcardWidget } = await import("./TodayFlashcardWidget");
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <TodayFlashcardWidget />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("1 tekrar")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Hemen çalış/ }));
    expect(navigate).toHaveBeenCalledWith("/flashcard?review=due");
    vi.doUnmock("@/app/router");
  });
});
