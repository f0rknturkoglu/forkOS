// @vitest-environment jsdom
/**
 * Home bileşen sözleşmesi (Productization P2).
 *
 * Home artık "her modülden biraz göster" panosu değil: temiz kurulumda yalnız
 * yürütmeyle ilgili yüzeyler görünür, geri kalanı kayıtlı ama ikincil kalır.
 *
 * Kapsam:
 *   - benzersiz kalıcı widget kimlikleri,
 *   - temiz kurulumda görünen TAM set (sakin varsayılan),
 *   - ikincil yüzeylerin varsayılan gizliliği ve Ayarlar'dan geri açılabilmesi,
 *   - kullanıcı sırası/gizleme tercihinin korunması,
 *   - eski (Faz 5) modül sırasının widget sırasına göçü.
 *
 * `today` teknik ad alanı bilinçli olarak korunur; yalnız görünen ad Home'dur.
 */
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import "@/modules"; // registerModule cagrilari
import {
  allTodayWidgetViews,
  allTodayWidgets,
  allTodayWidgetViewsIncludingHidden,
  allRoutes,
  allGlobalSurfaces,
  setTodayWidgetHidden,
  setTodayWidgetOrder,
} from "./registry";
import { focusedConfig, overviewConfig } from "./todayPresets";

/** Temiz kurulumda görünen yüzeyler: yürütme odaklı, bilinçli olarak az. */
const FOCUSED_HOME = ["today.pending-decisions", "today.attention", "today.now-next", "today.agenda"];

/** İkincil: kayıtlı ve açılabilir, ama varsayılan Home'da görünmez. */
const SECONDARY_HOME = [
  "today.feed-stream",
  "today.rhythm",
  "today.quick-links",
  "activity.heatmap",
  "activity.rhythm",
  "activity.widget",
  "inbox.widget",
  "learning.widget",
  "flashcard.due",
  "bookmarks.queue",
  "calendar.events",
  "documents.recent",
  "finance.recurring",
  "health.sources",
  "media.continue",
  "pomodoro.widget",
  "projects.widget",
  "review.widget",
  "todo.overdue",
];

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

describe("Home bileşen sözleşmesi", () => {
  it("hızlı işlem dock'unu her rotada tek global yüzey olarak kaydeder", () => {
    expect(allGlobalSurfaces().some((Surface) => Surface.name === "QuickActionDock")).toBe(true);
  });

  it("benzersiz kalıcı kimlikler ve kalıcı başlıklar taşır", () => {
    const widgets = allTodayWidgets();
    const ids = widgets.map((widget) => widget.id);
    expect(ids.length).toBeGreaterThanOrEqual(14);
    expect(new Set(ids).size).toBe(ids.length);
    for (const widget of widgets) {
      expect(widget.id).toMatch(/^[a-z0-9.-]+$/);
      expect(widget.title.length).toBeGreaterThan(0);
    }
  });

  it("temiz kurulumda yalnız yürütme odaklı yüzeyler görünür", () => {
    expect(allTodayWidgetViews().map((view) => view.id)).toEqual(FOCUSED_HOME);
  });

  it("ikincil yüzeylerin hepsi kayıtlı, varsayılan gizli ve geri açılabilir", () => {
    const visible = new Set(allTodayWidgetViews().map((view) => view.id));
    const registered = new Set(allTodayWidgets().map((widget) => widget.id));
    for (const id of SECONDARY_HOME) {
      expect(registered.has(id)).toBe(true);
      expect(visible.has(id)).toBe(false);
    }
    // Ayarlar > Home: gizliler listede görünür ki geri açılabilsin.
    const includable = new Set(allTodayWidgetViewsIncludingHidden().map((view) => view.id));
    for (const id of SECONDARY_HOME) expect(includable.has(id)).toBe(true);

    // Kullanıcı açıkça isterse hepsi yeniden görünür (güç kullanıcı yolu).
    setTodayWidgetHidden([]);
    const reopened = new Set(allTodayWidgetViews().map((view) => view.id));
    for (const id of SECONDARY_HOME) expect(reopened.has(id)).toBe(true);
  });

  it("kullanici sirasi render sirasini degistirir", () => {
    const order = allTodayWidgetViews().map((view) => view.id);
    // Ayarlar ekrani sirayi ve gizlemeyi BIRLIKTE yazar (tek tercih nesnesi).
    setTodayWidgetHidden(SECONDARY_HOME);
    setTodayWidgetOrder([...order].reverse());
    expect(allTodayWidgetViews().map((view) => view.id)).toEqual([...order].reverse());
  });

  it("gizlenen widget render edilmez ama modul rotasi acik kalir", () => {
    const target = allTodayWidgets()[0];
    setTodayWidgetHidden([target.id]);
    expect(allTodayWidgetViews().map((view) => view.id)).not.toContain(target.id);
    expect(allRoutes().length).toBeGreaterThan(0);
  });

  it("bilinmeyen id uygulamayi bozmaz", () => {
    setTodayWidgetHidden([...SECONDARY_HOME, "bilinmeyen.widget"]);
    setTodayWidgetOrder(["bilinmeyen.widget", "ayrıca.yok"]);
    expect([...allTodayWidgetViews().map((view) => view.id)].sort()).toEqual([...FOCUSED_HOME].sort());
  });

  it("presetler: odaklı ikincilleri gizler, genel bakış hepsini açar", () => {
    const focused = focusedConfig();
    expect(focused.hidden).toContain("today.feed-stream");
    expect(focused.hidden).toContain("activity.heatmap");
    expect(focused.hidden).not.toContain("today.agenda");
    setTodayWidgetHidden(focused.hidden);
    setTodayWidgetOrder(focused.order);
    expect([...allTodayWidgetViews().map((view) => view.id)].sort()).toEqual([...FOCUSED_HOME].sort());

    const overview = overviewConfig();
    expect(overview.hidden).toEqual([]);
    setTodayWidgetHidden(overview.hidden);
    setTodayWidgetOrder(overview.order);
    expect(allTodayWidgetViews().length).toBeGreaterThan(FOCUSED_HOME.length);
    expect(allTodayWidgetViews().some((view) => view.id === "today.feed-stream")).toBe(true);
  });

  it("eski varsayilan gizleme kaydini yok sayar ama acik kullanici tercihini korur", () => {
    store.set("lifeos.todayWidgetHidden", JSON.stringify(["today.agenda"]));
    // Dokunulmamış tercih: yeni varsayılan kazanır.
    expect(allTodayWidgetViews().some((view) => view.id === "today.agenda")).toBe(true);

    // Kullanıcı açıkça gizlerse saygı görür (varsayılanı açık olsa bile).
    setTodayWidgetHidden(["today.agenda"]);
    expect(allTodayWidgetViews().some((view) => view.id === "today.agenda")).toBe(false);
  });

  it("eski modul ID sirasi widget id'lerine goc eder", () => {
    store.set("lifeos.widgetOrder", JSON.stringify(["today"]));
    const todayWidgetIds = allTodayWidgetViewsIncludingHidden()
      .filter((view) => view.moduleId === "today")
      .map((view) => view.id);
    expect(todayWidgetIds.length).toBe(7);
    // Modül sırası göç eder; temiz kurulum varsayılanı yine yürütme odaklıdır.
    expect([...allTodayWidgetViews().map((view) => view.id)].sort()).toEqual([...FOCUSED_HOME].sort());
  });
});
