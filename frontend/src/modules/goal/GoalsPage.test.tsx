// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "@/core/api";
import { queryClient } from "@/core/queryClient";
import { GoalsPage } from "./GoalsPage";
vi.mock("@/core/api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn() } }));
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
const goal = {
  id: "g1",
  title: "YDS 60+",
  description: "Günde dört saat çalış.",
  status: "active",
  horizon: "quarter",
  priority: 2,
  weight: "1",
  target_at: null,
  milestones: [{ id: "m1", title: "İlk denemeyi çöz", completed_at: null }],
};
const objective = {
  goal,
  key_results: [],
  reasons: [],
  confidence: "low",
  trajectory: "unknown",
  evidence_refs: [],
  work: {
    progress_percent: 0,
    completed_count: 0,
    total_count: 1,
    milestones: [
      {
        id: "m1",
        title: "İlk denemeyi çöz",
        manual_completed: false,
        completed: false,
        progress_percent: 0,
        action_ids: [],
      },
    ],
    actions: [],
  },
};
const graph = {
  goal_id: "g1",
  nodes: [
    {
      id: "m1",
      title: "İlk denemeyi çöz",
      kind: "milestone",
      target_id: "m1",
      target_type: "goal_milestone",
      percent: 0,
      position: 0,
      persisted: false,
      dependencies: [],
    },
  ],
  percent: 0,
  legacy: true,
  warnings: [],
};
const workspace = {
  todos: [],
  learning: [],
  resources: [],
  planned_slots: [],
  projects: [],
  activity_windows: { "7": { count: 0, completed_todos: 0 }, "30": { count: 0 }, "90": { count: 0 } },
  outcome: { percent: null },
  accepted_revisions: [],
};
function response(path: string, overview: unknown = empty) {
  if (path.endsWith("/roadmap")) return graph;
  if (path.endsWith("/workspace")) return workspace;
  if (path.endsWith("/conversation")) throw new Error("Henüz görüşme yok");
  return overview;
}
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
  vi.mocked(api.get).mockImplementation(async (path) => response(path));
  localStorage.clear();
});
afterEach(() => {
  cleanup();
  queryClient().clear();
  vi.resetAllMocks();
});

it("starts with goal cards and offers creation without visible technical metrics", async () => {
  show();
  await screen.findByText("İlk hedefini oluştur");
  expect(screen.queryByText("Kanıt kalitesi")).toBeNull();
  expect(screen.queryByRole("tab", { name: "Stratejik plan" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Hedef oluştur" }));
  fireEvent.click(
    within(screen.getByRole("dialog", { name: "Yeni hedef" })).getByRole("button", { name: "Kendim oluştur" }),
  );
  expect(screen.getByLabelText("Hedef başlığı")).toBeTruthy();
});
it("shows a recoverable read error instead of an empty list", async () => {
  vi.mocked(api.get).mockRejectedValue(new Error("offline"));
  show();
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Yeniden dene" })).toBeTruthy();
  expect(screen.queryByText("İlk hedefini oluştur")).toBeNull();
});
it("opens a plain work view and keeps editing and evidence behind explicit buttons", async () => {
  vi.mocked(api.get).mockImplementation(async (path) => response(path, { ...empty, objectives: [objective] }));
  show();
  fireEvent.click(await screen.findByRole("button", { name: /YDS 60/ }));
  expect(await screen.findByRole("heading", { name: "Yol haritası" })).toBeTruthy();
  fireEvent.click(screen.getByText("Adımlar ve manuel ekleme"));
  expect(screen.getByRole("heading", { name: "Sıradaki adımlar" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "İlk denemeyi çöz: Göreve ekle" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "İlk denemeyi çöz: Öğrenmeye ekle" })).toBeTruthy();
  expect(screen.queryByLabelText("Hedef başlığı")).toBeNull();
  expect(screen.queryByText("Kanıt kalitesi")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Düzenle" }));
  expect((screen.getByLabelText("Hedef başlığı") as HTMLInputElement).value).toBe(goal.title);
  fireEvent.click(
    within(screen.getByRole("dialog", { name: "Hedefi düzenle" })).getByRole("button", { name: "Kapat" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Ölçümler ve ayrıntılar" }));
  expect(screen.getByText("Kanıt kalitesi")).toBeTruthy();
});
it("hydrates a newly created goal without automatically reopening its editor", async () => {
  let resolveDetail!: (value: unknown) => void;
  const pending = new Promise((resolve) => {
    resolveDetail = resolve;
  });
  vi.mocked(api.get).mockImplementation((path) => (path === "/goals/g1" ? pending : Promise.resolve(response(path))));
  vi.mocked(api.post).mockResolvedValue({ id: "g1" });
  show();
  fireEvent.click(await screen.findByRole("button", { name: "Hedef oluştur" }));
  fireEvent.click(
    within(screen.getByRole("dialog", { name: "Yeni hedef" })).getByRole("button", { name: "Kendim oluştur" }),
  );
  fireEvent.change(screen.getByLabelText("Hedef başlığı"), { target: { value: goal.title } });
  fireEvent.click(
    within(screen.getByRole("dialog", { name: "Yeni hedef" })).getByRole("button", { name: "Hedef oluştur" }),
  );
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/goals/g1"));
  await act(async () => resolveDetail(goal));
  expect(await screen.findByRole("heading", { name: goal.title })).toBeTruthy();
  expect(screen.queryByLabelText("Hedef başlığı")).toBeNull();
});
it("keeps technical findings out of the main view and exposes them on request", async () => {
  vi.mocked(api.get).mockResolvedValue({
    ...empty,
    findings: [{ observed_facts: "Etkin hedef için ölçülebilir sonuç yok.", evidence_refs: [], entity_refs: [] }],
  });
  show();
  await screen.findByText("İlk hedefini oluştur");
  expect(screen.queryByText("Etkin hedef için ölçülebilir sonuç yok.")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Geçmiş ve gelişmiş ayarlar" }));
  fireEvent.click(screen.getByRole("tab", { name: "Strateji ayrıntıları" }));
  expect(screen.getByText("Etkin hedef için ölçülebilir sonuç yok.")).toBeTruthy();
});
it("keeps plan revision history accessible", async () => {
  vi.mocked(api.get).mockImplementation(async (path) =>
    path.includes("history")
      ? {
          items: [{ id: "r1", title: "Plan revizyonu 1", state: { revision: 1 } }],
          comparison_reason: "Tanımlar farklı; delta hesaplanmadı.",
        }
      : empty,
  );
  show();
  fireEvent.click(await screen.findByRole("button", { name: "Geçmiş ve gelişmiş ayarlar" }));
  fireEvent.click(screen.getByRole("tab", { name: "Geçmiş" }));
  expect(await screen.findByText("Tanımlar farklı; delta hesaplanmadı.")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Plan revizyonu 1" })).toBeTruthy();
});
it("uses the bound goal in the persistent living conversation", async () => {
  vi.mocked(api.get).mockImplementation(async (path) =>
    path.includes("studio/status")
      ? { state: "ready", local: true }
      : response(path, { ...empty, objectives: [objective] }),
  );
  vi.mocked(api.post).mockResolvedValue({ id: "s1", state: "drafting", context: null, messages: [], revision: null });
  show();
  fireEvent.click(await screen.findByRole("button", { name: /YDS 60/ }));
  fireEvent.click(screen.getByRole("button", { name: "Hermes’e ilerlememi sor" }));
  fireEvent.change(screen.getByLabelText("Hermes mesajı"), { target: { value: "Nasıl gidiyorum?" } });
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Hermes’e gönder" }).hasAttribute("disabled")).toBe(false),
  );
  fireEvent.click(screen.getByRole("button", { name: "Hermes’e gönder" }));
  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith(
      "/goals/studio/sessions",
      expect.objectContaining({ goal_id: "g1", mode: "living" }),
    ),
  );
});
