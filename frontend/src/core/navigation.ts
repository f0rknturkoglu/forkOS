import { MODULE_GROUPS } from "./types";
import type { ModuleGroup, ModuleSpec } from "./types";

export interface NavigationGroup {
  id: ModuleGroup;
  label: string;
  modules: ModuleSpec[];
}

export function navigationGroups(modules: ModuleSpec[]): NavigationGroup[] {
  const pinned = modules.filter((module) => module.group === "pinned");
  const grouped = MODULE_GROUPS.map((group) => ({
    ...group,
    modules: modules.filter((module) => (module.group ?? "system") === group.id),
  })).filter((group) => group.modules.length > 0);

  return [{ id: "pinned", label: "Bugün", modules: pinned }, ...grouped];
}

export function activeNavigationGroup(
  path: string,
  groups: NavigationGroup[],
): NavigationGroup {
  return groups.find((group) =>
    group.modules.some((module) => module.routes.some((route) => route.path === path)),
  ) ?? groups[0];
}

export function groupTarget(group: NavigationGroup): string {
  return group.modules[0]?.routes[0]?.path ?? "/";
}
