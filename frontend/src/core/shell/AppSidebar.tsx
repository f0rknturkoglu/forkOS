import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, LayoutGrid, PanelLeftClose, Search, Star } from "lucide-react";
import { findRouteMatch } from "@/app/router";
import { openCommandPalette } from "@/core/CommandPalette";
import {
  areaForPath,
  areaIsActive,
  areaRows,
  areaShape,
  areasAt,
  moduleLanding,
  rowIsActive,
  type NavigationRow,
  type ProductArea,
  type ProductAreaId,
} from "@/core/navigation";
import { requestNavigation } from "@/core/navigationGuard";
import { enabledModules } from "@/core/registry";
import { usePinnedSavedViews } from "@/core/savedViews";
import type { ModuleSpec } from "@/core/types";
import { cx } from "@/core/ui";

const OPEN_AREAS_KEY = "forkos.sidebar.areas";

/** Varsayılan: alt satırı olan birincil alanlar açık; uzun kuyruk kapalı. */
function initialOpenAreas(modules: readonly ModuleSpec[]): Set<ProductAreaId> {
  try {
    const raw = JSON.parse(localStorage.getItem(OPEN_AREAS_KEY) ?? "null");
    if (Array.isArray(raw)) return new Set(raw as ProductAreaId[]);
  } catch {
    // Bozuk gorunum tercihi navigasyonu kitlemesin; guvenli varsayilana don.
  }
  return new Set(
    areasAt("primary")
      .filter((area) => areaShape(area, modules) === "section")
      .map((area) => area.id),
  );
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

/** Katlanır alan başlığı: etiket hedefe gider, oklu düğme yalnız açar/kapar. */
function AreaHeader({
  area,
  rows,
  open,
  collapsed,
  path,
  params,
  modules,
  onToggle,
  onNavigate,
}: {
  area: ProductArea;
  rows: NavigationRow[];
  open: boolean;
  collapsed: boolean;
  path: string;
  params: URLSearchParams;
  modules: readonly ModuleSpec[];
  onToggle: () => void;
  onNavigate: () => void;
}) {
  const active = areaIsActive(area, path, modules);
  const landing = area.landing;
  const AreaIcon = area.icon ?? LayoutGrid;
  return (
    <div className="flex min-w-0 items-center">
      {landing ? (
        <div className="min-w-0 flex-1">
          <SidebarLink
            href={landing}
            label={area.label}
            icon={area.icon}
            // Urun alani vurgusu: alt rotalardan biri aktifse alan da aktiftir.
            active={active}
            collapsed={collapsed}
            onNavigate={onNavigate}
          />
        </div>
      ) : (
        <button
          type="button"
          onClick={onToggle}
          title={collapsed ? area.label : undefined}
          className={cx(
            "group flex h-9 min-w-0 flex-1 items-center rounded-control text-body transition-colors",
            collapsed ? "justify-center px-0" : "gap-2.5 px-2.5",
            active ? "bg-surface-selected font-medium text-primary" : "text-secondary hover:bg-surface-hover hover:text-primary",
          )}
        >
          <AreaIcon size={16} className="shrink-0 text-icon group-hover:text-primary" />
          <span className={cx("min-w-0 flex-1 truncate text-left", collapsed && "md:hidden")}>{area.label}</span>
        </button>
      )}
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={`sidebar-area-${area.id}`}
        aria-label={`${area.label} alt satırları ${open ? "kapat" : "aç"}`}
        className={cx(
          "flex h-7 w-6 shrink-0 items-center justify-center rounded-control text-muted transition hover:bg-surface-hover hover:text-primary",
          collapsed && "md:hidden",
        )}
      >
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
      </button>
    </div>
  );
}

export function AppSidebar({
  path,
  params,
  collapsed,
  mobileOpen,
  onToggleCollapsed,
  onCloseMobile,
}: {
  path: string;
  params: URLSearchParams;
  collapsed: boolean;
  mobileOpen: boolean;
  onToggleCollapsed: () => void;
  onCloseMobile: () => void;
}) {
  const modules = enabledModules();
  const primary = areasAt("primary");
  const longtail = areasAt("longtail");
  const system = areasAt("system");
  const activeArea = areaForPath(path, modules);
  const [openAreas, setOpenAreas] = useState(() => initialOpenAreas(modules));
  const { data: pinnedViews = [] } = usePinnedSavedViews();

  useEffect(() => {
    // Hangi alan aktifse onu ac: kullanici rotayi dogrudan acsa bile alt
    // satirlar gorunur olur (uzun kuyruk dahil).
    if (!activeArea) return;
    setOpenAreas((current) => {
      if (current.has(activeArea.id)) return current;
      const next = new Set(current).add(activeArea.id);
      localStorage.setItem(OPEN_AREAS_KEY, JSON.stringify([...next]));
      return next;
    });
  }, [activeArea]);

  function toggleArea(area: ProductArea) {
    setOpenAreas((current) => {
      const next = new Set(current);
      if (next.has(area.id)) next.delete(area.id);
      else next.add(area.id);
      localStorage.setItem(OPEN_AREAS_KEY, JSON.stringify([...next]));
      return next;
    });
  }

  function renderRows(area: ProductArea, open: boolean) {
    const rows = areaRows(area, modules);
    return (
      <div id={`sidebar-area-${area.id}`} className={cx("space-y-0.5", !open && "hidden")}>
        {rows
          // Alanın hedefi zaten başlık satırıdır; alt listede TEKRAR etmez.
          .filter((row) => row.path !== area.landing)
          .map((row) => {
            const rowActive = rowIsActive(row, path, params);
            const nested = rowActive && rows.some((other) => other.child && rowIsActive(other, path, params));
            const ModuleSidebar = modules.find((module) => module.id === row.moduleId)?.sidebar;
            return (
              <div key={`${row.moduleId}-${row.path}-${row.query ?? ""}`}>
                <SidebarLink
                  href={row.query ? `${row.path}?${row.query}` : row.path}
                  label={row.label}
                  icon={row.icon}
                  active={rowActive && !nested}
                  collapsed={collapsed}
                  onNavigate={onCloseMobile}
                />
                {rowActive && ModuleSidebar && (
                  <div className={cx(collapsed && "md:hidden")}>
                    <ModuleSidebar collapsed={collapsed} onNavigate={onCloseMobile} />
                  </div>
                )}
              </div>
            );
          })}
      </div>
    );
  }

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
        id="app-sidebar"
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
            aria-label="forkOS Home"
            className={cx("flex min-w-0 items-center gap-2.5", collapsed ? "md:justify-center" : "flex-1")}
          >
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-control bg-primary text-heading text-canvas">
              f
            </span>
            <span className={cx("truncate text-heading text-primary", collapsed && "md:hidden")}>forkOS</span>
          </a>
          {/* Rayda 56px'e logo (28px) ve buton (32px) BIRLIKTE sigmaz; bu
              yuzden daraltilmis halde buton hic render edilmez, genisletme
              WorkspaceHeader'in soluna tasinir. */}
          {!collapsed && (
            <button
              type="button"
              onClick={onToggleCollapsed}
              title="Kenar çubuğunu daralt"
              aria-label="Kenar çubuğunu daralt"
              aria-controls="app-sidebar"
              aria-expanded
              className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-control text-muted transition hover:bg-surface-hover hover:text-primary md:flex"
            >
              <PanelLeftClose size={16} />
            </button>
          )}
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
        </div>

        <nav className={cx("min-h-0 flex-1 overflow-y-auto py-3", collapsed ? "md:px-2" : "px-2.5")}>
          <div className="space-y-1">
            {primary.map((area) => {
              const rows = areaRows(area, modules);
              const shape = areaShape(area, modules);
              if (shape === "link") {
                return (
                  <SidebarLink
                    key={area.id}
                    href={area.landing ?? "/"}
                    label={area.label}
                    icon={area.icon}
                    active={areaIsActive(area, path, modules)}
                    collapsed={collapsed}
                    onNavigate={onCloseMobile}
                  />
                );
              }
              const open = openAreas.has(area.id);
              return (
                <div key={area.id}>
                  <AreaHeader
                    area={area}
                    rows={rows}
                    open={open}
                    collapsed={collapsed}
                    path={path}
                    params={params}
                    modules={modules}
                    onToggle={() => toggleArea(area)}
                    onNavigate={onCloseMobile}
                  />
                  {renderRows(area, open)}
                </div>
              );
            })}
          </div>

          {pinnedViews.length > 0 && (
            <section className="mt-5" aria-labelledby="sidebar-pinned">
              <p
                id="sidebar-pinned"
                className={cx(
                  "mb-1 px-2 text-micro font-medium uppercase tracking-[0.16em] text-muted",
                  collapsed && "md:hidden",
                )}
              >
                Sabitlenenler
              </p>
              <div className="space-y-1">
                {pinnedViews.map((view) => {
                  const target = moduleLanding(modules, view.module);
                  if (!target) {
                    // Hedef modul kapali/silinmis: satir kalir ama tiklanmaz.
                    return (
                      <span
                        key={view.id}
                        title="Hedef modül kapalı"
                        className={cx(
                          "flex h-9 min-w-0 items-center gap-2.5 rounded-control px-2.5 text-body text-muted opacity-60",
                          collapsed && "md:justify-center md:px-0",
                        )}
                      >
                        <Star size={16} className="shrink-0 text-icon" />
                        <span className={cx("min-w-0 flex-1 truncate", collapsed && "md:hidden")}>{view.name}</span>
                      </span>
                    );
                  }
                  return (
                    <SidebarLink
                      key={view.id}
                      href={`${target}?saved=${view.id}`}
                      label={view.name}
                      icon={Star}
                      active={params.get("saved") === view.id}
                      collapsed={collapsed}
                      onNavigate={onCloseMobile}
                    />
                  );
                })}
              </div>
            </section>
          )}

          {longtail.map((area) => {
            const open = openAreas.has(area.id);
            return (
              <div key={area.id} className="mt-5">
                <AreaHeader
                  area={area}
                  rows={areaRows(area, modules)}
                  open={open}
                  collapsed={collapsed}
                  path={path}
                  params={params}
                  modules={modules}
                  onToggle={() => toggleArea(area)}
                  onNavigate={onCloseMobile}
                />
                {renderRows(area, open)}
              </div>
            );
          })}
        </nav>

        <div className={cx("shrink-0 border-t border-subtle py-2", collapsed ? "md:px-2" : "px-2.5")}>
          <div className="space-y-1">
            {system.map((area) =>
              areaRows(area, modules).map((row) => (
                <SidebarLink
                  key={`${area.id}-${row.path}`}
                  href={row.path}
                  label={row.label}
                  icon={row.icon}
                  active={Boolean(findRouteMatch([{ path: row.path }], path))}
                  collapsed={collapsed}
                  onNavigate={onCloseMobile}
                />
              )),
            )}
          </div>
          <p className={cx("mt-1 px-2.5 text-meta text-muted truncate", collapsed && "md:hidden")}>
            Yerel çalışma alanı
          </p>
        </div>
      </aside>
    </>
  );
}
