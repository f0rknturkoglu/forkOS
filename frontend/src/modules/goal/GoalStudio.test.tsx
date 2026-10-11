// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, it, expect, vi } from "vitest";
import { api } from "@/core/api";
import { GoalStudio } from "./GoalStudio";
vi.mock("@/core/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
  streamGoalStudio: vi.fn().mockResolvedValue(undefined),
}));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
const draft = {
  id: "session",
  state: "approval_pending",
  messages: [{ role: "assistant", text: "Mevcut YDS puanı bilinmiyor" }],
  error: null,
  revision: {
    id: "revision",
    fingerprint: "a".repeat(64),
    state: "ready_for_review",
    before: {},
    results: {},
    proposal: {
      schema_version: 1,
      rationale: "2027 hazırlığı",
      assumptions: [],
      missing_information: ["YDS güncel ölçümü"],
      warnings: [],
      evidence_refs: [],
      operations: [{ key: "goal", type: "goal.create", data: { title: "Yüksek lisans", weight: "1", priority: 2 } }],
    },
  },
};
function show(initialMessage?: string) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <GoalStudio goalId={null} goals={[]} onClose={vi.fn()} initialMessage={initialMessage} />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  localStorage.clear();
  vi.mocked(api.get).mockResolvedValue({ state: "not_configured", message: "Hermes yapılandırılmamış" });
});
it("an explicit initial message creates a session and sends one turn without extra clicks", async () => {
  vi.mocked(api.get).mockResolvedValue({ state: "ready" });
  vi.mocked(api.post).mockResolvedValue({ ...draft, revision: null, state: "drafting" });
  show("Nerede kalmıştım?");
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2));
  expect(api.post).toHaveBeenNthCalledWith(
    1,
    "/goals/studio/sessions",
    expect.objectContaining({ client_uuid: expect.any(String), goal_id: null }),
  );
  expect(api.post).toHaveBeenNthCalledWith(
    2,
    "/goals/studio/sessions/session/turns",
    expect.objectContaining({ client_uuid: expect.any(String), message: "Nerede kalmıştım?" }),
  );
});
it("a lost first turn response retries its original identity", async () => {
  vi.mocked(api.get).mockResolvedValue({ state: "ready" });
  vi.mocked(api.post)
    .mockResolvedValueOnce({ ...draft, revision: null, state: "drafting" })
    .mockRejectedValueOnce(new Error("Yanıt kayboldu"));
  show("Devam edelim");
  fireEvent.click(await screen.findByRole("button", { name: "Gönderimi yeniden dene" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(3));
  expect(vi.mocked(api.post).mock.calls[2]).toEqual(vi.mocked(api.post).mock.calls[1]);
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
it("unavailable Hermes keeps discussion editable and cannot authorize writes", async () => {
  vi.mocked(api.post).mockResolvedValue({ ...draft, revision: null, state: "drafting" });
  show();
  expect(await screen.findByText("Hermes yapılandırılmamış")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Görüşme aç" }));
  await screen.findByText("Görüşme");
  expect(screen.getByRole("button", { name: "Hermes’e gönder" }).hasAttribute("disabled")).toBe(true);
  expect(screen.queryByRole("button", { name: "Bu revizyonu onayla ve uygula" })).toBeNull();
});
it("edited preview cannot approve and a rejection binds the new revision", async () => {
  vi.mocked(api.post).mockResolvedValue(draft);
  show();
  fireEvent.click(screen.getByRole("button", { name: "Görüşme aç" }));
  const title = await screen.findByLabelText("Taslak başlık 1");
  const approve = screen.getByRole("button", { name: "Bu revizyonu onayla ve uygula" });
  expect(approve.hasAttribute("disabled")).toBe(false);
  fireEvent.change(title, { target: { value: "Yeni başlık" } });
  expect(approve.hasAttribute("disabled")).toBe(true);
  const revised = {
    ...draft,
    revision: {
      ...draft.revision,
      id: "revision-2",
      fingerprint: "b".repeat(64),
      proposal: {
        ...draft.revision.proposal,
        operations: [
          {
            ...draft.revision.proposal.operations[0],
            data: { ...draft.revision.proposal.operations[0].data, title: "Yeni başlık" },
          },
        ],
      },
    },
  };
  vi.mocked(api.put).mockResolvedValue(revised);
  fireEvent.click(screen.getByRole("button", { name: "Değişiklikleri doğrula · yeni revizyon" }));
  await waitFor(() => expect(approve.hasAttribute("disabled")).toBe(false));
  vi.mocked(api.post).mockResolvedValue({
    ...revised,
    state: "rejected",
    revision: { ...revised.revision, state: "rejected" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Reddet" }));
  await screen.findByText("Reddedildi");
  expect(api.post).toHaveBeenLastCalledWith("/goals/studio/sessions/session/decision", {
    revision_id: "revision-2",
    fingerprint: "b".repeat(64),
    decision: "reject",
  });
});
it("unknown delivery restored from server retries the same turn", async () => {
  const pending = { client_uuid: "turn-identity", message: "hazırla" };
  vi.mocked(api.post).mockResolvedValue({ ...draft, revision: null, state: "unknown_delivery", pending_turn: pending });
  show();
  fireEvent.click(screen.getByRole("button", { name: "Görüşme aç" }));
  fireEvent.click(await screen.findByRole("button", { name: "Aynı turu uzlaştır" }));
  await waitFor(() => expect(api.post).toHaveBeenLastCalledWith("/goals/studio/sessions/session/turns", pending));
});
it("raw JSON editing blocks approval until the changed draft is validated", async () => {
  vi.mocked(api.post).mockResolvedValue(draft);
  show();
  fireEvent.click(screen.getByRole("button", { name: "Görüşme aç" }));
  await screen.findByLabelText("Taslak başlık 1");
  fireEvent.click(screen.getByText("Gelişmiş taslak düzenleme (JSON)"));
  const text = screen.getByLabelText("Taslak JSON");
  fireEvent.change(text, { target: { value: "{broken" } });
  expect(screen.getByRole("button", { name: "Bu revizyonu onayla ve uygula" }).hasAttribute("disabled")).toBe(true);
});
