/**
 * Faz 18/32 guardrail: linklenebilir her entity tipi gercek, navigable ve
 * iliski gosteren bir yuzeye sahip olmali.
 *
 * Kaynak backend EntityTypeSpec'tir (kural 13): linkable=False tipler
 * bilincli olarak kapatilmistir (liste-rotali, alt-varlik, kaynak ya da
 * gecici icerik). Guardrail manuel SURFACES listesini backend registry ile
 * karsilastirir -- yeni linkable tip eklenirse yuzey olmadan test kirmali,
 * linkable=False yapilmadan listeden cikarmak da kirmali.
 */
import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(import.meta.dirname, "../../..");

interface BackendSpec {
  route: string;
  linkable: boolean;
}

/** Backend EntityTypeSpec kayitlarini {type: {route, linkable}} olarak okur. */
function backendEntitySpecs(): Record<string, BackendSpec> {
  const specs: Record<string, BackendSpec> = {};
  const moduleDirs = readdirSync(resolve(ROOT, "backend/app/modules"), {
    withFileTypes: true,
  })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name);
  for (const dir of moduleDirs) {
    const path = resolve(ROOT, `backend/app/modules/${dir}/__init__.py`);
    let src: string;
    try {
      src = readFileSync(path, "utf8");
    } catch {
      continue;
    }
    const blocks = src.split("EntityTypeSpec(").slice(1);
    for (const block of blocks) {
      const quotes = block.match(/["'][^"']+["']/g) ?? [];
      if (quotes.length < 4) continue;
      const type = quotes[0]!.slice(1, -1);
      const route = quotes[3]!.slice(1, -1);
      const head = block.slice(0, block.indexOf(")"));
      specs[type] = { route, linkable: !head.includes("linkable=False") };
    }
  }
  return specs;
}

/** Linklenebilir tip -> yuzey dosyasi (RelatedPanel tasir). */
const SURFACES: Record<string, string> = {
  todo: "src/modules/todo/TodoPage.tsx",
  project: "src/modules/projects/ProjectsPage.tsx",
  opportunity: "src/modules/opportunity/OpportunityDetail.tsx",
  // Ogrenme yuzeyi artik konu detayi ("Baglantilar" sekmesi); sayfa yalniz kabuk.
  study_topic: "src/modules/learning/TopicDetail.tsx",
  learning_resource: "src/modules/learning/TopicDetail.tsx",
  media_item: "src/modules/media/MediaDetailPage.tsx",
  bookmark: "src/modules/bookmarks/BookmarksPage.tsx",
  document: "src/modules/documents/DocumentsPage.tsx",
  note: "src/modules/notes/NotesPage.tsx",
  expense: "src/modules/finance/FinancePage.tsx",
  income: "src/modules/finance/FinancePage.tsx",
  recurring_payment: "src/modules/finance/FinancePage.tsx",
  flashcard_deck: "src/modules/flashcard/DeckDetail.tsx",
};

describe("entity relation visibility (Faz 18/32)", () => {
  const specs = backendEntitySpecs();

  it("backend registry linklenebilir tipleri yuzeyle esler", () => {
    const linkable = Object.entries(specs)
      .filter(([, spec]) => spec.linkable)
      .map(([type]) => type)
      .sort();
    expect(linkable).toEqual(Object.keys(SURFACES).sort());
  });

  it.each(Object.entries(SURFACES))("linklenebilir %s yuzeyinde RelatedPanel var (%s)", (type, path) => {
    expect(specs[type]?.linkable).toBe(true);
    const source = readFileSync(resolve(ROOT, "frontend", path), "utf8");
    expect(source).toContain("RelatedPanel");
    expect(source).not.toContain('post("/links"');
  });

  it("linkable=False tipler yuzey listesinde YOK (gerekceli kapatilmis)", () => {
    const disabled = Object.entries(specs)
      .filter(([, spec]) => !spec.linkable)
      .map(([type]) => type);
    for (const type of disabled) {
      expect(SURFACES[type]).toBeUndefined();
    }
    // Bilincli karar listesi -- yeni tip eklenirse bu test eslesmeli.
    expect(disabled.sort()).toEqual(
      [
        "course",
        "career_connection",
        "career_story",
        "external_event",
        "feed",
        "feed_item",
        "media_collection",
        "media_consumption",
        "media_cycle",
        "media_unit",
        "flashcard_card",
        "milestone",
        "note_folder",
        "pomodoro_session",
        "review",
        "study_area",
      ].sort(),
    );
  });
});
