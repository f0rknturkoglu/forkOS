// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { SettingsPage } from "./SettingsPage";

function json(value: unknown): Response {
  return new Response(JSON.stringify(value), { status: 200, headers: { "Content-Type": "application/json" } });
}

describe("Settings media-links target", () => {
  beforeEach(() => {
    location.hash = "#/settings?section=media-links";
    fireEvent(window, new HashChangeEvent("hashchange"));
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: { getItem: () => null, setItem: vi.fn(), removeItem: vi.fn() },
    });
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = new URL(String(input), "http://localhost").pathname;
        if (path === "/api/settings") return json({ "modules.disabled": [], "media.links": [] });
        if (path === "/api/sources/health") return json([]);
        if (path === "/api/backup/status")
          return json({ last_backup: null, drive_folder_id: null, last_drive_upload: null, last_drive_error: null });
        return json({ connected: false });
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("scrolls to and focuses the requested media links panel", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <SettingsPage />
        </ToastProvider>
      </QueryClientProvider>,
    );

    await screen.findByText("Medya sağlayıcı anahtarları");
    const target = container.querySelector<HTMLElement>("#media-links");
    await waitFor(() => expect(document.activeElement).toBe(target));
    expect(target?.scrollIntoView).toHaveBeenCalledWith({ block: "center" });
  });
});
