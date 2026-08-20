/**
 * Modul registry.
 *
 * Yeni modul eklemek = modules/<ad>/index.ts + modules/index.ts'e bir satir.
 * Router, Today ekrani, Command Palette ve Settings BU LISTEDEN beslenir.
 * Bu dosyalarin disinda hicbir yere modul adi yazma.
 */
import type { Command, ModuleSpec } from "./types";

const registry = new Map<string, ModuleSpec>();
let externalCommands: Command[] = [];

export function registerModule(spec: ModuleSpec): void {
  if (registry.has(spec.id)) throw new Error(`Modul zaten kayitli: ${spec.id}`);
  registry.set(spec.id, spec);
}

export const allModules = (): ModuleSpec[] => [...registry.values()];

export function enabledModules(): ModuleSpec[] {
  const disabled = new Set<string>(
    JSON.parse(localStorage.getItem("lifeos.disabledModules") ?? "[]"),
  );
  return allModules().filter((m) => !disabled.has(m.id));
}

export function hydrateSettings(settings: Record<string, unknown>): void {
  const disabled = Array.isArray(settings["modules.disabled"]) ? settings["modules.disabled"] : [];
  const order = Array.isArray(settings["today.widget_order"]) ? settings["today.widget_order"] : [];
  localStorage.setItem("lifeos.disabledModules", JSON.stringify(disabled));
  localStorage.setItem("lifeos.widgetOrder", JSON.stringify(order));
  localStorage.setItem("lifeos.pomodoroDefaults", JSON.stringify(settings["pomodoro.defaults"] ?? {}));
  const links = Array.isArray(settings["media.links"]) ? settings["media.links"] as { name: string; url: string }[] : [];
  externalCommands = links.map((link) => ({ id: `media.${link.name}`, label: `Open ${link.name}`, run: () => window.open(link.url, "_blank", "noopener") }));
}

export const allCommands = () => [...enabledModules().flatMap((m) => m.commands ?? []), ...externalCommands];
export const allTodayWidgets = () => {
  const order: string[] = JSON.parse(localStorage.getItem("lifeos.widgetOrder") ?? "[]");
  const modules = enabledModules();
  modules.sort((a, b) => {
    const ai = order.indexOf(a.id); const bi = order.indexOf(b.id);
    return (ai < 0 ? 999 : ai) - (bi < 0 ? 999 : bi);
  });
  return modules.flatMap((m) => m.todayWidgets ?? []);
};
export const allTodayStats = () => enabledModules().flatMap((m) => m.todayStats ?? []);
export const allRoutes = () => enabledModules().flatMap((m) => m.routes);
