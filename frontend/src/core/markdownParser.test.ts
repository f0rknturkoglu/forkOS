import { describe, expect, it } from "vitest";
import { parseInline, parseMarkdown, safeHref, wikilinkTargets } from "./markdownParser";

describe("markdown blokları", () => {
  it("başlık, paragraf, yatay çizgi ayırır", () => {
    const blocks = parseMarkdown("# Başlık\n\nBir paragraf.\n\n---\n");
    expect(blocks.map((b) => b.t)).toEqual(["heading", "paragraph", "hr"]);
    expect(blocks[0]).toMatchObject({ level: 1 });
  });

  it("kod bloğunun içindekileri yorumlamaz", () => {
    const blocks = parseMarkdown("```ts\nconst x = **1**; // #etiket [[bağ]]\n```");
    expect(blocks).toEqual([{ t: "code", lang: "ts", v: "const x = **1**; // #etiket [[bağ]]" }]);
  });

  it("sırasız, sıralı ve görev listelerini ayırır", () => {
    expect(parseMarkdown("- a\n- b")[0]).toMatchObject({ t: "list", ordered: false });
    expect(parseMarkdown("1. a\n2. b")[0]).toMatchObject({ t: "list", ordered: true });
    const tasks = parseMarkdown("- [ ] yapılacak\n- [x] bitti")[0];
    expect(tasks).toMatchObject({ t: "tasks" });
    expect(tasks.t === "tasks" && tasks.items.map((i) => i.checked)).toEqual([false, true]);
  });

  it("alıntı satırlarını tek blokta toplar", () => {
    const blocks = parseMarkdown("> ilk\n> ikinci");
    expect(blocks[0]).toMatchObject({ t: "quote" });
    expect(blocks[0].t === "quote" && blocks[0].content.length).toBe(2);
  });

  it("GFM tablosunu hizalamalarıyla ayrıştırır", () => {
    const table = parseMarkdown("| Konu | Durum |\n| :--- | ---: |\n| API | Bitti |")[0];
    expect(table).toMatchObject({ t: "table", align: ["left", "right"] });
    expect(table.t === "table" && table.rows).toHaveLength(1);
  });
});

describe("satır içi", () => {
  it("kalın, italik, üstü çizili ve kodu tanır", () => {
    expect(parseInline("**kalın** *italik* ~~çizik~~ `kod`").map((t) => t.t)).toEqual([
      "strong",
      "text",
      "em",
      "text",
      "strike",
      "text",
      "code",
    ]);
  });

  it("==metin== işaretini vurgu olarak tanır", () => {
    expect(parseInline("önemli ==cümle==").map((token) => token.t)).toEqual(["text", "mark"]);
  });

  it("[[wikilink]] ve takma adı çözer", () => {
    expect(parseInline("[[Lineer Cebir]]")[0]).toEqual({
      t: "wiki",
      target: "Lineer Cebir",
      label: "Lineer Cebir",
    });
    expect(parseInline("[[Kalkülüs|türev]]")[0]).toEqual({
      t: "wiki",
      target: "Kalkülüs",
      label: "türev",
    });
  });

  it("#etiketi tanır ama başlığı ve URL çırpasını etiket saymaz", () => {
    expect(parseInline("#matematik").map((t) => t.t)).toEqual(["tag"]);
    // "# Başlık" blok seviyesinde başlıktır; satır içinde de bosluk ayirir.
    expect(parseMarkdown("# Başlık")[0].t).toBe("heading");
    const url = parseInline("https://site.com/#bolum");
    expect(url.every((t) => t.t !== "tag")).toBe(true);
  });

  it("çıplak URL'i bağlantıya çevirir", () => {
    expect(parseInline("bak https://a.dev/x")[1]).toEqual({
      t: "link",
      label: "https://a.dev/x",
      href: "https://a.dev/x",
    });
  });

  it("markdown görselini bağlantıdan ayırır", () => {
    expect(parseInline("![ekran görüntüsü](/api/notes/n1/attachments/a1)")[0]).toEqual({
      t: "image",
      alt: "ekran görüntüsü",
      src: "/api/notes/n1/attachments/a1",
    });
  });
});

describe("bağlantı güvenliği", () => {
  it("yalnızca güvenli şemalara izin verir", () => {
    expect(safeHref("https://a.dev")).toBe("https://a.dev");
    expect(safeHref("mailto:a@b.c")).toBe("mailto:a@b.c");
    expect(safeHref("/yerel")).toBe("/yerel");
    // XSS: javascript:/data: baglanti URETILMEZ.
    expect(safeHref("javascript:alert(1)")).toBeNull();
    expect(safeHref("data:text/html,<script>")).toBeNull();
    expect(safeHref("  JavaScript:alert(1)")).toBeNull();
  });

  it("güvensiz şemalı markdown bağlantısı düz metne düşer", () => {
    const tokens = parseInline("[tıkla](javascript:alert(1))");
    expect(tokens.every((t) => t.t !== "link")).toBe(true);
  });
});

describe("wikilink hedefleri", () => {
  it("gövdedeki tüm hedefleri tekilleştirerek toplar", () => {
    const body = "[[A]] ve **[[B|takma]]**\n- [[A]]\n> [[C]]\n```\n[[Kod]]\n```";
    expect(wikilinkTargets(body).sort()).toEqual(["A", "B", "C"]);
  });
});
