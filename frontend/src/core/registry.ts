/**
 * Modul registry.
 *
 * Yeni modul eklemek = modules/<ad>/index.ts + modules/index.ts'e bir satir.
 * Router, Today ekrani, Command Palette ve Settings BU LISTEDEN beslenir.
 * Bu dosyalarin disinda hicbir yere modul adi yazma.
 */
import type { ModuleSpec } from "./types";

const registry = new Map<string, ModuleSpec>();

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

export const allCommands = () => enabledModules().flatMap((m) => m.commands ?? []);
export const allTodayWidgets = () => enabledModules().flatMap((m) => m.todayWidgets ?? []);
export const allTodayStats = () => enabledModules().flatMap((m) => m.todayStats ?? []);
export const allRoutes = () => enabledModules().flatMap((m) => m.routes);
