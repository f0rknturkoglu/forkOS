// @vitest-environment jsdom
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createTask,
  invalidateTaskWrite,
  planDayForToday,
  readPlanTodayPreference,
  writePlanTodayPreference,
} from "./tasks";

// jsdom 30 + Node 26'da window.localStorage getter'i undefined donuyor;
// test icin bellek ici bir localStorage tanimliyoruz (TodoComposer.test ile ayni).
vi.hoisted(() => {
  const store = new Map<string, string>();
  const storage: Storage = {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key) => store.get(key) ?? null,
    key: (index) => [...store.keys()][index] ?? null,
    removeItem: (key) => {
      store.delete(key);
    },
    setItem: (key, value) => {
      store.set(key, String(value));
    },
  };
  Object.defineProperty(globalThis, "localStorage", {
    value: storage,
    configurable: true,
    writable: true,
  });
});

const harness = vi.hoisted(() => ({ apiPost: vi.fn() }));
vi.mock("@/core/api", () => ({ api: { post: harness.apiPost } }));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: vi.fn(),
}));
vi.mock("@/core/queryClient", () => ({ queryClient: vi.fn() }));

/**
 * Faz 17 guardrail: gorev olusturma TEK intent katmanindan gecer.
 * Bilesenler daginik POST /todos body'si uretemez.
 */
// Faz 31: butun gorev giris dosyalari. Farkli endpoint adi kullanarak
// guardrail'den kacmak mumkun degil -- her giris ya createTask'tan gecer
// ya da planDayForToday ile ortak tercihi uygular.
const taskEntryFiles = [
  "src/modules/todo/TodoComposer.tsx",
  "src/modules/todo/TodoRow.tsx",
  "src/modules/projects/ProjectTodos.tsx",
  "src/modules/learning/LearningPage.tsx",
  "src/modules/opportunity/JobDetail.tsx",
  "src/modules/opportunity/AnnouncementDetail.tsx",
  "src/core/DropCapture.tsx",
  "src/modules/todo/index.ts",
];

describe("task creation intent (Faz 17)", () => {
  it.each(taskEntryFiles)("does not scatter direct POST /todos in %s", (path) => {
    const source = readFileSync(resolve(path), "utf8");
    expect(source).not.toContain('post("/todos"');
    expect(source).not.toContain('api.post("/todos"');
    // Tek intent kaynagi: her giris ortak katmandan beslenir (Faz 31) --
    // ya createTask/planDayForToday ya da yakalama kutusuna delege (DropCapture).
    expect(source).toMatch(/core\/(tasks|CaptureDialog)"|\.\/CaptureDialog"/);
  });

  beforeEach(() => {
    harness.apiPost.mockReset();
    localStorage.clear();
  });

  it("tercih acikken plan_day gider, due_at uretilmez", async () => {
    writePlanTodayPreference(true);
    await createTask({ title: "Test" });
    const [path, body] = harness.apiPost.mock.calls[0];
    expect(path).toBe("/todos");
    expect(body.plan_day).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(body).not.toHaveProperty("due_at");
  });

  it("tercih kapaliyken plan_day gövdede YOK", async () => {
    writePlanTodayPreference(false);
    await createTask({ title: "Test" });
    const [, body] = harness.apiPost.mock.calls[0];
    expect(body).not.toHaveProperty("plan_day");
  });

  it("acik plan_day tercihten once gelir; due_at yalnizca intent'ten", async () => {
    writePlanTodayPreference(false);
    await createTask({ title: "Test", plan_day: "2026-09-01", due_at: "2026-09-02T10:00:00Z" });
    const [, body] = harness.apiPost.mock.calls[0];
    expect(body.plan_day).toBe("2026-09-01");
    expect(body.due_at).toBe("2026-09-02T10:00:00Z");
  });

  it("invalidateTaskWrite hem todo hem plan key'lerini tazeler", async () => {
    const { invalidateAfter } = vi.mocked(await import("@/core/invalidation"));
    invalidateTaskWrite();
    expect(invalidateAfter).toHaveBeenCalledWith("todo.write", "plan.write");
  });

  it("planDayForToday tercihe gore plan_day uretir, asla due_at degil", async () => {
    writePlanTodayPreference(true);
    expect(planDayForToday()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    writePlanTodayPreference(false);
    expect(planDayForToday()).toBeUndefined();
  });

  it("preference localStorage'ta yasar", () => {
    writePlanTodayPreference(true);
    expect(readPlanTodayPreference()).toBe(true);
    writePlanTodayPreference(false);
    expect(readPlanTodayPreference()).toBe(false);
  });
});
