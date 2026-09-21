// @vitest-environment jsdom
/**
 * Home bileşen sözleşmesi (Productization P2).
 *
 * Home artık "her modülden biraz göster" panosu değil: iki katmanı var.
 *
 *   ÇEKİRDEK (`TodayWidget.core`) → Home iskeleti. Her zaman görünür,
 *     gizlenemez/sıralanamaz; DOM sırası dar ekranda okuma sırasıdır.
 *   İSTEĞE BAĞLI (core yok) → Ayarlar'dan gizlenir/sıralanır, iskeletin
 *     altında akar.
 *
 * Kapsam:
 *   - benzersiz kalıcı widget kimlikleri ve iki katmanın tam ayrımı,
 *   - çekirdek iskeletin SABİT sırası; eski gizleme kayıtlarının işlememesi,
 *   - isteğe bağlı yüzeylerin gizlenmesi/sıralanması ve preset'ler,
 *   - tercih değişiminin AYNI oturumda render'a yansıması (reaktivite),
 *   - sunucu anlık görüntüsünün yerel tercihi ezmemesi.
 *
 * `today` teknik ad alanı bilinçli olarak korunur; yalnız görünen ad Home'dur.
 */
import { act, cleanup, render, screen } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "@/modules"; // registerModule cagrilari
import {
  allTodayWidgetViews,
  allTodayWidgets,
  allTodayWidgetViewsIncludingHidden,
  allRoutes,
  allGlobalSurfaces,
  hydrateSettings,
  setTodayWidgetHidden,
  setTodayWidgetOrder,
  useTodayWidgetViews,
} from "./registry";
import { focusedConfig, overviewConfig } from "./todayPresets";

/** Çekirdek iskelet: DOM sırası = dar ekranda okuma sırası. */
const CORE_HOME = [
  "today.pending-decisions",
  "today.agenda",
  "today.deadlines",
  "today.career",
  "today.feed-stream",
  "learning.widget",
  "activity.heatmap",
];

/** İsteğe bağlı yüzeyler: kayıtlı, kullanıcı tercihine açık, iskeletin altında. */
const OPTIONAL_HOME = [
  "today.now-next",
  "today.rhythm",
  "today.quick-links",
  "activity.rhythm",
  "activity.widget",
  "inbox.widget",
  "flashcard.due",
  "bookmarks.queue",
  "calendar.events",
  "finance.recurring",
  "health.sources",
  "media.continue",
  "pomodoro.widget",
  "projects.widget",
  "review.widget",
  "todo.overdue",
];

/** jsdom ortaminda localStorage yok: tercih katmani icin Map tabanli taklit. */
const store = vi.hoisted(() => {
  const values = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
      clear: () => values.clear(),
    },
  });
  return values;
});

function ids(views: { id: string }[]): string[] {
  return views.map((view) => view.id);
}

function HomeProbe() {
  const widgets = useTodayWidgetViews();
  return createElement(
    "ul",
    null,
    widgets.map((view) => createElement("li", { key: view.id }, view.id)),
  );
}

describe("Home bileşen sözleşmesi", () => {
  beforeEach(() => store.clear());
  afterEach(cleanup);

  it("hızlı işlem dock'unu her rotada tek global yüzey olarak kaydeder", () => {
    expect(allGlobalSurfaces().some((Surface) => Surface.name === "QuickActionDock")).toBe(true);
  });

  it("benzersiz kalıcı kimlikler taşır", () => {
    const widgets = allTodayWidgets();
    const widgetIds = widgets.map((widget) => widget.id);
    expect(widgetIds.length).toBeGreaterThanOrEqual(14);
    expect(new Set(widgetIds).size).toBe(widgetIds.length);
    for (const widget of widgets) {
      expect(widget.id).toMatch(/^[a-z0-9.-]+$/);
      expect(widget.title.length).toBeGreaterThan(0);
    }
  });

  it("kayıtlı widget'lar çekirdek/isteğe bağlı ayrımına tam oturur", () => {
    expect(new Set(allTodayWidgets().map((widget) => widget.id))).toEqual(new Set([...CORE_HOME, ...OPTIONAL_HOME]));
    // `core` alanı Home iskeletini TEK başına belirler: ayrım başka yerde tutulmaz.
    for (const widget of allTodayWidgets()) {
      expect(Boolean(widget.core)).toBe(CORE_HOME.includes(widget.id));
    }
  });

  it("temiz kurulumda çekirdek iskelet sabit sırada görünür", () => {
    const visible = ids(allTodayWidgetViews());
    expect(visible.slice(0, CORE_HOME.length)).toEqual(CORE_HOME);
    // Varsayılan görünür isteğe bağlı yüzey: yalnız "Şimdi ve sırada".
    expect(visible.slice(CORE_HOME.length)).toEqual(["today.now-next"]);
  });

  it("çekirdek yüzeyler gizlenemez ve kullanıcı sırasıyla değişmez", () => {
    setTodayWidgetHidden([...CORE_HOME, ...OPTIONAL_HOME]);
    expect(ids(allTodayWidgetViews()).slice(0, CORE_HOME.length)).toEqual(CORE_HOME);

    setTodayWidgetOrder([...OPTIONAL_HOME].reverse());
    expect(ids(allTodayWidgetViews()).slice(0, CORE_HOME.length)).toEqual(CORE_HOME);
  });

  it("isteğe bağlı yüzeyler gizlenebilir ve kullanıcı sırasına uyar", () => {
    setTodayWidgetHidden(OPTIONAL_HOME);
    expect(ids(allTodayWidgetViews())).toEqual(CORE_HOME);

    // Açık tercih yazıldıktan sonra görünürlüğü kullanıcı belirler.
    setTodayWidgetHidden([]);
    expect(new Set(ids(allTodayWidgetViews()))).toEqual(new Set([...CORE_HOME, ...OPTIONAL_HOME]));

    setTodayWidgetOrder([...OPTIONAL_HOME].reverse());
    expect(ids(allTodayWidgetViews()).slice(CORE_HOME.length)).toEqual([...OPTIONAL_HOME].reverse());
  });

  it("sıfırlama varsayılan düzene döner", () => {
    setTodayWidgetHidden(["today.now-next"]);
    const hiddenNow = ids(allTodayWidgetViews());
    expect(hiddenNow).not.toContain("today.now-next");
    // Açık tercih yazıldığında görünürlüğü liste belirler (Faz 20 kuralı).
    expect(hiddenNow).toContain("todo.overdue");

    store.clear();
    expect(ids(allTodayWidgetViews())).toEqual([...CORE_HOME, "today.now-next"]);
  });

  it("presetler yalnız isteğe bağlı yüzeylere dokunur", () => {
    const focused = focusedConfig();
    expect(new Set(focused.hidden)).toEqual(new Set(OPTIONAL_HOME));
    expect(focused.hidden).not.toContain("today.agenda");
    setTodayWidgetHidden(focused.hidden);
    setTodayWidgetOrder(focused.order);
    expect(ids(allTodayWidgetViews())).toEqual(CORE_HOME);

    const overview = overviewConfig();
    expect(overview).toEqual({ order: [], hidden: [] });
    setTodayWidgetHidden(overview.hidden);
    setTodayWidgetOrder(overview.order);
    expect(new Set(ids(allTodayWidgetViews()))).toEqual(new Set([...CORE_HOME, ...OPTIONAL_HOME]));
  });

  it("bilinmeyen id uygulamayı bozmaz", () => {
    setTodayWidgetHidden(["bilinmeyen.widget"]);
    setTodayWidgetOrder(["bilinmeyen.widget", "ayrıca.yok"]);
    expect(new Set(ids(allTodayWidgetViews()))).toEqual(new Set([...CORE_HOME, ...OPTIONAL_HOME]));
  });

  it("gizlenen widget render edilmez ama modül rotası açık kalır", () => {
    setTodayWidgetHidden(["today.now-next"]);
    expect(ids(allTodayWidgetViews())).not.toContain("today.now-next");
    expect(allRoutes().length).toBeGreaterThan(0);
  });

  it("eski modül ID sırası widget sırasına göç eder", () => {
    localStorage.setItem("lifeos.widgetOrder", JSON.stringify(["today"]));
    const todayWidgetIds = ids(allTodayWidgetViewsIncludingHidden().filter((view) => view.moduleId === "today"));
    expect(new Set(todayWidgetIds)).toEqual(
      new Set([
        "today.pending-decisions",
        "today.agenda",
        "today.deadlines",
        "today.career",
        "today.feed-stream",
        "today.now-next",
        "today.rhythm",
        "today.quick-links",
      ]),
    );
    // Göç yalnız isteğe bağlı sırayı etkiler; iskelet sırası sabittir.
    expect(ids(allTodayWidgetViews()).slice(0, CORE_HOME.length)).toEqual(CORE_HOME);
  });

  it("tercih değişimi aynı oturumda render'ı günceller (reload yok)", () => {
    render(createElement(HomeProbe));
    expect(screen.getByText("today.now-next")).toBeTruthy();

    act(() => setTodayWidgetHidden(["today.now-next"]));
    expect(screen.queryByText("today.now-next")).toBeNull();

    act(() => setTodayWidgetHidden([]));
    expect(screen.getByText("today.now-next")).toBeTruthy();
  });

  it("başka sekmenin yazımı (storage olayı) render'ı tazeler", () => {
    render(createElement(HomeProbe));
    expect(screen.getByText("today.now-next")).toBeTruthy();

    // Başka sekme localStorage'a yazdı: bu sekmede yalnız `storage` olayı düşer.
    localStorage.setItem("forkos.todayPrefsTouched", "1");
    localStorage.setItem("forkos.todayWidgetHidden", JSON.stringify(["today.now-next"]));
    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", { key: "forkos.todayWidgetHidden", newValue: '["today.now-next"]' }),
      );
    });
    expect(screen.queryByText("today.now-next")).toBeNull();
  });

  it("sunucu anlık görüntüsü yerel tercihi EZMEZ, yalnız dokunulmamışken tohumlar", () => {
    // 1) Bu cihazda tercih yok: sunucudaki gizleme tohumlanır ve geçerli olur.
    hydrateSettings({ "today.widget_order": ["today.now-next"], "today.widget_hidden": ["today.now-next"] });
    expect(ids(allTodayWidgetViews())).not.toContain("today.now-next");

    // 2) Kullanıcı yerelde widget'ı açtı: sunucudaki eski liste artık kazanamaz.
    setTodayWidgetHidden([]);
    hydrateSettings({ "today.widget_order": [], "today.widget_hidden": ["today.now-next"] });
    expect(ids(allTodayWidgetViews())).toContain("today.now-next");
  });
});
