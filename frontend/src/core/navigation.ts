import { MODULE_GROUPS } from "./types";
import type { ModuleGroup, ModuleSpec } from "./types";
import { findRouteMatch } from "@/app/router";

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
  const candidates = groups.flatMap((group) =>
    group.modules.flatMap((module) =>
      module.routes.map((route) => ({ path: route.path, group })),
    ),
  );
  return findRouteMatch(candidates, path)?.group ?? groups[0];
}

/** Navigation never targets a path pattern when the module has a concrete page. */
export function moduleTarget(module: ModuleSpec): string {
  return module.routes.find((route) => !route.path.split("/").some((part) => part.startsWith(":")))?.path
    ?? module.routes[0]?.path
    ?? "/";
}

export function groupTarget(group: NavigationGroup): string {
  return group.modules[0] ? moduleTarget(group.modules[0]) : "/";
}
