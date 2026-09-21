// @vitest-environment jsdom

/**
 * Gun sayfasi: emek haritasindan gelen karenin dokumu.
 *
 * Sozlesme: SAYILAN isler (kind != null) once ve acik gelir; worker'in kendi
 * kayitlari (kind == null) ayri bolumde, varsayilan olarak KAPALI ve fiile gore
 * toplanmis durur -- gunun hikayesi 478 satir feed kaydiyla bogulmasin.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DayPage } from "./DayPage";

vi.mock("@/core/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), del: vi.fn(), patch: vi.fn(), put: vi.fn() },
  qs: (params: Record<string, unknown>) => {
    const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
    return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
  },
}));

import { api } from "@/core/api";

const apiGet = vi.mocked(api.get);

const DAY = "2026-08-20";

const EVENT = {
  id: 1,
  entity_id: "11111111-1111-1111-1111-111111111111",
  entity_type: "todo",
  verb: "todo.completed",
  payload: { title: "Raporu bitir" },
  occurred_at: `${DAY}T09:30:00+00:00`,
};

beforeEach(() => {
  apiGet.mockReset();
  location.hash = `#/day?d=${DAY}`;
  fireEvent(window, new HashChangeEvent("hashchange"));
  apiGet.mockImplementation(async (path: string) => {
    if (path.startsWith("/activity/day")) {
      return {
        day: DAY,
        events: [
          { ...EVENT, kind: "task" },
          {
            id: 2,
            entity_id: null,
            entity_type: "feed",
            verb: "source_sync.completed",
            payload: { count: 12 },
            occurred_at: `${DAY}T08:00:00+00:00`,
            kind: null,
            is_alert: false,
          },
          {
            id: 3,
            entity_id: null,
            entity_type: "feed",
            verb: "source_sync.completed",
            payload: { count: 5 },
            occurred_at: `${DAY}T07:00:00+00:00`,
            kind: null,
            is_alert: false,
          },
          {
            id: 4,
            entity_id: null,
            entity_type: "feed",
            verb: "rss.feed_failed",
            payload: { message: "zaman aşımı" },
            occurred_at: `${DAY}T06:00:00+00:00`,
            kind: null,
            is_alert: true,
          },
        ],
        kinds: { task: 1 },
        labels: { task: "görev" },
        total: 1,
        other: 3,
      };
    }
    throw new Error(`beklenmeyen çağrı: ${path}`);
  });
});

afterEach(cleanup);

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <DayPage />
    </QueryClientProvider>,
  );
}

describe("DayPage", () => {
  it("günün sayılan işlerini saatle listeler", async () => {
    renderPage();

    expect(await screen.findByText("O gün ne yaptın")).toBeTruthy();
    expect(screen.getByText(/Raporu bitir/)).toBeTruthy();
    expect(screen.getByText("görev")).toBeTruthy(); // MetricStrip rozeti
  });

  it("worker kayıtlarını varsayılan olarak kapalı ve fiile göre toplu gösterir", async () => {
    renderPage();

    const toggle = await screen.findByRole("button", { name: /göster/ });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    // Kapaliyken tek tek kayitlar gorunmez.
    expect(screen.queryByText("Kaynak senkronizasyonu tamamlandı")).toBeNull();

    fireEvent.click(toggle);

    await waitFor(() => expect(screen.getByRole("button", { name: /gizle/ })).toBeTruthy());
    const row = screen.getByText("Kaynak senkronizasyonu tamamlandı");
    expect(row).toBeTruthy();
    // Iki kayit tek satirda toplanir.
    expect(screen.getByText("2")).toBeTruthy();
  });

  it("uyarı taşıyan sistem kaydını vurgular (bayrak sunucudan gelir)", async () => {
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: /göster/ }));

    const alert = await screen.findByText("Besleme hata verdi");
    expect(alert.className).toContain("text-warn");
    expect(screen.getByText("Kaynak senkronizasyonu tamamlandı").className).not.toContain("text-warn");
  });

  it("saat ve gun gezinme baglantilari gun parametresini korur", async () => {
    const { container } = renderPage();

    await screen.findByText("O gün ne yaptın");
    const previous = container.querySelector<HTMLAnchorElement>('a[href*="/day?d=2026-08-19"]');
    expect(previous).toBeTruthy();
  });
});
