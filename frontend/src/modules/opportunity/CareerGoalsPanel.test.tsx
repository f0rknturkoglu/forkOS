// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { CareerGoalsPanel } from "./CareerGoalsPanel";
const harness = vi.hoisted(() => ({ get: vi.fn(), navigate: vi.fn() }));
vi.mock("@/core/api", () => ({ api: { get: harness.get } }));
vi.mock("@/app/router", () => ({ navigate: harness.navigate }));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
function show() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <CareerGoalsPanel />
    </QueryClientProvider>,
  );
}
it("reads canonical goals and navigates to their owning workspace", async () => {
  harness.get.mockResolvedValue([
    { id: "canonical", status: "active" },
    { id: "archived", status: "completed" },
  ]);
  show();
  expect(await screen.findByText(/1 aktif hedef/)).toBeTruthy();
  expect(harness.get).toHaveBeenCalledWith("/goals");
  fireEvent.click(screen.getByRole("button", { name: "Hedefleri aç" }));
  expect(harness.navigate).toHaveBeenCalledWith("/goals");
});
it("missing goals evidence is an error rather than a fictional count", async () => {
  harness.get.mockRejectedValue(new Error("unavailable"));
  show();
  expect(await screen.findByText(/Hedef özeti yüklenemedi/)).toBeTruthy();
  expect(screen.queryByText(/0 aktif hedef/)).toBeNull();
});
