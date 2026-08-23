import { describe, expect, it } from "vitest";
import { localDateKey } from "./date";

describe("localDateKey", () => {
  it("uses the Istanbul calendar day instead of the UTC day", () => {
    expect(localDateKey(new Date("2026-01-14T21:30:00Z"))).toBe("2026-01-15");
  });

  it("formats single digit months and days with leading zeroes", () => {
    expect(localDateKey(new Date("2026-02-03T09:00:00Z"))).toBe("2026-02-03");
  });
});
