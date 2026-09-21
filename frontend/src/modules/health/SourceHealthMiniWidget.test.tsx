// @vitest-environment jsdom
/**
 * Üst şerit kaynak özeti — dürüstlük sözleşmesi.
 *
 * Sorgu düşerken "Kaynaklar sağlıklı." DENMEZ; tek `empty` koşu ve `disabled`
 * kaynak sorun sayılmaz.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SourceHealthMiniWidget } from "./SourceHealthMiniWidget";
import type { SourceHealth } from "@/core/types";

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

function run(source: string, status: string): SourceHealth {
  return {
    circuit_open: false,
    consecutive_failures: 0,
    source,
    status,
    items_found: 0,
    error: null,
    started_at: "2026-09-20T10:00:00.000Z",
    finished_at: null,
  };
}

function serve(response: Response | Error) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => (response instanceof Error ? Promise.reject(response) : Promise.resolve(response))),
  );
}

function renderWidget() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SourceHealthMiniWidget />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("SourceHealthMiniWidget", () => {
  it("sorgu düştüğünde 'sağlıklı' demez", async () => {
    serve(new TypeError("Failed to fetch"));
    const { container } = renderWidget();

    expect(await screen.findByText("Kaynak sağlığı alınamadı.")).toBeTruthy();
    expect(container.textContent).not.toMatch(/sağlıklı/i);
  });

  it("tek boş koşuyu sorun saymaz", async () => {
    serve(json([run("bulten", "empty")]));
    const { container } = renderWidget();

    expect(await screen.findByText("İlgi isteyen kaynak yok.")).toBeTruthy();
    expect(container.textContent).not.toMatch(/hata veriyor/);
  });

  it("kapalı kaynağı sorun saymaz", async () => {
    serve(json([run("linkedin", "disabled")]));
    renderWidget();

    expect(await screen.findByText("İlgi isteyen kaynak yok.")).toBeTruthy();
  });

  it("kısmi koşuyu ilgi isteyen olarak sayar", async () => {
    serve(json([run("osym", "ok"), run("linkedin", "partial")]));
    renderWidget();

    expect(await screen.findByText(/1 kaynak ilgi istiyor/)).toBeTruthy();
  });

  it("tüm koşular sağlıklıysa sağlıklı der", async () => {
    serve(json([run("osym", "ok")]));
    renderWidget();

    expect(await screen.findByText("Kaynaklar sağlıklı.")).toBeTruthy();
  });
});
