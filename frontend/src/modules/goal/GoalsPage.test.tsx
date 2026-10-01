// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "@/core/api";
import { GoalsPage } from "./GoalsPage";
vi.mock("@/core/api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));
const empty = {
  warnings: [],
  plans: [],
  pillars: [],
  objectives: [],
  plan_progress: [],
  pillar_progress: [],
  findings: [],
  providers: [],
  alignment: { percent: null, eligible_count: 0, linked_count: 0, unaligned_count: 0, warnings: [], pillars: [] },
};
function show() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <GoalsPage />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  location.hash = "#/goals";
  vi.mocked(api.get).mockResolvedValue(empty);
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
it("offers a plan-free objective and keeps an empty denominator unknown", async () => {
  show();
  await screen.findByText("İlk hedefini tanımla");
  expect(screen.getByText("0/0 anlamlı hareket")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Hedef oluştur" }));
  expect(await screen.findByLabelText("Hedef başlığı")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Hedef oluştur" }).hasAttribute("disabled")).toBe(true);
});
it("shows a recoverable error instead of fake zeros", async () => {
  vi.mocked(api.get).mockRejectedValue(new Error("offline"));
  show();
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Yeniden dene" })).toBeTruthy();
  expect(screen.queryByText("0/0 anlamlı hareket")).toBeNull();
});
it("keeps plan revision history inspectable with comparison explanation", async () => {
  vi.mocked(api.get).mockImplementation(async (path) =>
    path.includes("history")
      ? {
          items: [{ id: "r1", title: "Plan revizyonu 1", occurred_at: "2026-10-01T00:00:00Z", state: { revision: 1 } }],
          comparable: false,
          comparison_reason: "Tanımlar farklı; delta hesaplanmadı.",
        }
      : empty,
  );
  show();
  await screen.findByText("İlk hedefini tanımla");
  fireEvent.click(screen.getByRole("tab", { name: "Geçmiş" }));
  expect(await screen.findByText("Tanımlar farklı; delta hesaplanmadı.")).toBeTruthy();
  expect(screen.getByText(/Plan revizyonu 1/)).toBeTruthy();
});
