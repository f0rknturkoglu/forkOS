// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "@/core/api";
import { ToastProvider } from "@/core/ui";
import { ContextualHelp, ContextMemory, ScheduleTasks } from "./ContextualHelp";
import type { SemanticCandidate } from "./agentSemantic";
import { BookmarkLearningAttach } from "@/modules/bookmarks/BookmarkLearningAttach";
vi.mock("@/core/api", () => ({ api: { get: vi.fn(), post: vi.fn() }, qs: () => "?area_id=a1" }));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/modules/goal/GoalStudio", () => ({ GoalStudio: () => <p>Hermes görüşmesi</p> }));
vi.mock("@/modules/today/PendingDecisions", () => ({
  PlanReviewModal: ({ planRowId }: { planRowId: number }) => <p>Ortak onay ekranı {planRowId}</p>,
}));
function show(ui: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}
    >
      <ToastProvider>{ui}</ToastProvider>
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  localStorage.clear();
  vi.resetAllMocks();
});
afterEach(cleanup);
it("local summary is directly visible; Hermes starts only after submitting a message", async () => {
  vi.mocked(api.post).mockResolvedValue({
    title: "Proje özeti",
    generated_at: "2026-10-11T12:00:00Z",
    facts: [{ text: "Sonuç bilinmiyor", status: "missing", support_refs: [] }],
    links: [],
    sources: [],
    warnings: [],
    memory_candidates: [],
  });
  show(<ContextualHelp context={{ kind: "project", entity_id: "p1" }} label="Nerede kalmıştım?" />);
  expect(api.get).not.toHaveBeenCalled();

  expect(await screen.findByText("Bilinmiyor: Sonuç bilinmiyor")).toBeTruthy();
  expect(api.post).toHaveBeenCalledExactlyOnceWith("/goals/studio/context", { kind: "project", entity_id: "p1" });
  expect(screen.queryByText("Hermes görüşmesi")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Kapat" }));
  expect(screen.getByRole("button", { name: "Nerede kalmıştım?" })).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Hermes'e sor"), { target: { value: "Sıradaki iş ne?" } });
  fireEvent.click(screen.getByRole("button", { name: "Gönder" }));
  expect(await screen.findByText("Hermes görüşmesi")).toBeTruthy();
});
it("summary failure stays dismissible with deliberate retry", async () => {
  vi.mocked(api.post).mockRejectedValue(new Error("unavailable"));
  show(
    <ContextualHelp
      context={{ kind: "review", period_kind: "weekly", period_start: "2026-10-05" }}
      label="Haftayı birlikte değerlendirelim"
    />,
  );
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Yeniden dene" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Kapat" }));
  expect(screen.queryByRole("alert")).toBeNull();
});
it("plan preparation is explicit; lost response retry reuses UUID and does not approve", async () => {
  vi.mocked(api.post).mockRejectedValueOnce(new Error("lost response")).mockResolvedValueOnce({ plan_row_id: 12 });
  show(<ScheduleTasks tasks={[{ id: "t1", title: "Mevcut görev" }]} />);
  expect(api.post).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Planla" }));
  expect(api.post).not.toHaveBeenCalled();
  fireEvent.blur(screen.getByLabelText("Plan günü"), { target: { value: "2026-10-20" } });
  fireEvent.click(screen.getByRole("button", { name: "Değişiklikleri incele" }));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Değişiklikleri incele" }));
  expect(await screen.findByText("Ortak onay ekranı 12")).toBeTruthy();
  expect(vi.mocked(api.post).mock.calls[0][1]).toEqual(vi.mocked(api.post).mock.calls[1][1]);
  expect(vi.mocked(api.post).mock.calls[0][1]).toMatchObject({ day: "2026-10-20" });
  expect(vi.mocked(api.post).mock.calls.every(([path]) => path === "/execution/planning")).toBe(true);
});
const candidate = {
  id: "m1",
  recurrence_count: 1,
  remote_allowed: false,
  candidate_key: "candidate",
  kind: "preference",
  primary_evidence_class: "explicit_user",
  observed_at: "2026-10-11T12:00:00Z",
  first_seen_at: "2026-10-11T12:00:00Z",
  last_seen_at: "2026-10-11T12:00:00Z",
  created_at: "2026-10-11T12:00:00Z",
  updated_at: "2026-10-11T12:00:00Z",
  statement: "Sabah kısa plan tercih ederim",
  scope: "global",
  sensitivity: "normal",
  revision: "original",
  suggested_destination: "hot_memory",
  status: "needs_review",
  evidence_refs: [{ ref: "event:1", source_revision: "verified" }],
} satisfies SemanticCandidate;
it("inspection is not consent; promotion uses the server confirmation revision", async () => {
  vi.mocked(api.post)
    .mockResolvedValueOnce({ ...candidate, status: "ready", revision: "confirmed" })
    .mockResolvedValueOnce({ status: "promoted" });
  show(<ContextMemory candidates={[candidate]} />);
  fireEvent.click(screen.getByRole("button", { name: "İncele" }));
  expect(api.post).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Hatırla" }));
  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith("/agent/semantic/candidates/m1/promote", {
      expected_revision: "confirmed",
      target_destination: "hot_memory",
      supersedes: undefined,
    }),
  );
  await waitFor(() => expect(screen.queryByRole("button", { name: "İncele" })).toBeNull());
});
it("memory dismissal is durable with no mutation", () => {
  const first = show(<ContextMemory candidates={[candidate]} />);
  fireEvent.click(screen.getByRole("button", { name: "Şimdi değil" }));
  first.unmount();
  show(<ContextMemory candidates={[candidate]} />);
  expect(screen.queryByRole("button", { name: "İncele" })).toBeNull();
  expect(api.post).not.toHaveBeenCalled();
});
it("topic search attaches the original bookmark with no collection mutation", async () => {
  vi.mocked(api.get).mockImplementation(async (path) =>
    path === "/study/areas"
      ? [{ id: "a1", title: "Yazılım" }]
      : [
          { id: "t1", title: "Python", children: [] },
          { id: "t2", title: "SQL", children: [] },
        ],
  );
  vi.mocked(api.post).mockResolvedValue({ id: "r1", topic_id: "t1", bookmark_id: "b1" });
  show(<BookmarkLearningAttach bookmarkId="b1" />);
  expect(api.get).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Öğrenme konusuna ekle" }));
  await screen.findByRole("option", { name: "Yazılım" });
  fireEvent.change(screen.getByLabelText("Çalışma alanı"), { target: { value: "a1" } });
  await screen.findByRole("option", { name: "Python" });
  fireEvent.change(screen.getByLabelText("Öğrenme konusu ara"), { target: { value: "Python" } });
  expect(screen.queryByRole("option", { name: "SQL" })).toBeNull();
  fireEvent.change(screen.getByLabelText("Mevcut öğrenme konusu"), { target: { value: "t1" } });
  fireEvent.click(screen.getByRole("button", { name: "Konuyu bağla" }));
  await screen.findByText("Kaynak bağlandı.");
  expect(api.post).toHaveBeenCalledExactlyOnceWith("/study/resources/attach-bookmark", {
    topic_id: "t1",
    bookmark_id: "b1",
  });
});
