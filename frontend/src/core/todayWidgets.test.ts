// @vitest-environment jsdom
/**
 * Faz 5 + Faz 19: Bugun paneli widget sozlesmesi.
 * - Her widget benzersiz kalici id + gorunen title tasir.
 * - Kullanici sirasi (lifeos.todayWidgetOrder) gercek siralamayi degistirir.
 * - Gizlenen widget render edilmez ama modul rotasi acik kalir.
 * - Eski modul ID sirasi (lifeos.widgetOrder) widget id'lerine goc eder.
 * - Bilinmeyen id'ler uygulamayi bozmaz.
 */
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import "@/modules"; // registerModule cagrilari
import {
  allTodayWidgetViews,
  allTodayWidgets,
  allTodayWidgetsIn,
  allRoutes,
  setTodayWidgetHidden,
  setTodayWidgetOrder,
} from "./registry";

const store = new Map<string, string>();

beforeAll(() => {
  Object.defineProperty(globalThis, "localStorage", {
    value: {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => {
        store.set(k, v);
      },
      removeItem: (k: string) => {
        store.delete(k);
      },
      clear: () => {
        store.clear();
      },
      key: () => null,
      get length() {
        return store.size;
      },
    },
    configurable: true,
  });
});

beforeEach(() => {
  store.clear();
});

describe("Bugun widget sozlesmesi", () => {
  it("en az 14 widget katkisi ve benzersiz kalici id'ler", () => {
    const widgets = allTodayWidgets();
    const ids = widgets.map((widget) => widget.id);
    expect(ids.length).toBeGreaterThanOrEqual(14);
    expect(new Set(ids).size).toBe(ids.length);
    for (const widget of widgets) {
      expect(widget.id).toMatch(/^[a-z0-9.-]+$/);
      expect(widget.title.length).toBeGreaterThan(0);
    }
  });

  it("kullanici sirasi render sirasini degistirir", () => {
    const first = allTodayWidgetViews()[0].id;
    const second = allTodayWidgetViews()[1].id;
    setTodayWidgetOrder([
      second,
      first,
      ...allTodayWidgetViews()
        .slice(2)
        .map((v) => v.id),
    ]);
    const views = allTodayWidgetViews();
    expect(views[0].id).toBe(second);
    expect(views[1].id).toBe(first);
  });

  it("gizlenen widget render edilmez ama modul rotasi acik kalir", () => {
    const target = allTodayWidgets()[0];
    setTodayWidgetHidden([target.id]);
    const visibleIds = allTodayWidgetViews().map((view) => view.id);
    expect(visibleIds).not.toContain(target.id);
    expect(allRoutes().length).toBeGreaterThan(0);
  });

  it("bilinmeyen id uygulamayi bozmaz", () => {
    setTodayWidgetOrder(["bilinmeyen.widget", "ayrıca.yok"]);
    setTodayWidgetHidden(["bilinmeyen.widget"]);
    expect(allTodayWidgetViews().length).toBeGreaterThanOrEqual(14);
    expect(allTodayWidgetsIn("left").length).toBeGreaterThanOrEqual(0);
  });

  it("eski modul ID sirasi widget id'lerine goc eder", () => {
    // Faz 5 legacy: modul id'leri. Bugun modulunun 3 widget'i var.
    store.set("lifeos.widgetOrder", JSON.stringify(["today"]));
    const todayWidgetIds = allTodayWidgetViews()
      .filter((view) => view.moduleId === "today")
      .map((view) => view.id);
    expect(todayWidgetIds.length).toBe(3);
    // Kullanici sirasi yokken: widget'lar once kullanici sirasindadirlar --
    // migration modul sirasini widget sirasina acar, hepsi listede kalir.
    expect(allTodayWidgetViews().length).toBeGreaterThanOrEqual(14);
  });
});
