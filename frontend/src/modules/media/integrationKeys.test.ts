import { describe, expect, it } from "vitest";
import { MEDIA_REFRESH_KEYS } from "./MediaPage";

describe("media mutation query integration", () => {
  it("refreshes media dashboards and Today continuation data", () => {
    expect(MEDIA_REFRESH_KEYS).toEqual([
      "media",
      "media-detail",
      "media-stats",
      "media-dashboard",
      "today-agenda",
      "activity",
    ]);
  });
});
