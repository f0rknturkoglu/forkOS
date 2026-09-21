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
import { invalidateAfter } from "@/core/invalidation";
import { queryClient } from "@/core/queryClient";

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
  "src/modules/today/TodayAgendaWidget.tsx",
  "src/modules/projects/ProjectTodos.tsx",
  "src/modules/learning/LearningPage.tsx",
  "src/modules/opportunity/JobDetail.tsx",
  "src/modules/opportunity/AnnouncementDetail.tsx",
  "src/modules/opportunity/OpportunityDetailSections.tsx",
  "src/modules/bookmarks/BookmarkReaderModal.tsx",
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

  /**
   * Faz 33 sozlesmesi: gorev yazmasi Todo + Home ajandasi + Haftalik plan +
   * Proje yuzeylerinin HEPSINI tazeler. Eksik anahtar kullaniciya "manuel
   * yenileme" olarak donuyordu (proje gorevlerinde tam olarak boyleydi).
   * Gercek cache uzerinde olculur; mock'lanmis cagri listesi degil.
   */
  it("gorev yazmasi Todo/Home/Plan/Proje sorgularini tazeler", () => {
    const cache = queryClient().getQueryCache();
    const keys = [
      ["todos", "open", "all", "", false],
      ["today-agenda", "2026-01-01"],
      ["plan", "2026-01-01"],
      ["project-todos", "p1"],
      ["projects", "active"],
    ];
    const queries = keys.map((queryKey) => cache.build(queryClient(), { queryKey, queryFn: async () => null }));
    for (const query of queries) {
      expect(query.state.isInvalidated, `${String(query.queryKey[0])} yazma oncesi taze`).toBe(false);
    }

    invalidateTaskWrite();

    for (const query of queries) {
      expect(query.state.isInvalidated, `${String(query.queryKey[0])} yazma sonrasi tazelenmeli`).toBe(true);
    }
  });

  /**
   * Degerlendirme kararlari gorev yazar (devret -> plan slotu, oncelik -> yeni
   * gorev); Home ajandasi kendi ucuyla okundugu icin ayrica tazelenmeli.
   */
  it("degerlendirme yazmasi Home ajandasini tazeler", () => {
    const query = queryClient()
      .getQueryCache()
      .build(queryClient(), { queryKey: ["today-agenda", "2026-01-01"], queryFn: async () => null });

    invalidateAfter("review.write");

    expect(query.state.isInvalidated).toBe(true);
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
