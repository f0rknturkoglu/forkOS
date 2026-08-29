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
  allTodayWidgetViewsIncludingHidden,
  allRoutes,
  setTodayWidgetHidden,
  setTodayWidgetOrder,
} from "./registry";
import { focusedConfig, overviewConfig } from "./todayPresets";

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
  it("en az 14 kayitli widget, benzersiz kalici id'ler ve odakli varsayilan", () => {
    const widgets = allTodayWidgets();
    const ids = widgets.map((widget) => widget.id);
    expect(ids.length).toBeGreaterThanOrEqual(14);
    // Faz 20: odakli varsayilan -- akis/ikincil gizli, plan widget'lari acik.
    const visible = allTodayWidgetViews();
    expect(visible.some((view) => view.id === "today.agenda")).toBe(true);
    expect(visible.some((view) => view.id === "today.feed-stream")).toBe(false);
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
    // Odakli varsayilan: akis/ikincil gizli, plan + durum widget'lari acik.
    const visible = allTodayWidgetViews();
    expect(visible.length).toBeGreaterThanOrEqual(8);
    expect(visible.some((view) => view.id === "today.agenda")).toBe(true);
  });

  it("Faz 33: degerlendirme karti varsayilan Today'de TEK yuzeyden gelir", () => {
    // review.widget varsayilan gizli -- gunluk degerlendirme yuzeyi
    // DailyRhythmWidget'tir (haftalik giris noktasi orada korunur).
    const review = allTodayWidgets().find((widget) => widget.id === "review.widget");
    expect(review?.defaultVisible).toBe(false);
    expect(allTodayWidgetViews().some((view) => view.id === "review.widget")).toBe(false);
  });

  it("focused preset ikincil widget'lari gizler, overview temizler", () => {
    const focused = focusedConfig();
    expect(focused.hidden).toContain("today.feed-stream");
    expect(focused.hidden).not.toContain("today.agenda");
    setTodayWidgetHidden(focused.hidden);
    setTodayWidgetOrder(focused.order);
    expect(allTodayWidgetViews().some((view) => view.id === "today.feed-stream")).toBe(false);
    // Gizliler ayar listesinde geri gosterilebilir durumda gorunur.
    expect(allTodayWidgetViewsIncludingHidden().some((view) => view.id === "today.feed-stream")).toBe(true);

    const overview = overviewConfig();
    expect(overview.hidden).toEqual([]);
    setTodayWidgetHidden(overview.hidden);
    setTodayWidgetOrder(overview.order);
    expect(allTodayWidgetViews().some((view) => view.id === "today.feed-stream")).toBe(true);
  });

  it("eski modul ID sirasi widget id'lerine goc eder", () => {
    // Faz 5 legacy: modul id'leri. Bugun modulunun 4 widget'i var (Faz 25 ritim dahil).
    store.set("lifeos.widgetOrder", JSON.stringify(["today"]));
    const todayWidgetIds = allTodayWidgetViewsIncludingHidden()
      .filter((view) => view.moduleId === "today")
      .map((view) => view.id);
    expect(todayWidgetIds.length).toBe(4);
    // Kullanici sirasi yokken: migration modul sirasini widget sirasina acar;
    // odakli varsayilan yine uygulanir (tercih yok).
    expect(allTodayWidgetViews().length).toBeGreaterThanOrEqual(8);
    expect(allTodayWidgetViews().some((view) => view.id === "today.agenda")).toBe(true);
  });
});
