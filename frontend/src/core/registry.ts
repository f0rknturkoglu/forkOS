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
  const disabled = new Set<string>(
    JSON.parse(localStorage.getItem("lifeos.disabledModules") ?? "[]"),
  );
  return allModules().filter((m) => !disabled.has(m.id));
}

/** Header'in tek modul kaynagi; isimler App katmaninda tekrar edilmez. */
export const navigationModules = (): ModuleSpec[] => enabledModules();

export function hydrateSettings(settings: Record<string, unknown>): void {
  const disabled = Array.isArray(settings["modules.disabled"]) ? settings["modules.disabled"] : [];
  const order = Array.isArray(settings["today.widget_order"]) ? settings["today.widget_order"] : [];
  localStorage.setItem("lifeos.disabledModules", JSON.stringify(disabled));
  localStorage.setItem("lifeos.widgetOrder", JSON.stringify(order));
  localStorage.setItem("lifeos.pomodoroDefaults", JSON.stringify(settings["pomodoro.defaults"] ?? {}));
  const lat = Number(settings["weather.lat"] ?? 0);
  const lon = Number(settings["weather.lon"] ?? 0);
  if (lat || lon) {
    localStorage.setItem("lifeos.weather.lat", JSON.stringify(lat));
    localStorage.setItem("lifeos.weather.lon", JSON.stringify(lon));
  }
  const links = Array.isArray(settings["media.links"]) ? settings["media.links"] as { name: string; url: string }[] : [];
  externalCommands = links.map((link) => ({ id: `media.${link.name}`, label: `Open ${link.name}`, run: () => { window.open(link.url, "_blank", "noopener"); } }));
}
export const allCommands = () => [...enabledModules().flatMap((m) => m.commands ?? []), ...externalCommands];
/** Ayarlardaki siraya gore modulleri dizer. */
function orderedModules(): ModuleSpec[] {
  const order: string[] = JSON.parse(localStorage.getItem("lifeos.widgetOrder") ?? "[]");
  return [...enabledModules()].sort((a, b) => {
    const ai = order.indexOf(a.id); const bi = order.indexOf(b.id);
    return (ai < 0 ? 999 : ai) - (bi < 0 ? 999 : bi);
  });
}

function normalize(entry: ComponentType | TodayWidget): TodayWidget {
  return typeof entry === "function" ? { component: entry } : entry;
}

export const allTodayWidgets = () =>
  orderedModules().flatMap((m) => (m.todayWidgets ?? []).map(normalize));
/**
 * Panel sutunundaki widget'lar, `order` alanina gore sirali.
 * Esitlikte modul sirasi korunur (Array#sort kararli).
 */
export const allTodayWidgetsIn = (slot: "left" | "center" | "right"): ComponentType[] =>
  allTodayWidgets()
    .filter((w) => (w.slot ?? "center") === slot)
    .sort((a, b) => (a.order ?? 50) - (b.order ?? 50))
    .map((w) => w.component);
export const allTodayStats = () => orderedModules().flatMap((m) => m.todayStats ?? []);
export const allRoutes = () => enabledModules().flatMap((m) => m.routes);

/** Aktif rotanin sahibi modul -- baslik ve ikon icin. */
export function moduleForPath(path: string): ModuleSpec | undefined {
  const candidates = enabledModules().flatMap((module) =>
    module.routes.map((route) => ({ path: route.path, module })),
  );
  return findRouteMatch(candidates, path)?.module;
}

/** Ust seritte gorunecek baslik: once rotanin kendi adi, sonra modulunki. */
export function titleForPath(path: string): string | undefined {
  const candidates = enabledModules().flatMap((module) =>
    module.routes.map((route) => ({ ...route, module })),
  );
  const match = findRouteMatch(candidates, path);
  return match ? match.title ?? match.module.title : undefined;
}
