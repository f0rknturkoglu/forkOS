import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Gun karari ureten dosyalar ortak date helper'ini kullanmak zorunda (Faz 14).
 * Uygulama gunu TEK kaynak: `@/lib/date` (Europe/Istanbul). Tarayicinin
 * yerel saati veya `toISOString().slice(0, 10)` (UTC gunu) yasak.
 */
const dayDecisionFiles = [
  "src/modules/activity/ActivityPage.tsx",
  "src/modules/calendar/CalendarPage.tsx",
  "src/modules/review/ReviewWidget.tsx",
  "src/modules/todo/OverdueTodosWidget.tsx",
  "src/modules/todo/TodoComposer.tsx",
  "src/modules/todo/TodoPage.tsx",
  "src/modules/todo/WeeklyPlannerPage.tsx",
  "src/modules/todo/priority.ts",
  "src/modules/today/TodayAgendaWidget.tsx",
];

describe("day decision call sites", () => {
  it.each(dayDecisionFiles)("uses the shared Istanbul date helper in %s", (path) => {
    const source = readFileSync(resolve(path), "utf8");

    expect(source).toContain('from "@/lib/date"');
    expect(source).not.toContain("toISOString().slice(0, 10)");
    expect(source).not.toContain("toISOString().slice(0,10)");
  });
});
