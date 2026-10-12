// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "@/core/api";
import { queryClient } from "@/core/queryClient";
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
    <QueryClientProvider client={queryClient()}>
      <GoalsPage />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  queryClient().setDefaultOptions({ queries: { retry: false } });
  location.hash = "#/goals";
  vi.mocked(api.get).mockResolvedValue(empty);
});
afterEach(() => {
  cleanup();
  queryClient().clear();
  vi.resetAllMocks();
});
it("offers a plan-free objective and keeps an empty denominator unknown", async () => {
  show();
  await screen.findByText("İlk hedefini tanımla");
  expect(screen.getByText("Ölçüm yok")).toBeTruthy();
  expect(screen.getByRole("tab", { name: "Stratejik plan" })).toBeTruthy();
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
it("keeps missing measurement evidence readable without exposing internal finding codes", async () => {
  vi.mocked(api.get).mockResolvedValue({
    ...empty,
    findings: [
      {
        code: "MISSING_MEASUREMENT",
        observed_facts: "Etkin hedef için ölçülebilir stratejik sonuç yok.",
        window_start: "2026-09-12",
        window_end: "2026-10-12",
        entity_refs: [],
        evidence_refs: [],
      },
    ],
  });
  show();
  expect(await screen.findByText("Etkin hedef için ölçülebilir stratejik sonuç yok.")).toBeTruthy();
  expect(screen.queryByText(/MISSING_MEASUREMENT/)).toBeNull();
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
it("tutorial target toggles the new goal editor and preserves an unfinished title", async () => {
  location.hash = "#/goals?view=objectives";
  show();
  const toggle = await screen.findByRole("button", { name: "Kendim oluştur" });
  const title = screen.getByLabelText("Hedef başlığı") as HTMLInputElement;
  expect(title.closest("[hidden]")).not.toBeNull();
  fireEvent.click(toggle);
  expect(toggle.getAttribute("aria-expanded")).toBe("true");
  expect(title.closest("[hidden]")).toBeNull();
  fireEvent.change(title, { target: { value: "Taslak hedef" } });
  fireEvent.click(toggle);
  expect(toggle.getAttribute("aria-expanded")).toBe("false");
  expect(title.closest("[hidden]")).not.toBeNull();
  fireEvent.click(toggle);
  expect(title.value).toBe("Taslak hedef");
  expect(toggle.closest('[data-onboarding="goal-create"]')).not.toBeNull();
});

it("hydrates the new goal editor when its first detail response arrives later", async () => {
  location.hash = "#/goals?view=objectives";
  let resolveDetail!: (value: unknown) => void;
  const pending = new Promise((resolve) => {
    resolveDetail = resolve;
  });
  vi.mocked(api.get).mockImplementation((path) => (path === "/goals/late-goal" ? pending : Promise.resolve(empty)));
  vi.mocked(api.post).mockResolvedValue({ id: "late-goal" });
  show();
  fireEvent.click(await screen.findByRole("button", { name: "Kendim oluştur" }));
  fireEvent.change(screen.getByLabelText("Hedef başlığı"), { target: { value: "Kalıcı hedef" } });
  fireEvent.change(screen.getByLabelText("Hedef açıklaması"), { target: { value: "Korunacak açıklama" } });
  fireEvent.click(screen.getByRole("button", { name: "Hedef oluştur" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/goals/late-goal"));
  await act(async () =>
    resolveDetail({
      id: "late-goal",
      title: "Kalıcı hedef",
      description: "Korunacak açıklama",
      status: "active",
      horizon: "quarter",
      priority: 2,
      weight: "1",
      milestones: [],
    }),
  );
  await waitFor(() => expect((screen.getByLabelText("Hedef başlığı") as HTMLInputElement).value).toBe("Kalıcı hedef"));
  expect((screen.getByLabelText("Hedef açıklaması") as HTMLTextAreaElement).value).toBe("Korunacak açıklama");
});

it("waits for the created plan before mounting its editor", async () => {
  location.hash = "#/goals?view=plans";
  const plan = {
    id: "late-plan",
    title: "Kalıcı plan",
    summary: "Kalıcı özet",
    start_at: "2026-10-01T00:00:00Z",
    end_at: "2026-12-31T00:00:00Z",
    status: "active",
    revision: 1,
  };
  let created = false;
  let resolveOverview!: (value: unknown) => void;
  const pending = new Promise((resolve) => {
    resolveOverview = resolve;
  });
  vi.mocked(api.get).mockImplementation(() => (created ? pending : Promise.resolve(empty)));
  vi.mocked(api.post).mockImplementation(async () => {
    created = true;
    return plan;
  });
  show();
  fireEvent.click(await screen.findByRole("button", { name: "Planı kendim oluştur" }));
  fireEvent.change(await screen.findByLabelText("Plan başlığı"), { target: { value: plan.title } });
  fireEvent.change(screen.getByLabelText("Plan özeti"), { target: { value: plan.summary } });
  fireEvent.change(screen.getByLabelText("Plan başlangıcı"), { target: { value: "2026-10-01" } });
  fireEvent.change(screen.getByLabelText("Plan bitişi"), { target: { value: "2026-12-31" } });
  fireEvent.click(screen.getByRole("button", { name: "Planı kaydet" }));
  expect(await screen.findByText("Plan yükleniyor…")).toBeTruthy();
  expect(screen.queryByLabelText("Plan başlığı")).toBeNull();
  await act(async () => resolveOverview({ ...empty, plans: [plan] }));
  await waitFor(() => expect((screen.getByLabelText("Plan başlığı") as HTMLInputElement).value).toBe(plan.title));
  expect((screen.getByLabelText("Plan özeti") as HTMLTextAreaElement).value).toBe(plan.summary);
  expect((screen.getByLabelText("Plan başlangıcı") as HTMLInputElement).value).toBe("2026-10-01");
});
