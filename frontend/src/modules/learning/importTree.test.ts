import { describe, expect, it } from "vitest";
import { normalizeImportTree } from "./importTree";

describe("normalizeImportTree", () => {
  it("preserves enriched metadata and practice instructions in API resources", () => {
    const tree = normalizeImportTree({
      area: "Python",
      topics: [
        {
          title: "venv",
          practice: "Create an environment",
          completion_criteria: ["Run a script"],
          resources: [
            {
              title: "Tutorial",
              url: "https://example.com",
              type: "documentation",
              language: "en",
              description: "Read this",
              verification: "http_ok",
              checked_on: "2026-10-03",
            },
          ],
        },
      ],
    });
    expect(tree.topics).toEqual([
      {
        title: "venv",
        resources: [
          {
            title: "Tutorial",
            url: "https://example.com",
            kind: "doc",
            note: "Read this\nKaynak türü: documentation\nDil: en\nDoğrulama: http_ok\nKontrol tarihi: 2026-10-03",
          },
          {
            title: "Uygulama ve tamamlama ölçütleri",
            kind: "exercise",
            note: "Uygulama\nCreate an environment\n\nTamamlama ölçütleri\n- Run a script",
          },
        ],
      },
    ]);
  });
  it("preserves canonical seeds and nested order", () => {
    const tree = {
      area: "A",
      topics: [
        {
          title: "B",
          status: "done",
          target_min: 10,
          position: 2,
          resources: [{ title: "C", kind: "book", note: "notes" }],
          children: [{ title: "D", resources: [] }],
        },
      ],
    };
    expect(normalizeImportTree(tree)).toEqual(tree);
  });
  it("rejects unsupported fields instead of silently discarding data", () => {
    expect(() => normalizeImportTree({ area: "A", topics: [{ title: "B", unsupported: true }] })).toThrow(
      "desteklenmeyen alanlar",
    );
    expect(() => normalizeImportTree({ area: "A", topics: [{ title: "B", completion_criteria: "wrong" }] })).toThrow(
      "Tamamlama ölçütleri",
    );
  });
});
