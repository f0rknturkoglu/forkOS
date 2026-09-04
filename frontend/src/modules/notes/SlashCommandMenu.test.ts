import { describe, expect, it } from "vitest";
import { highlightMarkdown } from "./BookmarkHighlights";
import { slashContext } from "./SlashCommandMenu";

describe("not slash komutları", () => {
  it("yalnız satır başındaki slash sorgusunu yakalar", () => {
    expect(slashContext("# Başlık\n/tabl", 14)).toEqual({ start: 9, query: "tabl" });
    expect(slashContext("metin /tabl", 11)).toBeNull();
  });

  it("yer imi seçimini kaynaklı markdown vurgusuna çevirir", () => {
    const markdown = highlightMarkdown({
      id: "b1",
      title: "Kaynak",
      url: "https://example.com",
      description: null,
      collection: "reference",
      source: "extension",
      read_status: "read",
      favorite: false,
      note: null,
      selection: "İlk satır\nİkinci satır",
      saved_at: "2026-09-04T00:00:00Z",
      tags: [],
    });
    expect(markdown).toContain("> ==İlk satır\n> İkinci satır==");
    expect(markdown).toContain("[Kaynak](https://example.com)");
  });
});
