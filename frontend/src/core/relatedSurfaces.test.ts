/**
 * Faz 18 guardrail: her linklenebilir entity tipi detay/focus yuzeyinde
 * RelatedPanel ile gorunur iliskilere sahip olmali.
 *
 * Tip -> yuzey eslemesi backend EntityTypeSpec'teki rotalara dayanir
 * (kural 13); burada tip->rota sabiti YOKTUR, yalnizca hangi sayfa
 * dosyasinin paneli barindirdigi listelenir.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const SURFACES: Record<string, string> = {
  todo: "src/modules/todo/TodoPage.tsx",
  project: "src/modules/projects/ProjectsPage.tsx",
  opportunity: "src/modules/opportunity/OpportunityDetail.tsx",
  study_topic: "src/modules/learning/LearningPage.tsx",
  media_item: "src/modules/media/MediaDetailPage.tsx",
  bookmark: "src/modules/bookmarks/BookmarksPage.tsx",
  document: "src/modules/documents/DocumentsPage.tsx",
  expense: "src/modules/finance/FinancePage.tsx",
  recurring_payment: "src/modules/finance/FinancePage.tsx",
};

describe("entity relation visibility (Faz 18)", () => {
  it.each(Object.entries(SURFACES))("type %s has a RelatedPanel entry point in %s", (type, path) => {
    const source = readFileSync(resolve(path), "utf8");
    expect(source).toContain("RelatedPanel");
    // Iliskiler yalnizca panel uzerinden; dogrudan POST /links yok.
    expect(source).not.toContain('post("/links"');
  });
});
