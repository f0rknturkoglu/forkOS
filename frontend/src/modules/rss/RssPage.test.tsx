// @vitest-environment jsdom
/**
 * RSS okuyucu sayfası — besleme durumu sözlüğü (tek kaynak: @/core/sourceStatus).
 *
 * Kilitlenen davranış:
 *  - Kapatılan beslemenin durum led'i NÖTR "kapalı" der; kırmızı "hata" demez.
 *    (Eski kod `error_count > 0 || !active` ikilisini "broken" sayıp kırmızı
 *    gösteriyordu: bilerek kapatılan besleme bozuk sanılıyordu.)
 *  - Hata biriktiren besleme kırmızı ve etiketinde hata sayısını taşır.
 *  - Besleme listesi alınamazsa "henüz besleme yok" DENMEZ: sorgu hatası
 *    boşluk değildir.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { RssPage } from "./RssPage";

let feedsBody: unknown = [];
let feedsStatus = 200;
let itemsStatus = 200;

const FETCHED_AT = "2026-09-20T08:00:00.000Z";

function feed(overrides: Record<string, unknown>): Record<string, unknown> {
  return {
    id: "f1",
    title: "Besleme",
    url: "https://example.com/rss",
    site_url: null,
    favicon_url: null,
    category: null,
    active: true,
    error_count: 0,
    last_status: "ok",
    last_fetched_at: FETCHED_AT,
    unread: 0,
    ...overrides,
  };
}

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

beforeEach(() => {
  feedsBody = [];
  feedsStatus = 200;
  itemsStatus = 200;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      const path = url.pathname.replace(/^\/api/, "");
      if (path === "/rss/feeds") return json(feedsBody, feedsStatus);
      if (path === "/rss/stats")
        return json({ feeds: 1, active_feeds: 1, failing_feeds: 0, unread: 0, today: 0, saved: 0 });
      if (path.startsWith("/rss/items")) return json([], itemsStatus);
      return json({}, 200);
    }),
  );
});

afterEach(cleanup);

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <RssPage />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("RSS okuyucu durum dili", () => {
  it("shows pending refresh, prevents a second request and reports completion", async () => {
    let finish!: (response: Response) => void;
    const original = fetch;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        if (String(input).includes("/rss/refresh-all"))
          return new Promise<Response>((resolve) => {
            finish = resolve;
          });
        return original(input, init);
      }),
    );
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Tümünü tazele" }));
    const pending = await screen.findByRole("button", { name: "Yenileniyor…" });
    expect((pending as HTMLButtonElement).disabled).toBe(true);
    expect(pending.getAttribute("aria-busy")).toBe("true");
    finish(json({ started: 1, added: 2 }));
    expect(await screen.findByText("1 besleme yenilendi.")).toBeTruthy();
    expect(((await screen.findByRole("button", { name: "Tümünü tazele" })) as HTMLButtonElement).disabled).toBe(false);
  });
  it("kapatılan besleme nötr 'kapalı' led'i taşır — kırmızı hata değil", async () => {
    feedsBody = [feed({ id: "f1", title: "Kapalı Besleme", active: false })];
    renderPage();

    await screen.findByText("Kapalı Besleme");
    const led = screen.getByRole("img", { name: "kapalı" });
    expect(led.className).toContain("bg-icon");
    expect(led.className).not.toContain("bg-danger");
  });

  it("hata biriktiren besleme kırmızı led ve sayılı etiket taşır", async () => {
    feedsBody = [feed({ id: "f1", title: "Bozuk Besleme", error_count: 5, last_status: "error" })];
    renderPage();

    await screen.findByText("Bozuk Besleme");
    const led = screen.getByRole("img", { name: "5 hata" });
    expect(led.className).toContain("bg-danger");
  });

  it("tek boş koşu bilgi düzeyinde kalır: 'yeni kayıt yok'", async () => {
    feedsBody = [feed({ id: "f1", title: "Sessiz Besleme", last_status: "empty" })];
    renderPage();

    await screen.findByText("Sessiz Besleme");
    const led = screen.getByRole("img", { name: "yeni kayıt yok" });
    expect(led.className).toContain("bg-warn");
    expect(led.className).not.toContain("bg-danger");
  });

  it("besleme listesi alınamazsa 'henüz besleme yok' denmez", async () => {
    feedsStatus = 503;
    renderPage();

    expect(await screen.findByText(/Besleme listesi alınamadı/)).toBeTruthy();
    expect(screen.queryByText(/Henüz besleme yok/)).toBeNull();
  });

  it("yazı listesi alınamazsa 'yazı yok' denmez", async () => {
    itemsStatus = 503;
    renderPage();

    expect(await screen.findByText(/Yazılar alınamadı/)).toBeTruthy();
    expect(screen.queryByText(/Bu görünümde yazı yok/)).toBeNull();
  });
});
