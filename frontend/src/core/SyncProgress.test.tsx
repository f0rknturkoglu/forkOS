// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SyncProgress } from "@/core/SyncProgress";

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

describe("SyncProgress", () => {
  let responses: Response[];

  beforeEach(() => {
    responses = [
      json({ detail: "medya eşitlemesi kapalı" }, 500),
      json({ active: null, last_completed: null, running: [], sources: [] }),
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(responses.shift() ?? json({}))),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows a retryable error and returns to the compact idle state after a successful retry", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <QueryClientProvider client={client}>
        <SyncProgress scope="media" compact />
      </QueryClientProvider>,
    );

    expect((await screen.findByRole("alert")).textContent).toContain("medya eşitlemesi kapalı");
    fireEvent.click(screen.getByRole("button", { name: "Yeniden dene" }));
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
    expect(container.textContent).toBe("");
  });

  it("shows the live new-record badge and every source state", async () => {
    responses = [
      json({
        active: {
          id: "batch-1",
          scope: "opportunity",
          status: "running",
          source_ids: ["osym", "jobhunter:eures", "jobhunter:linkedin"],
          total_sources: 3,
          completed_sources: 1,
          ok_sources: 0,
          partial_sources: 1,
          empty_sources: 0,
          error_sources: 0,
          items_found: 7,
          progress_pct: 33,
          created_at: "2026-09-20T10:00:00Z",
          started_at: "2026-09-20T10:00:01Z",
          finished_at: null,
        },
        last_completed: null,
        running: [
          {
            source: "jobhunter:eures",
            status: "running",
            started_at: "2026-09-20T10:00:02Z",
            finished_at: null,
            items_found: 0,
            error: null,
          },
        ],
        sources: [
          {
            source: "osym",
            status: "partial",
            started_at: "2026-09-20T10:00:01Z",
            finished_at: "2026-09-20T10:00:03Z",
            items_found: 7,
            error: "bazı sayfalar alınamadı",
          },
          {
            source: "jobhunter:eures",
            status: "running",
            started_at: "2026-09-20T10:00:02Z",
            finished_at: null,
            items_found: 0,
            error: null,
          },
          {
            source: "jobhunter:linkedin",
            status: "queued",
            started_at: null,
            finished_at: null,
            items_found: 0,
            error: null,
          },
        ],
      }),
    ];
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <SyncProgress compact />
      </QueryClientProvider>,
    );

    expect(await screen.findByLabelText("7 yeni kayıt")).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Tüm kaynakları göster" }));

    expect(screen.getByText("kısmi")).not.toBeNull();
    expect(screen.getByText("çekiliyor")).not.toBeNull();
    expect(screen.getByText("kuyrukta")).not.toBeNull();
  });
});
