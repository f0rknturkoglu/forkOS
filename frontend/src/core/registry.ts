/**
 * Modul registry.
 *
 * Yeni modul eklemek = modules/<ad>/index.ts + modules/index.ts'e bir satir.
 * Router, Today ekrani, Command Palette ve Settings BU LISTEDEN beslenir.
 * Bu dosyalarin disinda hicbir yere modul adi yazma.
 */
import type { ComponentType } from "react";
import { MODULE_GROUPS } from "./types";
import type { Command, ModuleGroup, ModuleSpec, TodayWidget, TodayZone } from "./types";
import { matchRoutePath } from "@/app/router";

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

export function enabledModules(): ModuleSpec[] {
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
  // Panel duzeni + hava durumu konumu -- ayarlardan gelen localStorage cache'i
  const columns = Number(settings["today.columns"] ?? 3);
  localStorage.setItem("lifeos.todayColumns", JSON.stringify(columns >= 1 && columns <= 4 ? columns : 3));
  const lat = Number(settings["weather.lat"] ?? 0);
  const lon = Number(settings["weather.lon"] ?? 0);
  if (lat || lon) {
    localStorage.setItem("lifeos.weather.lat", JSON.stringify(lat));
    localStorage.setItem("lifeos.weather.lon", JSON.stringify(lon));
  }
  const links = Array.isArray(settings["media.links"]) ? settings["media.links"] as { name: string; url: string }[] : [];
  externalCommands = links.map((link) => ({ id: `media.${link.name}`, label: `Open ${link.name}`, run: () => { window.open(link.url, "_blank", "noopener"); } }));
}

/** Panel (Today) sutun sayisi -- Ayarlar'daki "today.columns" degeri. */
export function todayColumns(): number {
  const value = Number(JSON.parse(localStorage.getItem("lifeos.todayColumns") ?? "3"));
  return value >= 1 && value <= 4 ? value : 3;
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

/** Bolge verilmemis widget "ritim"e duser -- eski kayitlar bozulmaz. */
function normalize(entry: ComponentType | TodayWidget): TodayWidget {
  return typeof entry === "function" ? { component: entry, zone: "rhythm" } : entry;
}

export const allTodayWidgets = () =>
  orderedModules().flatMap((m) => (m.todayWidgets ?? []).map(normalize));

export const todayWidgetsIn = (zone: TodayZone): ComponentType[] =>
  allTodayWidgets().filter((w) => w.zone === zone).map((w) => w.component);

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

/** Sol menu bunu okur. Modul adi App.tsx'e YAZILMAZ -- buradan gelir. */
export function pinnedModules(): ModuleSpec[] {
  return enabledModules().filter((m) => m.group === "pinned");
}

export function groupedModules(): { id: ModuleGroup; label: string; modules: ModuleSpec[] }[] {
  const modules = enabledModules().filter((m) => m.group !== "pinned");
  return MODULE_GROUPS.map((group) => ({
    ...group,
    modules: modules.filter((m) => (m.group ?? "system") === group.id),
  })).filter((group) => group.modules.length > 0);
}

/** Aktif rotanin sahibi modul -- baslik ve ikon icin. */
export function moduleForPath(path: string): ModuleSpec | undefined {
  return enabledModules().find((m) =>
    m.routes.some((route) => matchRoutePath(route.path, path) !== null),
  );
}

/** Ust seritte gorunecek baslik: once rotanin kendi adi, sonra modulunki. */
export function titleForPath(path: string): string | undefined {
  for (const module of enabledModules()) {
    const route = module.routes.find((candidate) => matchRoutePath(candidate.path, path) !== null);
    if (route) return route.title ?? module.title;
  }
  return undefined;
}
