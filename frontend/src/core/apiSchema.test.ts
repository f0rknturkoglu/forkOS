import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("generated API contracts", () => {
  it("contains the high-risk orchestration schemas", () => {
    const generated = readFileSync(
      fileURLToPath(new URL("../generated/api-schema.ts", import.meta.url)),
      "utf8",
    );

    expect(generated).toContain("TodayAgenda");
    expect(generated).toContain("ReviewPreview");
    expect(generated).toContain("SourceSyncStatusOut");
    expect(generated).toContain("SourceRunOut");
  });
});
