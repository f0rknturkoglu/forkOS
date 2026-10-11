// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { api } from "@/core/api";
import { WeeklyPlannerPage } from "./WeeklyPlannerPage";
vi.mock("@/core/api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() }, qs: () => "" }));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/ContextualHelp", () => ({ ScheduleTasks: () => null }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
it("places immediately during a slow save and restores the backlog after a failed save", async () => {
  vi.mocked(api.get).mockImplementation(async (path) =>
    path.startsWith("/todos?")
      ? [{ id: "test-todo", title: "Bekleyen görev", status: "open", tags: [], priority: 2 }]
      : [],
  );
  let rejectSave!: (error: Error) => void;
  vi.mocked(api.post).mockImplementation(
    () =>
      new Promise((_resolve, reject) => {
        rejectSave = reject;
      }),
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <WeeklyPlannerPage />
      </ToastProvider>
    </QueryClientProvider>,
  );
  fireEvent.click(await screen.findByRole("button", { name: "Bekleyen görev görevini planlamak için seç" }));
  const place = screen.getAllByRole("button", { name: /Seçili görevi .* gününe planla/ })[0];
  fireEvent.click(place);
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
  expect(screen.queryByRole("button", { name: "Bekleyen görev görevini planlamak için seç" })).toBeNull();
  expect(screen.getByRole("button", { name: "Bekleyen görev" })).toBeTruthy();
  expect(place.hasAttribute("disabled")).toBe(true);
  rejectSave(new Error("Kayıt reddedildi"));
  await screen.findByRole("button", { name: "Bekleyen görev seçimini kaldır" });
  expect(screen.getByText("Kayıt reddedildi")).toBeTruthy();
  const plans = client.getQueriesData({ queryKey: ["plan"] });
  expect(plans.every(([, value]) => Array.isArray(value) && value.length === 0)).toBe(true);
  client.clear();
});
