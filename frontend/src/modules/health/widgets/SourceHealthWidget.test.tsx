// @vitest-environment jsdom
/**
 * Kaynak Sağlığı widget'ı — dürüstlük sözleşmesi.
 *
 * NO DATA ≠ HEALTHY · QUERY ERROR ≠ HEALTHY · UNKNOWN ≠ HEALTHY
 * Tek `empty` koşu bilgilendirmedir, `disabled` nötrdür; ikisi de sorun değil.
 * Kopyala eylemi Markdown tanılama paketi üretir ve sorgu düştüğünde de çalışır.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "@/core/ui";
import { SourceHealthWidget } from "./SourceHealthWidget";
import type { SourceHealth } from "@/core/types";

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

function run(overrides: Partial<SourceHealth>): SourceHealth {
  return {
    circuit_open: false,
    consecutive_failures: 0,
    source: "osym",
    status: "ok",
    items_found: 3,
    error: null,
    started_at: "2026-09-20T10:00:00.000Z",
    finished_at: "2026-09-20T10:00:02.000Z",
    ...overrides,
  };
}

let copied = "";
const writeText = vi.fn((text: string) => {
  copied = text;
  return Promise.resolve();
});

function serve(response: Response | Error | Promise<Response>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => (response instanceof Error ? Promise.reject(response) : Promise.resolve(response))),
  );
}

function renderWidget() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <SourceHealthWidget />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  copied = "";
  writeText.mockClear();
  Object.defineProperty(window.navigator, "clipboard", { configurable: true, value: { writeText } });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/** TS lib hedefi ES2024 degil: kucuk bir ertelenmis soz yardimcisi. */
function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

describe("SourceHealthWidget", () => {
  it("sorgu düştüğünde 'sağlıklı' DEMEZ, bilinmiyor der ve sahte sıfır göstermez", async () => {
    serve(new TypeError("Failed to fetch"));
    const { container } = renderWidget();

    expect(await screen.findByText("Kaynak sağlığı alınamadı.")).toBeTruthy();
    expect(container.textContent).toContain("durum bilinmiyor");
    expect(container.textContent).not.toMatch(/sağlıklı/i);
    expect(container.textContent).not.toContain("Bütün kaynaklar son koşumda sağlıklı görünüyor.");
  });

  it("yüklenirken sahte sıfır ve 'sağlıklı' göstermez", () => {
    serve(deferred<Response>().promise);
    const { container } = renderWidget();

    expect(container.textContent).not.toMatch(/\d/);
    expect(container.textContent).not.toMatch(/sağlıklı/i);
  });

  it("tek boş koşu sorun sayılmaz, bilgilendirme olarak yazılır", async () => {
    serve(json([run({ source: "bulten", status: "empty", items_found: 0 })]));
    const { container } = renderWidget();

    expect(await screen.findByText("İlgi isteyen kaynak yok.")).toBeTruthy();
    expect(screen.getByText(/1 kaynak son koşumda yeni kayıt bulamadı/)).toBeTruthy();
    expect(screen.getByText(/bilgilendirme, sorun değil/)).toBeTruthy();
    // Uyarı listesi (kırmızı yüzey) çizilmez.
    expect(container.querySelector(".bg-danger-surface")).toBeNull();
  });

  it("kapalı kaynak nötrdür ve ilgi istemez", async () => {
    serve(json([run({ source: "linkedin", status: "disabled", items_found: 0 })]));
    const { container } = renderWidget();

    expect(await screen.findByText("İlgi isteyen kaynak yok.")).toBeTruthy();
    expect(screen.getByText(/1 kaynak kapalı/)).toBeTruthy();
    expect(container.querySelector(".bg-danger-surface")).toBeNull();
  });

  it("hata veren kaynağı tek sözlükten etiketler ve tanılama paketini kopyalar", async () => {
    serve(
      json([
        run({ source: "osym" }),
        run({ source: "forkjob_core:linkedin", status: "error", error: "429 Too Many Requests", finished_at: null }),
        run({ source: "bulten", status: "empty", items_found: 0 }),
      ]),
    );
    renderWidget();

    expect(await screen.findByText("hata")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Tanılamayı kopyala/ }));

    await waitFor(() => expect(copied).toContain("# forkOS Source Diagnostics"));
    expect(copied).toContain("## Problem 1");
    expect(copied).toContain("Source: forkjob_core:linkedin");
    expect(copied).toContain("Source count: 3");
    expect(copied).toContain("429 Too Many Requests");
    expect(copied.match(/## Problem /g)?.length).toBe(1); // sağlıklı ve boş koşu girmiyor
    expect(copied).not.toContain("Source: osym");
    expect(copied).not.toContain("Source: bulten");
    expect((await screen.findByRole("status")).textContent).toContain("1 kaynak sorunu panoya kopyalandı.");
  });

  it("sorgu düşse de tanılamayı kopyalar ve bilinmeyen durumu açıkça yazar", async () => {
    serve(new TypeError("Failed to fetch"));
    renderWidget();

    await screen.findByText("Kaynak sağlığı alınamadı.");
    fireEvent.click(screen.getByRole("button", { name: /Tanılamayı kopyala/ }));

    await waitFor(() => expect(copied).toContain("Unknown sections: sources"));
    expect(copied).toContain("Source count: unknown");
    expect((await screen.findByRole("status")).textContent).toContain("Kaynak sağlığı bilinmiyor");
  });
});
