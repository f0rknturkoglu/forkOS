import { beforeAll, describe, expect, it, vi } from "vitest";
import type { ModuleSpec } from "@/core/types";
import { TodayAgendaWidget } from "./TodayAgendaWidget";

const harness = vi.hoisted(() => ({
  specs: [] as ModuleSpec[],
}));

vi.mock("@/core/registry", () => ({
  registerModule: (spec: ModuleSpec) => harness.specs.push(spec),
}));

describe("Today module registrations", () => {
  beforeAll(async () => {
    await import("@/modules/index");
  });

  it("replaces the three duplicate plan widgets with the unified agenda", () => {
    const main = harness.specs
      .flatMap((spec) => spec.todayWidgets ?? [])
      .filter((widget) => typeof widget !== "function" && widget.region === "main");
    const components = main.map((widget) => (typeof widget === "function" ? widget : widget.component));

    expect(components.filter((component) => component === TodayAgendaWidget)).toHaveLength(1);
    expect(components.map((component) => component.name)).not.toEqual(
      expect.arrayContaining(["TodayScheduleWidget", "TodoWidget", "PlannerWidget"]),
    );
  });

  it("does not expose Habit as a separate frontend module", () => {
    expect(harness.specs.map((spec) => spec.id)).not.toContain("habit");
  });
});
