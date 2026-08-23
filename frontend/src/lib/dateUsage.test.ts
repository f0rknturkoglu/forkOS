import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const calendarDayFiles = [
  "src/modules/activity/DayPage.tsx",
  "src/modules/finance/FinancePage.tsx",
  "src/modules/review/ReviewPage.tsx",
  "src/modules/todo/WeeklyPlannerPage.tsx",
];

describe("calendar-day call sites", () => {
  it.each(calendarDayFiles)("uses the shared Istanbul date helper in %s", (path) => {
    const source = readFileSync(resolve(path), "utf8");

    expect(source).not.toContain("toISOString().slice(0, 10)");
    expect(source).not.toContain("toISOString().slice(0,10)");
    expect(source).toContain("localDateKey");
  });
});
