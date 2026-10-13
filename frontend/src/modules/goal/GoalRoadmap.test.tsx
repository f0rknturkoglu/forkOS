// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { GoalRoadmap } from "./GoalRoadmap";
import type { components } from "@/generated/api-schema";
const node = (id: string, parent_id: string | null = null) => ({
  id,
  title: id,
  parent_id,
  kind: parent_id ? "record" : "phase",
  position: 0,
  percent: 0,
  completed: false,
  missing: false,
  weight: 1,
  progress_bearing: true,
  completion_gate: false,
  persisted: true,
  dependencies: [],
});
const graph = (nodes: ReturnType<typeof node>[]) =>
  ({
    goal_id: "g",
    nodes,
    percent: 0,
    completed_requirements: 0,
    completed_scope_count: 0,
    scope_count: nodes.length,
    unplanned_count: 0,
    known_requirements: nodes.length,
    total_requirements: nodes.length,
    legacy: false,
    truncated: false,
    warnings: [],
  }) satisfies components["schemas"]["RoadmapOut"];
afterEach(cleanup);
it("keeps detailed work collapsed and exposes an accessible list", () => {
  const select = vi.fn();
  render(
    <GoalRoadmap
      graph={graph([node("Aşama"), node("Çalışma", "Aşama")])}
      title="Hedef"
      selected={null}
      onSelect={select}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Liste" }));
  const list = screen.getByRole("list", { name: "Yol haritası listesi" });
  expect(within(list).queryByRole("button", { name: /Çalışma/ })).toBeNull();
  fireEvent.click(within(list).getByRole("button", { name: "Aşama alt adımları" }));
  fireEvent.click(within(list).getByRole("button", { name: /Çalışma/ }));
  expect(select).toHaveBeenCalledWith(expect.objectContaining({ id: "Çalışma" }));
});
it("supports graph keyboard navigation and zoom controls", () => {
  render(
    <GoalRoadmap graph={graph([node("Bir"), node("İki")])} title="Hedef" selected={null} onSelect={() => undefined} />,
  );
  const view = screen.getByLabelText("Grafiği kaydır; düğümler arasında ok tuşlarıyla gez");
  const first = within(view).getByRole("button", { name: "Bir, %0" });
  first.focus();
  fireEvent.keyDown(first, { key: "ArrowDown" });
  expect(document.activeElement).toBe(within(view).getByRole("button", { name: "İki, %0" }));
  fireEvent.click(screen.getByRole("button", { name: "Yakınlaştır" }));
  expect(screen.getByText("%115")).toBeTruthy();
});
it("handles hundreds of children without opening the entire graph initially", () => {
  render(
    <GoalRoadmap
      graph={graph([node("Dönem"), ...Array.from({ length: 400 }, (_, i) => node(`İş ${i}`, "Dönem"))])}
      title="Uzun vadeli hedef"
      selected={null}
      onSelect={() => undefined}
    />,
  );
  const view = screen.getByLabelText("Grafiği kaydır; düğümler arasında ok tuşlarıyla gez");
  expect(within(view).queryAllByRole("button")).toHaveLength(2);
  fireEvent.click(within(view).getByRole("button", { name: "Dönem alt adımları" }));
  expect(within(view).getByRole("button", { name: "İş 399, %0" })).toBeTruthy();
});
