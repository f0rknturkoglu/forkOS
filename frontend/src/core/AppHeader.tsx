import type { ReactNode } from "react";
import { Moon, Search, Sun } from "lucide-react";
import { openCommandPalette } from "./CommandPalette";
import { NotificationPanel } from "./NotificationPanel";
import { StatusLed } from "./StatusLed";
import { navigationModules } from "./registry";
import { Kbd, cx, useTheme } from "./ui";
import { activeNavigationGroup, groupTarget, moduleTarget, navigationGroups } from "./navigation";
import { findRouteMatch } from "@/app/router";
import type { NavigationGroup } from "./navigation";
import type { ModuleSpec } from "./types";

function ModuleTab({ module, active }: { module: ModuleSpec; active: boolean }) {
  const target = moduleTarget(module);
  const Icon = module.icon;

  return (
    <a
      href={`#${target}`}
      aria-current={active ? "page" : undefined}
      className={cx(
        "flex h-9 shrink-0 items-center gap-1.5 border-b-2 text-meta transition-colors",
        active ? "border-accent text-primary" : "border-transparent text-muted hover:text-primary",
      )}
    >
      {Icon && <Icon size={13} className="shrink-0" />}
      {module.title}
    </a>
  );
}

export function NavigationRows({
  path,
  groups,
  utilities,
}: {
  path: string;
  groups: NavigationGroup[];
  utilities: ReactNode;
}) {
  const activeGroup = activeNavigationGroup(path, groups);
  const activeModule = findRouteMatch(
    activeGroup.modules.flatMap((module) => module.routes.map((route) => ({ path: route.path, module }))),
    path,
  )?.module;

  return (
    <header className="relative z-header shrink-0 border-b border-subtle bg-canvas/95 backdrop-blur">
      {/* backdrop-blur stacking context yaratiyor; z yokken bildirim dropdown'i
          (iceride z-popover) sayfa ici sticky toolbar'larin (z-sticky) ALTINDA kaliyor.
          Header'i z-header yap: toolbar'larin (sticky) ustune, drawer/modal/toast'larin altina. */}
      <div className="mx-auto flex h-12 w-full max-w-[1600px] items-center gap-1.5 px-4 sm:gap-3 sm:px-5 lg:px-6">
        <a href="#/" className="flex shrink-0 items-center gap-2" aria-label="forkOS Bugün">
          <span className="flex h-5 w-5 items-center justify-center rounded-sm bg-primary  text-meta text-canvas">
            f
          </span>
          <span className="hidden  text-heading text-primary sm:inline">forkOS</span>
        </a>

        <nav
          aria-label="Ana bölümler"
          className="flex min-w-0 flex-1 items-center gap-0.5 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden sm:gap-1"
        >
          {groups.map((group) => (
            <a
              key={group.id}
              href={`#${groupTarget(group)}`}
              aria-current={group.id === activeGroup.id ? "page" : undefined}
              className={cx(
                "shrink-0 border-b px-1.5 py-1 text-micro transition-colors sm:px-2 sm:text-meta",
                group.id === activeGroup.id
                  ? "border-accent text-primary"
                  : "border-transparent text-muted hover:text-primary",
              )}
            >
              {group.label}
            </a>
          ))}
        </nav>

        <div className="flex shrink-0 items-center gap-0.5 sm:gap-1.5">{utilities}</div>
      </div>

      <nav aria-label="Modüller" className="border-t border-subtle/70">
        <div className="mx-auto flex h-9 w-full max-w-[1600px] items-center gap-4 overflow-x-auto px-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden sm:px-5 lg:px-6">
          {activeGroup.modules.map((module) => (
            <ModuleTab key={module.id} module={module} active={activeModule?.id === module.id} />
          ))}
        </div>
      </nav>
    </header>
  );
}

function HeaderUtilities() {
  const [theme, setTheme] = useTheme();

  return (
    <>
      <StatusLed />
      <button
        type="button"
        onClick={openCommandPalette}
        className="hidden h-8 w-56 items-center gap-2 rounded-control border border-subtle bg-surface px-2.5 text-left text-meta text-muted transition-colors hover:border-strong lg:flex"
      >
        <Search size={14} />
        <span className="flex-1 truncate">Ara veya komut…</span>
        <Kbd>Ctrl K</Kbd>
      </button>
      <button
        type="button"
        onClick={openCommandPalette}
        title="Ara (Ctrl+K)"
        aria-label="Ara"
        className="flex h-8 w-8 items-center justify-center text-muted transition-colors hover:text-primary lg:hidden"
      >
        <Search size={15} />
      </button>
      <NotificationPanel />
      <button
        type="button"
        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        title="Temayı değiştir"
        aria-label="Temayı değiştir"
        className="flex h-8 w-8 items-center justify-center text-muted transition-colors hover:text-primary"
      >
        {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
      </button>
    </>
  );
}

export function AppHeader({ path }: { path: string }) {
  return <NavigationRows path={path} groups={navigationGroups(navigationModules())} utilities={<HeaderUtilities />} />;
}
