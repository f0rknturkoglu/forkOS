// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "@/core/api";
import { Heatmap } from "./Heatmap";
vi.mock("@/core/api", async (original) => ({
  ...(await original<typeof import("@/core/api")>()),
  api: { get: vi.fn() },
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
it("previews dates without requests for empty days, lazily loads human events, and supports Escape", async () => {
  const heatmap = {
    days: [
      { day: "2026-10-11", total: 0, kinds: {} },
      { day: "2026-10-12", total: 1, kinds: { reading: 1 } },
    ],
    labels: { reading: "okuma" },
    totals: { reading: 1 },
    total: 1,
    active_days: 1,
    streak: 1,
  };
  vi.mocked(api.get).mockImplementation(async (path) =>
    path.includes("heatmap")
      ? heatmap
      : {
          events: [
            {
              id: 1,
              kind: "reading",
              verb: "rss.item_read",
              payload: { title: "Okuduğum makale" },
              occurred_at: "2026-10-12T09:00:00Z",
            },
            { id: 2, kind: null, verb: "rss.items_added", payload: {}, occurred_at: "2026-10-12T09:01:00Z" },
          ],
        },
  );
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <Heatmap />
    </QueryClientProvider>,
  );
  const empty = await screen.findByRole("link", { name: "11 Ekim 2026 — kayıt yok" });
  fireEvent.mouseEnter(empty);
  expect(within(screen.getByRole("tooltip")).getByText("11 Ekim 2026")).toBeTruthy();
  expect(api.get).toHaveBeenCalledTimes(1);
  fireEvent.mouseEnter(screen.getByRole("link", { name: "12 Ekim 2026 — 1 okuma" }));
  const preview = screen.getByRole("tooltip");
  expect(await within(preview).findByText(/Okuduğum makale/)).toBeTruthy();
  expect(within(preview).queryByText(/Yeni RSS yazıları/)).toBeNull();
  expect(within(preview).getByRole("link", { name: "Günü aç →" }).getAttribute("href")).toBe("#/day?d=2026-10-12");
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/activity/day?day=2026-10-12"));
  const cell = screen.getByRole("link", { name: "12 Ekim 2026 — 1 okuma" });
  act(() => cell.focus());
  fireEvent.scroll(window);
  expect(screen.getByRole("tooltip")).toBeTruthy();
  fireEvent.keyDown(window, { key: "Escape" });
  expect(screen.queryByRole("tooltip")).toBeNull();
});
