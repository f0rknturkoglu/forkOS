// @vitest-environment jsdom
/**
 * `/sources` derin bağlantıları ve kabuk çerçevesi.
 *
 *  - `?filter=problems` (ve `?problem=1`) yalnızca sorunlu kaynakları bırakır,
 *  - `?source=<id>` hedef satırı vurgular, görünüme kaydırır ve süzgeçler onu
 *    gizlese bile görünür tutar,
 *  - sayfa yüzeyi "system" çerçevesiyle (paylaşılan bileşen) kurar.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SourcesPage } from "./SourcesPage";

const catalog = [
  { id: "forkjob_core:eures", interval_minutes: 1440, kind: "job", class: "normal", estimated_seconds: 120 },
  { id: "forkjob_core:linkedin", interval_minutes: 720, kind: "job", class: "slow_optin", estimated_seconds: 180 },
];

const coverageBase = {
  kind: "job",
  category: null,
  official: null,
  url: null,
  parser_version: null,
  last_run_at: "2026-09-21T08:00:00Z",
  last_success_at: "2026-09-21T08:00:00Z",
  last_new_content_at: "2026-09-21T08:00:00Z",
  avg_publish_interval_days: null,
  consecutive_empty: 0,
  circuit_open: false,
  consecutive_failures: 0,
  tracked: true,
  retry_at: null,
};

const coverage = [
  {
    ...coverageBase,
    source: "forkjob_core:eures",
    class: "normal",
    last_status: "ok",
    last_error: null,
    last_error_kind: null,
  },
  {
    ...coverageBase,
    source: "forkjob_core:linkedin",
    class: "slow_optin",
    last_status: "error",
    last_error: "429 Too Many Requests",
    last_error_kind: "http_429",
  },
];

const harness = vi.hoisted(() => ({
  params: new URLSearchParams(""),
  scrollIntoView: vi.fn(),
  get: vi.fn(),
}));

vi.mock("@/app/router", () => ({
  navigate: vi.fn(),
  useHashRoute: () => ({ path: "/sources", params: harness.params }),
}));
vi.mock("@/core/api", () => ({
  api: { get: harness.get, post: vi.fn(), patch: vi.fn(), del: vi.fn() },
}));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true, useInvalidate: () => vi.fn() }));

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SourcesPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  harness.params = new URLSearchParams("");
  harness.scrollIntoView.mockReset();
  harness.get.mockReset();
  harness.get.mockImplementation(async (path: string) => {
    if (path === "/sources/catalog") return catalog;
    if (path === "/sources/coverage") return coverage;
    if (path === "/sources/sync") return { active: null, last_completed: null, running: [], sources: [] };
    if (path === "/sources/cache") {
      return { dir: "/c", mode: "on", files: 0, bytes: 0, oldest: null, hosts: {}, max_bytes: 1, max_age_seconds: 1 };
    }
    return [];
  });
  Element.prototype.scrollIntoView = harness.scrollIntoView;
});

afterEach(() => cleanup());

describe("sistem çerçevesi", () => {
  it("paylaşılan yüzeyi sistem kabuğunda açar", async () => {
    renderPage();
    expect(await screen.findByText("Kaynak operasyonları")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Kaynak Durumu" })).toBeTruthy();
  });
});

describe("derin bağlantılar", () => {
  it("?filter=problems yalnızca sorunlu kaynağı bırakır", async () => {
    harness.params = new URLSearchParams("filter=problems");
    renderPage();

    await waitFor(() => expect(document.getElementById("source-row-forkjob_core:linkedin")).toBeTruthy());
    expect(document.getElementById("source-row-forkjob_core:eures")).toBeNull();
    expect(screen.getByRole("button", { name: /Yalnızca sorunlular/ }).getAttribute("aria-pressed")).toBe("true");
  });

  it("?problem=1 aynı süzgeci açar (kısa biçim)", async () => {
    harness.params = new URLSearchParams("problem=1");
    renderPage();

    await waitFor(() => expect(document.getElementById("source-row-forkjob_core:linkedin")).toBeTruthy());
    expect(document.getElementById("source-row-forkjob_core:eures")).toBeNull();
  });

  it("?source= satırı vurgular ve görünüme kaydırır", async () => {
    harness.params = new URLSearchParams("source=forkjob_core:eures");
    renderPage();

    const row = await screen.findByText("forkjob_core:eures");
    const node = document.getElementById("source-row-forkjob_core:eures");
    expect(node).toBeTruthy();
    expect(node?.contains(row)).toBe(true);
    expect(node?.className).toContain("bg-accent-surface/40");
    await waitFor(() => expect(harness.scrollIntoView).toHaveBeenCalled());
  });

  it("odaklanan satır süzgeç onu gizlese bile görünür kalır", async () => {
    harness.params = new URLSearchParams("filter=problems&source=forkjob_core:eures");
    renderPage();

    expect(await screen.findByText("forkjob_core:eures")).toBeTruthy();
    await waitFor(() => expect(document.getElementById("source-row-forkjob_core:eures")).toBeTruthy());
    expect(document.getElementById("source-row-forkjob_core:linkedin")).toBeTruthy();
  });
});
