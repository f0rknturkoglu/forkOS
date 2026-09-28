// @vitest-environment jsdom
/**
 * StatusLed paneli — dürüstlük sözleşmesi.
 *
 * LED'in RENGİ kaynak basıncına göre yanar (o karar korunur); ama panel bir
 * sorgu düştüğünde/yüklendiğinde "beslemeler sağlıklı" DEMEZ, satır satır
 * "bilinmiyor" der. Kaynak satırında yalnız `attention` işaretli koşular
 * (hata/kısmi/yarım kaldı) sayılır; `empty` ve `disabled` sayılmaz.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { StatusLed } from "@/core/StatusLed";
import type { SourceHealth } from "@/core/types";

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

const STATS = {
  cpu_pct: 12,
  load: [0.5],
  cpu_count: 10,
  mem_total_kb: 16_000_000,
  mem_available_kb: 8_000_000,
  disk: { total: 1_000_000_000_000, free: 500_000_000_000, path: "/app" },
  uptime_s: 3_600,
  worker: { status: "healthy", heartbeat_at: "2026-09-20T10:00:00.000Z" },
};

function run(source: string, status: string): SourceHealth {
  return {
    circuit_open: false,
    consecutive_failures: 0,
    source,
    status,
    items_found: 3,
    items_seen: 3,
    error: null,
    started_at: "2026-09-20T10:00:00.000Z",
    finished_at: "2026-09-20T10:00:02.000Z",
  };
}

type Answer = Response | Error | Promise<Response>;

/** TS lib hedefi ES2024 degil: kucuk bir ertelenmis soz yardimcisi. */
function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

/** Hic oturmeyen yanit: "yukleniyor" durumunu sabitler. */
function pendingResponse(): Promise<Response> {
  return deferred<Response>().promise;
}

/** Mikro gorev + effect kuyrugunu bosaltir (bekleyen sorgular beklemede kalir). */
function flush(): Promise<void> {
  const { promise, resolve } = deferred<void>();
  setTimeout(resolve, 0);
  return promise;
}

function serve(answers: { stats?: Answer; sources?: Answer; rss?: Answer }) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      const answer = url.includes("/system/stats")
        ? answers.stats
        : url.includes("/sources/health")
          ? answers.sources
          : answers.rss;
      if (answer instanceof Error) return Promise.reject(answer);
      return Promise.resolve(answer ?? json({}));
    }),
  );
}

/** LED'e tiklayip paneli acar; panel elemani sorgular oturdukca yerinde kalir. */
function openPanel(): HTMLElement {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const { container } = render(
    <QueryClientProvider client={client}>
      <StatusLed />
    </QueryClientProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: /^Sistem durumu/ }));
  const panel = container.querySelector<HTMLElement>('[role="dialog"]');
  if (!panel) throw new Error("durum paneli açılmadı");
  return panel;
}

/** Panel satirinin metni (etiket + chip) — satir satir dürüstlügü ölcer. */
function rowText(panel: HTMLElement, label: string): string {
  const item = Array.from(panel.querySelectorAll("li")).find((li) => li.textContent?.startsWith(label));
  return item?.textContent ?? "";
}

beforeEach(() => {
  Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("StatusLed paneli", () => {
  it("besleme sorgusu düştüğünde besleme satırı bilinmiyor der", async () => {
    serve({ stats: json(STATS), sources: json([]), rss: json({}, 500) });
    const panel = openPanel();

    await waitFor(() => expect(rowText(panel, "Yerel API")).toBe("Yerel APIsağlıklı"));
    expect(rowText(panel, "RSS")).toBe("RSSbilinmiyor");
    expect(panel.textContent).not.toContain("Kaynaklar ve beslemeler sağlıklı.");
    expect(panel.textContent).not.toContain("beslemeler sağlıklı");
  });

  it("besleme ucu hiç yanıt vermezken de sağlıklı demez", async () => {
    serve({ stats: json(STATS), sources: json([]), rss: new TypeError("Failed to fetch") });
    const panel = openPanel();

    await waitFor(() => expect(rowText(panel, "Yerel API")).toBe("Yerel APIsağlıklı"));
    expect(rowText(panel, "RSS")).toBe("RSSbilinmiyor");
  });

  it("yüklenirken satırlar bilinmiyor der (sahte yeşil yok)", async () => {
    serve({
      stats: pendingResponse(),
      sources: pendingResponse(),
      rss: pendingResponse(),
    });
    const panel = openPanel();
    await act(async () => {
      await flush();
    });

    expect(panel.textContent).not.toMatch(/sağlıklı/i);
    expect(rowText(panel, "Kaynaklar")).toBe("Kaynaklarbilinmiyor");
    expect(rowText(panel, "Worker")).toBe("Workerbilinmiyor");
    expect(rowText(panel, "Yerel API")).toBe("Yerel APIbilinmiyor");
  });

  it("kısmi ilgi ister, boş koşu istemez; LED rengi kaynak basıncına göre YANMAZ", async () => {
    serve({
      stats: json(STATS),
      sources: json([run("osym", "ok"), run("bulten", "empty"), run("linkedin", "partial")]),
      rss: json({ feeds: 3, active_feeds: 2, failing_feeds: 0, unread: 4 }),
    });
    const panel = openPanel();

    await waitFor(() => expect(rowText(panel, "Kaynaklar")).toBe("Kaynaklar1 ilgi istiyor"));
    expect(rowText(panel, "RSS")).toBe("RSSsağlıklı");
    expect(panel.textContent).toContain("CPU");
    // Kaynakta ilgi isteyen koşu var ama LED yeşil kalır: renk kaynak basıncı.
    const dot = document.querySelector<HTMLElement>("button[aria-label] > span");
    expect(dot?.className).toContain("bg-ok");
  });

  it("tek boş koşu kaynak satırını kirletmez", async () => {
    serve({
      stats: json(STATS),
      sources: json([run("bulten", "empty")]),
      rss: json({ feeds: 1, active_feeds: 1, failing_feeds: 0, unread: 0 }),
    });
    const panel = openPanel();

    await waitFor(() => expect(rowText(panel, "Kaynaklar")).toBe("Kaynaklarsorun yok"));
  });

  it("kapalı worker nötrdür, hata gibi gösterilmez", async () => {
    serve({
      stats: json({ ...STATS, worker: { status: "disabled", heartbeat_at: null } }),
      sources: json([]),
      rss: json({ feeds: 1, active_feeds: 1, failing_feeds: 0, unread: 0 }),
    });
    const panel = openPanel();

    await waitFor(() => expect(rowText(panel, "Worker")).toBe("Workerkapalı"));
    expect(rowText(panel, "Yerel API")).toBe("Yerel APIsağlıklı");
  });

  it("yerel API düştüğünde uyarıyı ve bilinmiyor satırını gösterir", async () => {
    serve({ stats: new TypeError("Failed to fetch"), sources: json([]), rss: json({}) });
    const panel = openPanel();

    await waitFor(() => expect(panel.textContent).toContain("Yerel API'ye ulaşılamıyor."));
    expect(rowText(panel, "Yerel API")).toBe("Yerel APIbilinmiyor");
    // Kaynak listesi bos: "sorun yok" degil, "kayit yok".
    expect(rowText(panel, "Kaynaklar")).toBe("Kaynaklarkayıt yok");
  });
});
