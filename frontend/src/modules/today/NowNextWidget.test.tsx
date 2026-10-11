// @vitest-environment jsdom
/**
 * Şimdi / Sırada sözleşmesi (P2 §21).
 *
 * Home'un en yüksek görsel önceliği: "şu an ne yapıyorum, sırada ne var?".
 * Yüzey takvimli satırlardan yalnız 1 güncel + en fazla 3 sıradaki kaydı
 * gösterir; boşsa hiç çizilmez.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NowNextWidget } from "./NowNextWidget";

const apiGet = vi.fn();

vi.mock("@/core/api", () => ({
  api: { get: (...args: unknown[]) => apiGet(...args) },
  qs: vi.fn(() => ""),
}));

vi.mock("@/core/entityRegistry", () => ({
  entityRoute: (type: string, id: string) => `#/entity/${type}/${id}`,
}));

const MINUTE = 60_000;

function row(overrides: Record<string, unknown> = {}) {
  return {
    id: "r1",
    title: "Toplantı",
    kind: "calendar",
    source: "calendar",
    completed: false,
    context_only: false,
    read_only: true,
    starts_at: new Date(Date.now() - 10 * MINUTE).toISOString(),
    duration_min: 30,
    entity_id: "e1",
    entity_type: "opportunity",
    ...overrides,
  };
}

function serveTimed(rows: unknown[]) {
  apiGet.mockResolvedValue({
    day: "2026-01-01",
    timed: rows,
    checklist: [],
    completed: [],
    suggestions: { todos: [], rss: [], flashcards: [], study: [], career: [] },
  });
}

function renderWidget() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <NowNextWidget />
    </QueryClientProvider>,
  );
}

describe("NowNextWidget", () => {
  beforeEach(() => apiGet.mockReset());
  afterEach(cleanup);

  it("süren kaydı 'şimdi', sonrakileri 'sırada' gösterir", async () => {
    serveTimed([
      row(),
      row({ id: "r2", title: "Kod incelemesi", starts_at: new Date(Date.now() + 60 * MINUTE).toISOString() }),
      row({ id: "r3", title: "Spor", starts_at: new Date(Date.now() + 120 * MINUTE).toISOString() }),
    ]);
    renderWidget();

    expect(await screen.findByText("Toplantı")).toBeTruthy();
    expect(screen.getByText("şimdi")).toBeTruthy();
    expect(screen.getByText("Kod incelemesi")).toBeTruthy();
    expect(screen.getByText("Spor")).toBeTruthy();
    expect(screen.getAllByText("sırada").length).toBe(2);
  });

  it("güncel kayıt yoksa yalnız sıradakileri gösterir ve 3 ile sınırlar", async () => {
    serveTimed(
      Array.from({ length: 5 }, (_, index) =>
        row({
          id: `r${index}`,
          title: `İş ${index + 1}`,
          starts_at: new Date(Date.now() + (index + 1) * 60 * MINUTE).toISOString(),
        }),
      ),
    );
    renderWidget();

    expect(await screen.findByText("İş 1")).toBeTruthy();
    expect(screen.getAllByText("sırada").length).toBe(3);
    expect(screen.queryByText("İş 4")).toBeNull();
    expect(screen.queryByText("şimdi")).toBeNull();
  });

  it("bitmiş ve bağlam satırlarını yok sayar", async () => {
    serveTimed([
      row({ id: "past", title: "Bitmiş toplantı", starts_at: new Date(Date.now() - 120 * MINUTE).toISOString() }),
      row({ id: "done", title: "Tamamlanan", completed: true }),
      row({ id: "ctx", title: "Bağlam", context_only: true }),
    ]);
    const { container } = renderWidget();

    await waitFor(() => expect(apiGet).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });

  it("takvimli satır yoksa hiçbir şey çizmez", async () => {
    serveTimed([]);
    const { container } = renderWidget();

    await waitFor(() => expect(apiGet).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });

  it("satır kaydın kendi rotasına gider", async () => {
    serveTimed([row({ starts_at: new Date(Date.now() + 30 * MINUTE).toISOString() })]);
    renderWidget();

    const link = await screen.findByRole("link", { name: /Toplantı/ });
    expect(link.getAttribute("href")).toBe("#/entity/opportunity/e1");
  });

  it("süre verilmemiş kaydı 30 dakikalık blok sayar", async () => {
    // Başlangıç 20 dk önce: varsayılan 30 dk blok içinde → hâlâ "şimdi".
    serveTimed([row({ duration_min: null, starts_at: new Date(Date.now() - 20 * MINUTE).toISOString() })]);
    renderWidget();

    expect(await screen.findByText("şimdi")).toBeTruthy();
  });
});
