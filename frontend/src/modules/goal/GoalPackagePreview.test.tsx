// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { GoalPackagePreview } from "./GoalPackagePreview";
import type { components } from "@/generated/api-schema";
type Proposal = components["schemas"]["StudioProposal-Output"];
const data = {
  title: "Başlangıç",
  kind: "phase" as const,
  position: 0,
  weight: "1",
  progress_bearing: true,
  completion_gate: false,
};
const proposal: Proposal = {
  schema_version: 2,
  rationale: "Plan",
  operations: [
    { key: "goal", type: "goal.create", data: { title: "Hedef" } },
    { key: "phase", type: "roadmap.create", goal_ref: "goal", data },
    { key: "task", type: "todo.create", data: { title: "Çalış", priority: 2 } },
    {
      key: "work",
      type: "roadmap.create",
      goal_ref: "goal",
      parent_ref: "phase",
      target_ref: "task",
      data: { ...data, title: "Çalış", kind: "record" },
    },
    { key: "slot", type: "plan.schedule", task_ref: "task", data: { day: "2026-10-13", duration_min: 30 } },
  ],
} as Proposal;
afterEach(cleanup);
it("requires deliberate calendar override and resets it when the date changes", () => {
  const change = vi.fn();
  render(<GoalPackagePreview proposal={proposal} before={{}} onChange={change} disabled={false} />);
  fireEvent.click(screen.getByRole("checkbox", { name: "Çalış: takvim engeline rağmen bu gün çalışmayı seçiyorum" }));
  expect(
    (change.mock.calls.at(-1)![0] as Proposal).operations.find((op) => op.type === "plan.schedule")?.data,
  ).toMatchObject({ calendar_override: true });
  fireEvent.input(screen.getByLabelText("Çalış plan günü"), { target: { value: "2026-10-20" } });
  expect(
    (change.mock.calls.at(-1)![0] as Proposal).operations.find((op) => op.type === "plan.schedule")?.data,
  ).toMatchObject({ calendar_override: false, day: "2026-10-20" });
});
it("uses the canonical Todo priority scale in the approval preview", () => {
  const change = vi.fn();
  render(<GoalPackagePreview proposal={proposal} before={{}} onChange={change} disabled={false} />);
  const priority = screen.getByRole("combobox", { name: "Çalış öncelik" });
  expect(within(priority).getByRole("option", { name: "yüksek" }).getAttribute("value")).toBe("3");
  fireEvent.change(priority, { target: { value: "3" } });
  expect((change.mock.calls[0][0] as Proposal).operations.find((op) => op.type === "todo.create")?.data).toMatchObject({
    priority: 3,
  });
});
it("preserves rapid edits to different fields before the parent acknowledges them", () => {
  const change = vi.fn();
  render(<GoalPackagePreview proposal={proposal} before={{}} onChange={change} disabled={false} />);
  fireEvent.input(screen.getByLabelText("Çalış plan günü"), { target: { value: "2026-10-20" } });
  fireEvent.change(screen.getByLabelText("Oluşturulacak görevler: Çalış"), { target: { value: "Güncel iş" } });
  const next = change.mock.calls.at(-1)![0] as Proposal;
  expect(next.operations.find((o) => o.type === "plan.schedule")?.data).toMatchObject({ day: "2026-10-20" });
  expect(next.operations.find((o) => o.type === "todo.create")?.data).toMatchObject({ title: "Güncel iş" });
});
it("commits a planning date when leaving the native date field", () => {
  const change = vi.fn();
  render(<GoalPackagePreview proposal={proposal} before={{}} onChange={change} disabled={false} />);
  fireEvent.blur(screen.getByLabelText("Çalış plan günü"), { target: { value: "2026-10-14" } });
  expect(
    (change.mock.calls.at(-1)![0] as Proposal).operations.find((op) => op.type === "plan.schedule")?.data,
  ).toMatchObject({ day: "2026-10-14" });
});
it("removing a task also removes its graph node and plan slot", () => {
  const change = vi.fn();
  render(<GoalPackagePreview proposal={proposal} before={{}} onChange={change} disabled={false} />);
  const task = screen.getByLabelText("Oluşturulacak görevler: Çalış").closest("div.rounded-card")!;
  fireEvent.click(within(task as HTMLElement).getByRole("button", { name: "Paketten çıkar" }));
  const next = change.mock.calls[0][0] as Proposal;
  expect(next.operations.map((o) => o.key)).toEqual(["goal", "phase"]);
});
it("removing a phase removes the canonical work that only that phase owns", () => {
  const change = vi.fn();
  render(<GoalPackagePreview proposal={proposal} before={{}} onChange={change} disabled={false} />);
  const phase = screen.getByLabelText("Yol haritası: Başlangıç").closest("div.rounded-card")!;
  fireEvent.click(within(phase as HTMLElement).getByRole("button", { name: "Paketten çıkar" }));
  expect((change.mock.calls[0][0] as Proposal).operations.map((o) => o.key)).toEqual(["goal"]);
});
it("adding a task creates both a canonical action and a graph reference", () => {
  const change = vi.fn();
  render(<GoalPackagePreview proposal={proposal} before={{}} onChange={change} disabled={false} />);
  fireEvent.change(screen.getByLabelText("Yeni adım başlığı"), { target: { value: "Ek deneme" } });
  fireEvent.change(screen.getByLabelText("Bağlanacak aşama"), { target: { value: "phase" } });
  fireEvent.click(screen.getByRole("button", { name: "Pakete ekle" }));
  const ops = (change.mock.calls[0][0] as Proposal).operations;
  expect(ops.at(-2)).toMatchObject({ type: "todo.create", data: { title: "Ek deneme" } });
  expect(ops.at(-1)).toMatchObject({ type: "roadmap.create", target_ref: ops.at(-2)?.key, parent_ref: "phase" });
});
