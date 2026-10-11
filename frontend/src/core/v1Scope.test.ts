import "@/modules";
import { describe, expect, it, vi } from "vitest";
import { allModules, allRoutes, allCommands, allTodayWidgets, hydrateSettings } from "./registry";
import { AFTER } from "./invalidation";
import { areasAt } from "./navigation";

describe("V1 scope", () => {
  it("retires product discovery even with legacy settings", () => {
    hydrateSettings({ "media.links": [{ name: "Retired", url: "https://example.invalid" }] } as never);
    const retired = ["media", "finance", "documents", "knowledge"];
    expect(allModules().map((m) => m.id)).not.toEqual(expect.arrayContaining(retired));
    for (const id of retired) {
      expect(allModules().some((m) => m.id === id)).toBe(false);
      expect(allCommands().some((c) => c.id.startsWith(`${id}.`))).toBe(false);
      expect(allTodayWidgets().some((w) => w.id.startsWith(`${id}.`))).toBe(false);
    }
    expect(allRoutes().some((r) => /^\/(media|finance|documents|notes)(\/|$)/.test(r.path))).toBe(false);
    expect(areasAt("primary").flatMap((a) => a.moduleIds)).not.toEqual(expect.arrayContaining(retired));
  });
  it("does not retain retired mutation invalidations", () => {
    expect(Object.keys(AFTER)).not.toContain("media.write");
    expect(Object.keys(AFTER)).not.toContain("finance.write");
    expect(AFTER["pomodoro.write"]).toEqual(
      expect.arrayContaining(["activity", "review-preview", "study-tree", "study-areas"]),
    );
  });
  it("keeps first-class core modules and diagnostics", () => {
    const ids = allModules().map((m) => m.id);
    for (const id of [
      "today",
      "todo",
      "projects",
      "goal",
      "opportunity",
      "learning",
      "flashcard",
      "calendar",
      "pomodoro",
      "rss",
      "bookmarks",
      "health",
    ])
      expect(ids).toContain(id);
  });
});

vi.hoisted(() => {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => store.set(k, v) },
  });
});
