import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, LayoutGrid, PanelLeftClose, PanelLeftOpen, Plus, Search } from "lucide-react";
import { findRouteMatch } from "@/app/router";
import { openCapture } from "@/core/CaptureDialog";
import { openCommandPalette } from "@/core/CommandPalette";
import { moduleTarget, navigationGroups } from "@/core/navigation";
import { requestNavigation } from "@/core/navigationGuard";
import { navigationModules } from "@/core/registry";
import type { ModuleGroup, ModuleSpec } from "@/core/types";
import { cx } from "@/core/ui";

const OPEN_GROUPS_KEY = "forkos.sidebar.groups";

function initialOpenGroups(): Set<ModuleGroup> {
  try {
    const raw = JSON.parse(localStorage.getItem(OPEN_GROUPS_KEY) ?? "null");
    if (Array.isArray(raw)) return new Set(raw as ModuleGroup[]);
  } catch {
    // Bozuk gorunum tercihi navigasyonu kitlemesin; guvenli varsayilana don.
  }
  return new Set<ModuleGroup>(["capture", "do", "track"]);
}

function moduleIsActive(module: ModuleSpec, path: string): boolean {
  return Boolean(findRouteMatch(module.routes, path));
}

function SidebarLink({
  href,
  label,
  active,
  icon: Icon,
  collapsed,
  child = false,
  onNavigate,
}: {
  href: string;
  label: string;
  active: boolean;
  icon?: ModuleSpec["icon"];
  collapsed: boolean;
  child?: boolean;
  onNavigate: () => void;
}) {
  const LinkIcon = Icon ?? LayoutGrid;
  return (
    <a
      href={`#${href}`}
      title={collapsed ? label : undefined}
      aria-current={active ? "page" : undefined}
      onClick={(event) => {
        if (!requestNavigation(href)) {
          event.preventDefault();
          return;
        }
        onNavigate();
      }}
      className={cx(
        "group flex h-9 min-w-0 items-center rounded-control text-body transition-colors",
        child
          ? collapsed
            ? "justify-center px-0"
            : "gap-2.5 pl-6 pr-2.5 text-meta"
          : collapsed
            ? "justify-center px-0"
            : "gap-2.5 px-2.5",
        active
          ? "bg-surface-selected font-medium text-primary"
          : "text-secondary hover:bg-surface-hover hover:text-primary",
      )}
    >
      <LinkIcon
        size={child ? 14 : 16}
        className={cx(
          "shrink-0 transition-colors",
          child ? "text-muted group-hover:text-primary" : "text-icon group-hover:text-primary",
        )}
      />
      <span className={cx("min-w-0 flex-1 truncate", collapsed && "md:hidden")}>{label}</span>
      {active && (
        <span className={cx("h-1.5 w-1.5 shrink-0 rounded-full bg-accent", collapsed && "md:hidden")} aria-hidden />
      )}
    </a>
  );
}

export function AppSidebar({
  path,
  collapsed,
  mobileOpen,
  onToggleCollapsed,
  onCloseMobile,
}: {
  path: string;
  collapsed: boolean;
  mobileOpen: boolean;
  onToggleCollapsed: () => void;
  onCloseMobile: () => void;
}) {
  const groups = navigationGroups(navigationModules());
  const [openGroups, setOpenGroups] = useState(initialOpenGroups);
  const activeGroup = groups.find((group) => group.modules.some((module) => moduleIsActive(module, path)))?.id;

  useEffect(() => {
    if (!activeGroup || activeGroup === "pinned") return;
    setOpenGroups((current) => {
      if (current.has(activeGroup)) return current;
      const next = new Set(current).add(activeGroup);
      localStorage.setItem(OPEN_GROUPS_KEY, JSON.stringify([...next]));
      return next;
    });
  }, [activeGroup]);

  function toggleGroup(group: ModuleGroup) {
    setOpenGroups((current) => {
      const next = new Set(current);
      if (next.has(group)) next.delete(group);
      else next.add(group);
      localStorage.setItem(OPEN_GROUPS_KEY, JSON.stringify([...next]));
      return next;
    });
  }

  const pinned = groups.find((group) => group.id === "pinned")?.modules ?? [];
  const sections = groups.filter((group) => group.id !== "pinned");

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Kenar çubuğunu kapat"
          onClick={onCloseMobile}
          className="fixed inset-0 z-popover bg-scrim md:hidden"
        />
      )}
      <aside
        aria-label="Ana navigasyon"
        className={cx(
          "fixed inset-y-0 left-0 z-drawer flex w-sidebar -translate-x-full flex-col border-r border-subtle bg-sidebar transition-[width,transform] duration-300 ease-in-out md:sticky md:top-0 md:h-dvh md:translate-x-0",
          mobileOpen && "translate-x-0",
          collapsed ? "md:w-rail" : "md:w-sidebar",
        )}
      >
        <div
          className={cx(
            "flex h-workspace-header shrink-0 items-center",
            collapsed ? "md:justify-center md:px-2" : "px-3",
          )}
        >
          <a
            href="#/"
            onClick={onCloseMobile}
            aria-label="forkOS Bugün"
            className={cx("flex min-w-0 items-center gap-2.5", collapsed ? "md:justify-center" : "flex-1")}
          >
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-control bg-primary text-heading text-canvas">
              f
            </span>
            <span className={cx("truncate text-heading text-primary", collapsed && "md:hidden")}>forkOS</span>
          </a>
          <button
            type="button"
            onClick={onToggleCollapsed}
            title={collapsed ? "Kenar çubuğunu genişlet" : "Kenar çubuğunu daralt"}
            aria-label={collapsed ? "Kenar çubuğunu genişlet" : "Kenar çubuğunu daralt"}
            className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-control text-muted transition hover:bg-surface-hover hover:text-primary md:flex"
          >
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
        </div>

        <div className={cx("shrink-0 space-y-1 border-y border-subtle py-2", collapsed ? "md:px-2" : "px-2.5")}>
          <button
            type="button"
            onClick={openCommandPalette}
            title={collapsed ? "Ara veya komut" : undefined}
            className={cx(
              "flex h-9 w-full items-center rounded-control text-secondary transition hover:bg-surface-hover hover:text-primary",
              collapsed ? "md:justify-center" : "gap-2.5 px-2.5",
            )}
          >
            <Search size={16} className="shrink-0 text-icon" />
            <span className={cx("min-w-0 flex-1 truncate text-left text-body", collapsed && "md:hidden")}>
              Ara veya komut
            </span>
            <span className={cx("text-meta text-muted", collapsed && "md:hidden")}>⌘K</span>
          </button>
          <button
            type="button"
            onClick={() => openCapture()}
            title={collapsed ? "Yeni kayıt" : undefined}
            className={cx(
              "flex h-9 w-full items-center rounded-control bg-surface text-primary shadow-card transition hover:bg-surface-hover",
              collapsed ? "md:justify-center" : "gap-2.5 px-2.5",
            )}
          >
            <Plus size={16} className="shrink-0" />
            <span className={cx("min-w-0 flex-1 truncate text-left text-body font-medium", collapsed && "md:hidden")}>
              Yeni kayıt
            </span>
          </button>
        </div>

        <nav className={cx("min-h-0 flex-1 overflow-y-auto py-3", collapsed ? "md:px-2" : "px-2.5")}>
          <div className="space-y-1">
            {pinned.map((module) => (
              <SidebarLink
                key={module.id}
                href={moduleTarget(module)}
                label={module.title}
                icon={module.icon}
                active={moduleIsActive(module, path)}
                collapsed={collapsed}
                onNavigate={onCloseMobile}
              />
            ))}
          </div>

          <div className="mt-4 space-y-4">
            {sections.map((group) => {
              const open = openGroups.has(group.id);
              return (
                <section key={group.id} aria-labelledby={`sidebar-${group.id}`}>
                  <div className={cx("mx-2 mb-2 h-px bg-subtle", collapsed ? "hidden md:block" : "hidden")} />
                  <button
                    type="button"
                    id={`sidebar-${group.id}`}
                    onClick={() => toggleGroup(group.id)}
                    aria-expanded={open}
                    className={cx(
                      "mb-1 flex h-7 w-full items-center gap-1 px-2 text-left text-micro font-medium uppercase tracking-[0.16em] text-muted transition hover:text-primary",
                      collapsed && "md:hidden",
                    )}
                  >
                    {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    <span>{group.label}</span>
                  </button>
                  <div className={cx("space-y-1", !open && "hidden", collapsed && "md:block")}>
                    {group.modules.map((module) => {
                      const active = moduleIsActive(module, path);
                      const children = module.routes.filter((route) => route.navigation === "child");
                      const childActive = children.some((route) => Boolean(findRouteMatch([route], path)));
                      const ModuleSidebar = module.sidebar;
                      return (
                        <div key={module.id}>
                          <SidebarLink
                            href={moduleTarget(module)}
                            label={module.title}
                            icon={module.icon}
                            active={active && !childActive}
                            collapsed={collapsed}
                            onNavigate={onCloseMobile}
                          />
                          {open && children.length > 0 && (
                            <div className={cx("mt-0.5 space-y-0.5", collapsed && "md:hidden")}>
                              {children.map((route) => (
                                <SidebarLink
                                  key={route.path}
                                  href={route.path}
                                  label={route.title ?? module.title}
                                  icon={route.icon}
                                  active={Boolean(findRouteMatch([route], path))}
                                  collapsed={collapsed}
                                  child
                                  onNavigate={onCloseMobile}
                                />
                              ))}
                            </div>
                          )}
                          {open && active && ModuleSidebar && (
                            <div className={cx(collapsed && "md:hidden")}>
                              <ModuleSidebar collapsed={collapsed} onNavigate={onCloseMobile} />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </div>
        </nav>

        <div
          className={cx(
            "shrink-0 border-t border-subtle py-2 text-meta text-muted",
            collapsed ? "md:px-2 md:text-center" : "px-4",
          )}
        >
          <span className="block truncate">{collapsed ? "1.0" : "Yerel çalışma alanı"}</span>
        </div>
      </aside>
    </>
  );
}
