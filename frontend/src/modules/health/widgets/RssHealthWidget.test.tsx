// @vitest-environment jsdom
/**
 * RSS Sağlığı widget'ı — durum sözlüğü ve dürüstlük kuralları.
 *
 * Kilitlenen davranış:
 *  - Bilerek KAPATILAN besleme "kapalı"dır (nötr), bozuk DEĞİLDİR; kırmızı
 *    gösterilmez.
 *  - Sağlık widget'ı teşhis eder, kaydı yönetmez: yıkıcı toplu silme YOKTUR,
 *    yerine RSS modülüne derin bağlantı vardır.
 *  - Tek boş koşu ("yeni kayıt yok") sorun sayılmaz.
 *  - Sorgu düşerse/eksikse "hepsi sağlıklı" DENMEZ; kısmi durum dürüstçe yazılır.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { RssHealthWidget } from "./RssHealthWidget";

type Call = { method: string; path: string };

let calls: Call[] = [];
let feedsBody: unknown = [];
let feedsStatus = 200;
let statsBody: unknown = { feeds: 0, active_feeds: 0, failing_feeds: 0, unread: 0 };
let statsStatus = 200;

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
  calls = [];
  feedsBody = [];
  feedsStatus = 200;
  statsBody = { feeds: 0, active_feeds: 0, failing_feeds: 0, unread: 0 };
  statsStatus = 200;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const path = url.pathname.replace(/^\/api/, "");
      calls.push({ method: (init?.method ?? "GET").toUpperCase(), path });
      if (path === "/rss/feeds") return json(feedsBody, feedsStatus);
      if (path === "/rss/stats") return json(statsBody, statsStatus);
      if (path === "/rss/refresh-all") return json({ started: 2 });
      if (path.startsWith("/rss/feeds/")) return json({ ok: true });
      return json({ detail: "yok" }, 404);
    }),
  );
});

afterEach(cleanup);

function renderWidget() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <RssHealthWidget />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("RSS Sağlığı widget'ı", () => {
  it("bilerek kapatılan besleme nötr 'kapalı' der — kırmızı 'kapatıldı' değil", async () => {
    feedsBody = [feed({ id: "f1", title: "Kapalı Besleme", active: false })];
    statsBody = { feeds: 1, active_feeds: 0, failing_feeds: 1, unread: 0 };
    renderWidget();

    await screen.findByText("Kapalı Besleme");
    const chip = screen.getByText("kapalı").className;
    expect(chip).toContain("text-muted");
    expect(chip).not.toContain("text-danger");
    // Eski yalan: kapatılan besleme "kapatıldı" + danger olarak gösteriliyordu.
    expect(screen.queryByText("kapatıldı")).toBeNull();
    // Kapalı besleme "ilgi istiyor" sayılmaz ve yeşil "hepsi sağlıklı" da denmez.
    expect(screen.queryByText(/ilgi istiyor/)).toBeNull();
    expect(screen.queryByText(/Bütün beslemeler sağlıklı/)).toBeNull();
  });

  it("hata biriktiren besleme tehlike rozeti taşır ve ilgi listesine girer", async () => {
    feedsBody = [feed({ id: "f1", title: "Bozuk Besleme", error_count: 5, last_status: "error" })];
    statsBody = { feeds: 1, active_feeds: 1, failing_feeds: 1, unread: 0 };
    renderWidget();

    await screen.findByText("Bozuk Besleme");
    expect(screen.getByText("5 hata").className).toContain("text-danger");
    expect(screen.getByText(/ilgi istiyor/)).toBeTruthy();
  });

  it("tek boş koşu sorun değildir: 'yeni kayıt yok' bilgi rozeti, ilgi listesine girmez", async () => {
    feedsBody = [feed({ id: "f1", title: "Sessiz Besleme", last_status: "empty" })];
    statsBody = { feeds: 1, active_feeds: 1, failing_feeds: 0, unread: 0 };
    renderWidget();

    await screen.findByText("Sessiz Besleme");
    const chip = screen.getByText("yeni kayıt yok").className;
    expect(chip).toContain("text-warn");
    expect(chip).not.toContain("text-danger");
    expect(screen.queryByText(/ilgi istiyor/)).toBeNull();
    // Tek boş koşu "hata" diye de gösterilmez.
    expect(screen.queryByText(/\d+ hata/)).toBeNull();
  });

  it("hiç çekilmemiş besleme nötr 'çekilmedi' der", async () => {
    feedsBody = [feed({ id: "f1", title: "Yeni Besleme", last_status: null, last_fetched_at: null })];
    statsBody = { feeds: 1, active_feeds: 1, failing_feeds: 0, unread: 0 };
    renderWidget();

    await screen.findByText("Yeni Besleme");
    expect(screen.getByText("çekilmedi").className).toContain("text-muted");
  });

  it("besleme listesi alınamazsa 'hepsi sağlıklı' DENMEZ", async () => {
    feedsStatus = 503;
    statsBody = { feeds: 1, active_feeds: 1, failing_feeds: 0, unread: 0 };
    renderWidget();

    await screen.findByText(/Besleme listesi alınamadı/);
    expect(screen.getByText(/durum bilinmiyor/)).toBeTruthy();
    expect(screen.queryByText(/Bütün beslemeler sağlıklı/)).toBeNull();
    expect(screen.queryByText(/sağlıklı/)).toBeNull();
  });

  it("özet ucu düşerse okunabilen kısım korunur, yeşil cümle kurulmaz", async () => {
    feedsBody = [feed({ id: "f1", title: "Bozuk Besleme", error_count: 5, last_status: "error" })];
    statsStatus = 503;
    renderWidget();

    await screen.findByText(/RSS özeti alınamadı/);
    expect(screen.queryByText(/Bütün beslemeler sağlıklı/)).toBeNull();
    // Okunabilen kısım kaybolmaz: besleme listesi ve sorunu yerinde kalır.
    expect(screen.getByText("Bozuk Besleme")).toBeTruthy();
    expect(screen.getByText("5 hata")).toBeTruthy();
  });

  it("özet ucu düşerse beslemeler temiz olsa bile 'hepsi sağlıklı' denmez", async () => {
    feedsBody = [feed({ id: "f1", title: "Sorunsuz Besleme" })];
    statsStatus = 503;
    renderWidget();

    await screen.findByText(/RSS özeti alınamadı/);
    expect(screen.getByText(/durum bilinmiyor/)).toBeTruthy();
    expect(screen.queryByText(/Bütün beslemeler sağlıklı/)).toBeNull();
  });

  it("tüm beslemeler gerçekten sağlıklıysa yeşil cümle kurulur", async () => {
    feedsBody = [feed({ id: "f1", title: "Sorunsuz Besleme" })];
    statsBody = { feeds: 1, active_feeds: 1, failing_feeds: 0, unread: 0 };
    renderWidget();

    expect(await screen.findByText(/Bütün beslemeler sağlıklı/)).toBeTruthy();
    // Sağlıklı besleme listede tekrar edilmez: yalnız ilgi isteyenler listelenir.
    expect(screen.queryByText("Sorunsuz Besleme")).toBeNull();
  });

  it("sağlık yüzeyi yıkıcı toplu silme taşımaz; RSS'i yönet bağlantısı verir", async () => {
    feedsBody = [
      feed({ id: "f1", title: "Bozuk Besleme", error_count: 5, last_status: "error" }),
      feed({ id: "f2", title: "Kapalı Besleme", active: false }),
    ];
    statsBody = { feeds: 2, active_feeds: 1, failing_feeds: 2, unread: 0 };
    const { container } = renderWidget();

    await screen.findByText("Kapalı Besleme");
    // Eylem yüzeyi TAM olarak budur: [Tümünü tazele] + besleme başına [Çek].
    // Eski yıkıcı toplu silme düğmesi ("N sorunlu sil") geri gelirse bu düşer.
    const actions = screen.getAllByRole("button").map((button) => button.textContent?.trim());
    expect(actions).toEqual(["Tümünü tazele", "Çek", "Çek"]);
    expect(container.textContent).not.toMatch(/sil/i);
    expect(calls.filter((call) => call.method === "DELETE")).toEqual([]);

    const link = screen.getByRole("link", { name: /RSS'i yönet/ });
    expect(link.getAttribute("href")).toBe("#/rss");
  });

  it("gerçek aksiyonlar korunur: tümünü tazele ve tek beslemeyi çek", async () => {
    feedsBody = [feed({ id: "f1", title: "Bozuk Besleme", error_count: 5, last_status: "error" })];
    statsBody = { feeds: 1, active_feeds: 1, failing_feeds: 1, unread: 0 };
    renderWidget();

    await screen.findByText("Bozuk Besleme");
    fireEvent.click(screen.getByRole("button", { name: /Tümünü tazele/ }));
    // Tek besleme cekme dugmesinin erisilebilir adi title'indan gelir.
    const single = screen.getByRole("button", { name: "Bu beslemeyi şimdi çek" });
    fireEvent.click(single);

    expect(await screen.findByText(/besleme yenilendi/)).toBeTruthy();
    await waitFor(() => expect(calls.some((call) => call.path === "/rss/feeds/f1/refresh")).toBe(true));
    expect(calls.some((call) => call.path === "/rss/refresh-all")).toBe(true);
  });
});
