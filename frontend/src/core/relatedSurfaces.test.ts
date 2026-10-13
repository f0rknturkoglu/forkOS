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

/** Linklenebilir tip -> yuzey dosyasi/dosyalari (RelatedPanel tasir).
 *  Firsat detayi is ilani ve duyuru calisma yuzeylerine ayrildi; ikisi de
 *  RelatedPanel tasir, bu yuzden birlikte listelenir.
 *
 *  Faz 3: bilgi Vault'a tasindigi icin `note`/`note_folder` backend'de
 *  linkable=False oldu; yuzeyleri yok (asagidaki kapali liste). */
const SURFACES: Record<string, string | string[]> = {
  todo: "src/modules/todo/TodoPage.tsx",
  goal: "src/modules/goal/GoalsPage.tsx",
  goal_milestone: "src/modules/goal/GoalsPage.tsx",
  goal_roadmap_node: "src/modules/goal/GoalLivingWorkspace.tsx",
  strategic_plan: "src/modules/goal/GoalsPage.tsx",
  strategic_pillar: "src/modules/goal/GoalsPage.tsx",
  key_result: "src/modules/goal/GoalsPage.tsx",

  project: "src/modules/projects/ProjectResources.tsx",
  opportunity: ["src/modules/opportunity/JobDetail.tsx", "src/modules/opportunity/AnnouncementDetail.tsx"],
  // Ogrenme yuzeyi artik konu detayi ("Baglantilar" sekmesi); sayfa yalniz kabuk.
  study_topic: "src/modules/learning/TopicDetail.tsx",
  learning_resource: "src/modules/learning/TopicDetail.tsx",
  bookmark: "src/modules/bookmarks/BookmarksPage.tsx",
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

  it.each(Object.entries(SURFACES))("linklenebilir %s yuzeyinde RelatedPanel var (%s)", (type, paths) => {
    expect(specs[type]?.linkable).toBe(true);
    for (const path of Array.isArray(paths) ? paths : [paths]) {
      const source = readFileSync(resolve(ROOT, "frontend", path), "utf8");
      expect(source).toContain("RelatedPanel");
      expect(source).not.toContain('post("/links"');
    }
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
        "capture_receipt", // delivery workflow; not a user relationship destination
        "goal_studio_session", // contextual conversation, not an operational Goal
        "goal_studio_revision", // approval workflow
        "course",
        "career_connection",
        "career_story",
        "external_event",
        "feed",
        "feed_item",
        "document",
        "expense",
        "income",
        "recurring_payment",
        "media_item",
        "media_collection",
        "media_consumption",
        "media_cycle",
        "media_unit",
        "flashcard_card",
        "career_action_proposal",
        "milestone",
        "note",
        "note_folder",
        "pomodoro_session",
        "review",
        "strategic_plan_revision",
        "study_area",
      ].sort(),
    );
  });
});
