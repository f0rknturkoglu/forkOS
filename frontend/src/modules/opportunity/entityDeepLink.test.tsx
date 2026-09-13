// @vitest-environment jsdom
/**
 * Entity derin bağlantı zinciri (Faz 8).
 *
 * Kayıt defteri rotası → adres çubuğu → sayfanın açtığı sekme. Graf, Today ve
 * global arama aynı `entityRoute()` çıktısını kullanır; bu test rotanın
 * gerçekten DOĞRU sekmeyi açtığını kilitler (eskiden `?story=` bağlantısı
 * "İşler" sekmesini açıyordu).
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { entityRoute, hydrateEntityRegistry, type EntityTypeSpec } from "@/core/entityRegistry";

// jsdom bu kurulumda localStorage sağlamıyor.
vi.hoisted(() => {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => store.set(key, value),
      removeItem: (key: string) => store.delete(key),
      clear: () => store.clear(),
    },
  });
});

import type { OpportunityBrowseFilters } from "./opportunityBrowse";
import { parseOpportunityUrl, serializeOpportunityUrl } from "./opportunityUrl";

/** Backend `EntityTypeSpec` kayıtları (fırsat modülü). */
const SPECS: EntityTypeSpec[] = [
  {
    type: "opportunity",
    label: "Fırsat",
    label_plural: "Fırsatlar",
    route: "/opportunities?focus={id}",
    icon: "Target",
    searchable: true,
    linkable: true,
  },
  {
    type: "career_story",
    label: "Kariyer hikâyesi",
    label_plural: "Kariyer hikâyeleri",
    route: "/opportunities?story={id}",
    icon: "BookOpen",
    searchable: true,
    linkable: false,
  },
  {
    type: "career_connection",
    label: "Kariyer bağlantısı",
    label_plural: "Kariyer bağlantıları",
    route: "/opportunities?connection={id}",
    icon: "Users",
    searchable: true,
    linkable: false,
  },
];

const BASE: OpportunityBrowseFilters = { section: "jobs", sort: "score", offset: 0, limit: 60 };

/** `#/opportunities?story=x` → `story=x` */
function queryOf(route: string): string {
  return route.slice(route.indexOf("?") + 1);
}

describe("entity deep links open the right workspace", () => {
  beforeEach(() => hydrateEntityRegistry(SPECS));

  it.each([
    ["career_story", "story-1", "career"],
    ["career_connection", "conn-1", "career"],
    ["opportunity", "opp-1", "jobs"],
  ])("%s rotası %s sekmesini açar", (type, id, expectedTab) => {
    const parsed = parseOpportunityUrl(new URLSearchParams(queryOf(entityRoute(type, id))), BASE);
    expect(parsed.tab).toBe(expectedTab);
  });

  it("ilan bağlantısı kaydı focus olarak taşır", () => {
    const parsed = parseOpportunityUrl(
      new URLSearchParams(queryOf(entityRoute("opportunity", "opp-9"))),
      BASE,
    );
    expect(parsed.focus).toBe("opp-9");
  });

  it("hikâye bağlantısı kaydı story olarak taşır ve tekrar yazıldığında korunur", () => {
    const parsed = parseOpportunityUrl(
      new URLSearchParams(queryOf(entityRoute("career_story", "story-7"))),
      BASE,
    );
    expect(parsed.story).toBe("story-7");

    const rewritten = serializeOpportunityUrl({
      tab: parsed.tab,
      focus: parsed.focus,
      story: parsed.story,
      connection: parsed.connection,
      filters: parsed.filters,
      view: parsed.view,
    });
    expect(new URLSearchParams(rewritten).get("story")).toBe("story-7");
    expect(new URLSearchParams(rewritten).get("tab")).toBe("career");
  });

  it("bilinmeyen tip kök rotaya düşer (kırık bağlantı üretmez)", () => {
    expect(entityRoute("bilinmeyen_tip", "x")).toBe("#/");
  });
});
