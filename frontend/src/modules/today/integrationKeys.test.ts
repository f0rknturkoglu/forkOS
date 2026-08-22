import { describe, expect, it } from "vitest";
import { TODAY_CALENDAR_KEY } from "@/modules/calendar/TodayScheduleWidget";
import { RECURRING_WIDGET_KEY } from "@/modules/finance/RecurringWidget";
import { RSS_SAVE_REFRESH_KEYS } from "@/modules/rss/RssPage";
import { PROJECT_REFRESH_KEYS } from "@/modules/projects/ProjectTodos";

describe("cross-page query integration", () => {
  it("uses detail-page prefixes in Today widgets", () => {
    expect(TODAY_CALENDAR_KEY[0]).toBe("calendar-events");
    expect(RECURRING_WIDGET_KEY[0]).toBe("recurring");
  });

  it("refreshes every linked consumer", () => {
    expect(RSS_SAVE_REFRESH_KEYS).toContain("bookmark-stats");
    expect(PROJECT_REFRESH_KEYS).toContain("project-timeline");
    expect(PROJECT_REFRESH_KEYS).toContain("projects");
  });
});
