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
async function sendMessage() {
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  fireEvent.change(screen.getByLabelText("Hermes mesajı"), { target: { value: "Hedefimi hazırla" } });
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Hermes’e gönder" }).hasAttribute("disabled")).toBe(false),
  );
  fireEvent.click(screen.getByRole("button", { name: "Hermes’e gönder" }));
}
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
  show();
  expect(await screen.findByText("Hermes yapılandırılmamış")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Hermes mesajı"), { target: { value: "Hedefimi hazırla" } });
  expect(screen.getByRole("button", { name: "Hermes’e gönder" }).hasAttribute("disabled")).toBe(true);
  expect(api.post).not.toHaveBeenCalled();
});

it("edited preview cannot approve and a rejection binds the new revision", async () => {
  vi.mocked(api.get).mockResolvedValue({ state: "ready" });
  vi.mocked(api.post).mockResolvedValue(draft);
  show();
  await sendMessage();
  const title = await screen.findByLabelText("Taslak başlık 1");
  const approve = screen.getByRole("button", { name: "Taslağı onayla ve uygula" });
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
  fireEvent.click(screen.getByRole("button", { name: "Değişiklikleri kaydet" }));
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
  vi.mocked(api.get).mockResolvedValue({ state: "ready" });
  const pending = { client_uuid: "turn-identity", message: "hazırla" };
  vi.mocked(api.post).mockResolvedValue({ ...draft, revision: null, state: "unknown_delivery", pending_turn: pending });
  show();
  await sendMessage();
  fireEvent.click(await screen.findByRole("button", { name: "Aynı turu uzlaştır" }));
  await waitFor(() => expect(api.post).toHaveBeenLastCalledWith("/goals/studio/sessions/session/turns", pending));
});
it("raw JSON editing blocks approval until the changed draft is validated", async () => {
  vi.mocked(api.get).mockResolvedValue({ state: "ready" });
  vi.mocked(api.post).mockResolvedValue(draft);
  show();
  await sendMessage();
  await screen.findByLabelText("Taslak başlık 1");
  fireEvent.click(screen.getByText("Gelişmiş taslak düzenleme (JSON)"));
  const text = screen.getByLabelText("Taslak JSON");
  fireEvent.change(text, { target: { value: "{broken" } });
  expect(screen.getByRole("button", { name: "Taslağı onayla ve uygula" }).hasAttribute("disabled")).toBe(true);
});

it("cloud consent is explicit, bound to server policy, revocable and shows actual model origin", async () => {
  const permission = { revision: "c".repeat(64), policy_id: "d".repeat(64), allowed: false };
  const cloud = {
    state: "consent_required",
    provider_label: "Nous Portal",
    configured_model: "configured-model",
    local: false,
    consent: permission,
  };
  vi.mocked(api.get).mockResolvedValue(cloud);
  vi.mocked(api.put).mockResolvedValue({ ...permission, allowed: true });
  show("Hedefimi konuşalım");
  const grant = await screen.findByRole("button", { name: "İzni kaydet" });
  expect(grant.hasAttribute("disabled")).toBe(true);
  expect(api.post).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("checkbox"));
  vi.mocked(api.get).mockResolvedValue({ ...cloud, state: "ready", consent: { ...permission, allowed: true } });
  vi.mocked(api.post).mockResolvedValue({ ...draft, runtime: { provider: "nous", model: "actual-model" } });
  fireEvent.click(grant);
  await waitFor(() => expect(api.put).toHaveBeenCalledWith("/goals/studio/consent", { ...permission, allowed: true }));
  fireEvent.click(screen.getByRole("button", { name: "Bağlantı ayrıntıları" }));
  expect(await screen.findByText("Son yanıt: nous · actual-model")).toBeTruthy();
  fireEvent.click(await screen.findByRole("button", { name: "Bulut iznini geri al" }));
  await waitFor(() =>
    expect(api.put).toHaveBeenLastCalledWith("/goals/studio/consent", { ...permission, allowed: false }),
  );
});
it("edits a contextual draft's content and date before explicit approval", async () => {
  vi.mocked(api.get).mockResolvedValue({ state: "ready" });
  vi.mocked(api.post).mockResolvedValue({ ...draft, context: { kind: "project", entity_id: "selected-project" } });
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <GoalStudio
        goalId={null}
        goals={[]}
        onClose={vi.fn()}
        assistanceContext={{ kind: "project", entity_id: "selected-project" }}
      />
    </QueryClientProvider>,
  );
  await sendMessage();
  await screen.findByLabelText("Taslak açıklama 1");
  fireEvent.change(screen.getByLabelText("Taslak açıklama 1"), { target: { value: "Günde dört saat çalışma." } });
  fireEvent.change(screen.getByLabelText("Taslak tarih 1"), { target: { value: "2026-11-26" } });
  expect(screen.getByRole("button", { name: "Taslağı onayla ve uygula" }).hasAttribute("disabled")).toBe(true);
  vi.mocked(api.put).mockResolvedValue({ ...draft, context: { kind: "project", entity_id: "selected-project" } });
  fireEvent.click(screen.getByRole("button", { name: "Değişiklikleri kaydet" }));
  await waitFor(() =>
    expect(api.put).toHaveBeenCalledWith(
      "/goals/studio/sessions/session/proposal",
      expect.objectContaining({
        operations: [
          expect.objectContaining({
            data: expect.objectContaining({
              description: "Günde dört saat çalışma.",
              target_at: "2026-11-25T21:00:00.000Z",
            }),
          }),
        ],
      }),
    ),
  );
  expect(vi.mocked(api.post).mock.calls.every(([path]) => !path.includes("decision"))).toBe(true);
});
