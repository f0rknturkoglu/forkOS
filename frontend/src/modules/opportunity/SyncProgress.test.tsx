// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SyncProgress } from "./SyncProgress";

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
});
