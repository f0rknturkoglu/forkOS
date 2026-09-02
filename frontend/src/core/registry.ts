/**
 * Modul registry.
 *
 * Yeni modul eklemek = modules/<ad>/index.ts + modules/index.ts'e bir satir.
 * Router, Today ekrani, Command Palette ve Settings BU LISTEDEN beslenir.
 * Bu dosyalarin disinda hicbir yere modul adi yazma.
 */
import type { ComponentType } from "react";
import type { Command, ModuleSpec, TodayWidget } from "./types";
import { findRouteMatch } from "@/app/router";

const registry = new Map<string, ModuleSpec>();
let externalCommands: Command[] = [];

export function registerModule(spec: ModuleSpec): void {
  if (registry.has(spec.id)) {
    // Dev'de HMR modul dosyasini yeniden calistirir; ayni id ile ikinci kayit
    // hata degil, guncelleme demektir. Uretimde iki modul ayni id'yi
    // aliyorsa bu gercek bir cakismadir -- orada patlamali.
    if (import.meta.hot) {
      registry.set(spec.id, spec);
      return;
    }
    throw new Error(`Modul zaten kayitli: ${spec.id}`);
  }
  registry.set(spec.id, spec);
}

export const allModules = (): ModuleSpec[] => [...registry.values()];

function enabledModules(): ModuleSpec[] {
  const disabled = new Set<string>(JSON.parse(localStorage.getItem("lifeos.disabledModules") ?? "[]"));
  return allModules().filter((m) => !disabled.has(m.id));
}

/** Header'in tek modul kaynagi; isimler App katmaninda tekrar edilmez.
 *  hidden moduller nav'da yer tutmaz (rotalar/widget'lar ayakta kalir). */
export const navigationModules = (): ModuleSpec[] => enabledModules().filter((m) => !m.hidden);

export function hydrateSettings(settings: Record<string, unknown>): void {
  const disabled = Array.isArray(settings["modules.disabled"]) ? settings["modules.disabled"] : [];
  const order = Array.isArray(settings["today.widget_order"]) ? settings["today.widget_order"] : [];
  const widgetHidden = Array.isArray(settings["today.widget_hidden"]) ? settings["today.widget_hidden"] : [];
  localStorage.setItem("lifeos.disabledModules", JSON.stringify(disabled));
  localStorage.setItem("lifeos.widgetOrder", JSON.stringify(order));
  // Faz 19: widget kimlikli siralama + gizleme (modul ID sirasi legacy kalir).
  localStorage.setItem("lifeos.todayWidgetOrder", JSON.stringify(order));
  localStorage.setItem("lifeos.todayWidgetHidden", JSON.stringify(widgetHidden));
  localStorage.setItem("lifeos.pomodoroDefaults", JSON.stringify(settings["pomodoro.defaults"] ?? {}));
  const lat = Number(settings["weather.lat"] ?? 0);
  const lon = Number(settings["weather.lon"] ?? 0);
  if (lat || lon) {
    localStorage.setItem("lifeos.weather.lat", JSON.stringify(lat));
    localStorage.setItem("lifeos.weather.lon", JSON.stringify(lon));
  }
  const links = Array.isArray(settings["media.links"])
    ? (settings["media.links"] as { name: string; url: string }[])
    : [];
  externalCommands = links.map((link) => ({
    id: `media.${link.name}`,
    label: `Open ${link.name}`,
    run: () => {
      window.open(link.url, "_blank", "noopener");
    },
  }));
}
export const allCommands = () => [...enabledModules().flatMap((m) => m.commands ?? []), ...externalCommands];
/** Ayarlardaki siraya gore modulleri dizer. */
function orderedModules(): ModuleSpec[] {
  const order: string[] = JSON.parse(localStorage.getItem("lifeos.widgetOrder") ?? "[]");
  return [...enabledModules()].sort((a, b) => {
    const ai = order.indexOf(a.id);
    const bi = order.indexOf(b.id);
    return (ai < 0 ? 999 : ai) - (bi < 0 ? 999 : bi);
  });
}

export const allTodayWidgets = () => enabledModules().flatMap((m) => m.todayWidgets ?? []);
export const allGlobalSurfaces = () => enabledModules().flatMap((m) => m.globalSurfaces ?? []);

export interface TodayWidgetView {
  id: string;
  title: string;
  widget: TodayWidget;
  moduleId: string;
}

/** Kullanicinin widget tercihleri (Faz 19): sirala + gizle. */
function readWidgetPrefs(): { order: string[]; hidden: Set<string>; touched: boolean } {
  const known = new Set(allTodayWidgets().map((w) => w.id));
  const touched = localStorage.getItem("lifeos.todayPrefsTouched") === "1";
  const rawOrder: unknown = JSON.parse(localStorage.getItem("lifeos.todayWidgetOrder") ?? "null");
  // Eski (Faz 5) deger: modul ID'leri. Widget id'lerinden hicbiri yoksa bu
  // hala modul sirasidir -- her modulun widget'larina acilir (migration).
  const legacy: string[] = JSON.parse(localStorage.getItem("lifeos.widgetOrder") ?? "[]");
  let order: string[] = [];
  if (Array.isArray(rawOrder) && rawOrder.some((id) => known.has(String(id)))) {
    order = rawOrder.map(String);
  } else if (legacy.length > 0) {
    const byModule = new Map(enabledModules().map((m) => [m.id, (m.todayWidgets ?? []).map((w) => w.id)]));
    order = legacy.flatMap((mid) => byModule.get(mid) ?? []);
  }
  const storedHidden = (JSON.parse(localStorage.getItem("lifeos.todayWidgetHidden") ?? "[]") as string[]).filter((id) =>
    known.has(id),
  );
  // Eski odakli varsayilan, feed gibi sonradan temel deneyime alinan
  // widget'lari hidden listesinde birakabilir. Kullanici Today duzenine henuz
  // dokunmadiysa yeni defaultVisible sozlesmesi kazanir; acik tercihler korunur.
  const hidden = new Set<string>(touched ? storedHidden : []);
  return { order: order.filter((id) => known.has(id)), hidden, touched };
}

/**
 * Panelde gorunecek widget'lar, kullanici sirasi + gizleme uygulanmis.
 * Kullanici sirasindaki widget'lar once gelir; sirasizlar varsayilan
 * slot/order'a duser. Bilinmeyen id'ler guvenle yok sayilir.
 */
export function allTodayWidgetViews(): TodayWidgetView[] {
  const { order, hidden, touched } = readWidgetPrefs();
  const userIndex = new Map(order.map((id, i) => [id, i]));
  const views: TodayWidgetView[] = [];
  for (const module of enabledModules()) {
    for (const widget of module.todayWidgets ?? []) {
      views.push({ id: widget.id, title: widget.title, widget, moduleId: module.id });
    }
  }
  // Tercih yoksa (temiz kurulum) defaultVisible uygulanir = odakli varsayilan;
  // kullanici/preset tercih yazdiysa ACIK liste gecerli olur (Faz 20).
  return views
    .filter((view) => !hidden.has(view.id) && (touched || view.widget.defaultVisible !== false))
    .sort((a, b) => {
      const ai = userIndex.has(a.id) ? userIndex.get(a.id)! : Number.MAX_SAFE_INTEGER;
      const bi = userIndex.has(b.id) ? userIndex.get(b.id)! : Number.MAX_SAFE_INTEGER;
      if (ai !== bi) return ai - bi;
      return a.widget.order - b.widget.order || a.id.localeCompare(b.id);
    });
}

/**
 * Panel sutunundaki widget'lar (kullanici sirasi + gizleme uygulanir).
 * Esitlikte varsayilan order korunur (Array#sort kararli).
 */
/**
 * Ayarlar ekrani icin: gizliler DAHIL tum widget'lar (siralama uygulanir).
 * Gizli bir widget listede gorunur ki geri gosterilebilsin.
 */
export function allTodayWidgetViewsIncludingHidden(): TodayWidgetView[] {
  const { order } = readWidgetPrefs();
  const userIndex = new Map(order.map((id, i) => [id, i]));
  const views: TodayWidgetView[] = [];
  for (const module of enabledModules()) {
    for (const widget of module.todayWidgets ?? []) {
      views.push({ id: widget.id, title: widget.title, widget, moduleId: module.id });
    }
  }
  return views.sort((a, b) => {
    const ai = userIndex.has(a.id) ? userIndex.get(a.id)! : Number.MAX_SAFE_INTEGER;
    const bi = userIndex.has(b.id) ? userIndex.get(b.id)! : Number.MAX_SAFE_INTEGER;
    if (ai !== bi) return ai - bi;
    return a.widget.order - b.widget.order || a.id.localeCompare(b.id);
  });
}

/** Ayarlar ekrani: siralamayi kaydeder (backend'e yazma cagiran taraf). */
export function setTodayWidgetOrder(ids: string[]): void {
  localStorage.setItem("lifeos.todayPrefsTouched", "1");
  localStorage.setItem("lifeos.todayWidgetOrder", JSON.stringify(ids));
}

export function setTodayWidgetHidden(ids: string[]): void {
  localStorage.setItem("lifeos.todayPrefsTouched", "1");
  localStorage.setItem("lifeos.todayWidgetHidden", JSON.stringify(ids));
}

/** Varsayilana don: kullanici sirasi/gizleme temizlenir. */
export function resetTodayWidgetPrefs(): void {
  localStorage.removeItem("lifeos.todayPrefsTouched");
  localStorage.removeItem("lifeos.todayWidgetOrder");
  localStorage.removeItem("lifeos.todayWidgetHidden");
}

export const allTodayStats = () => orderedModules().flatMap((m) => m.todayStats ?? []);
export const allRoutes = () => enabledModules().flatMap((m) => m.routes);

/** Aktif rotanin sahibi modul -- baslik ve ikon icin. */
export function moduleForPath(path: string): ModuleSpec | undefined {
  const candidates = enabledModules().flatMap((module) => module.routes.map((route) => ({ path: route.path, module })));
  return findRouteMatch(candidates, path)?.module;
}

/** Ust seritte gorunecek baslik: once rotanin kendi adi, sonra modulunki. */
export function titleForPath(path: string): string | undefined {
  const candidates = enabledModules().flatMap((module) => module.routes.map((route) => ({ ...route, module })));
  const match = findRouteMatch(candidates, path);
  return match ? (match.title ?? match.module.title) : undefined;
}
