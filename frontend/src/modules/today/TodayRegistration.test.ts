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

  it("günün işi alanında tek plan yüzeyi tutar: birleşik ajanda", () => {
    const plan = harness.specs
      .flatMap((spec) => spec.todayWidgets ?? [])
      .filter((widget) => typeof widget !== "function" && widget.core === "plan");
    const components = plan.map((widget) => (typeof widget === "function" ? widget : widget.component));

    expect(components.filter((component) => component === TodayAgendaWidget)).toHaveLength(1);
    expect(components.map((component) => component.name)).not.toEqual(
      expect.arrayContaining(["TodayScheduleWidget", "TodoWidget", "PlannerWidget"]),
    );
  });

  it("does not expose Habit as a separate frontend module", () => {
    expect(harness.specs.map((spec) => spec.id)).not.toContain("habit");
  });

  it("çekirdek bağlam yüzeyleri sütunlarını kendi kayıtlarında bildirir", () => {
    const widgets = harness.specs.flatMap((spec) => spec.todayWidgets ?? []);
    for (const [id, lane] of [
      ["today.career", "main"],
      ["learning.widget", "main"],
      ["today.feed-stream", "secondary"],
      ["activity.heatmap", "secondary"],
    ]) {
      expect(widgets.find((widget) => widget.id === id)?.contextLane).toBe(lane);
    }
  });
});
