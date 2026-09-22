import { useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  ChevronsDownUp,
  ChevronsUpDown,
  LayoutGrid,
  PanelLeftClose,
  Star,
} from "lucide-react";
import { findRouteMatch } from "@/app/router";
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

/**
 * Temiz kurulumda SADECE kök alanlar görünür: alt satırlar kapalı başlar
 * (sakin varsayılan). Aktif rota kendi alanını yine otomatik açar, kullanıcının
 * aç/kapa tercihi `forkos.sidebar.areas` altında saklanır.
 */
function initialOpenAreas(): Set<ProductAreaId> {
  try {
    const raw = JSON.parse(localStorage.getItem(OPEN_AREAS_KEY) ?? "null");
    if (Array.isArray(raw)) return new Set(raw as ProductAreaId[]);
  } catch {
    // Bozuk gorunum tercihi navigasyonu kitlemesin; guvenli varsayilana don.
  }
  return new Set<ProductAreaId>();
}

/**
 * Navigasyon satiri. Kök alan satırı tam ağırlıkta; alt satırlar hafif küçük
 * ve girintili (ağaç okunur olsun diye ağırlık farkı, okunamayacak kadar
 * küçültme DEĞİL).
 */
function SidebarLink({
  href,
  label,
  active,
  icon: Icon,
  collapsed,
  depth = 0,
  onNavigate,
}: {
  href: string;
  label: string;
  active: boolean;
  icon?: ModuleSpec["icon"];
  collapsed: boolean;
  /** 0 = kök alan satırı, 1 = alan hedefi, 2 = hedefin alt rotası. */
  depth?: 0 | 1 | 2;
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
        "group flex min-w-0 items-center rounded-control transition-colors",
        collapsed
          ? "h-9 justify-center px-0"
          : depth === 0
            ? "h-9 gap-2.5 px-2.5 text-body"
            : depth === 1
              ? "h-8 gap-2.5 pl-6 pr-2.5 text-meta"
              : "h-7 gap-2 pl-10 pr-2.5 text-meta",
        active
          ? "bg-surface-selected font-medium text-primary"
          : depth === 0
            ? "text-secondary hover:bg-surface-hover hover:text-primary"
            : "text-muted hover:bg-surface-hover hover:text-primary",
      )}
    >
      <LinkIcon
        size={depth === 0 ? 16 : depth === 1 ? 14 : 13}
        className={cx(
          "shrink-0 transition-colors",
          depth === 0 ? "text-icon group-hover:text-primary" : "text-muted group-hover:text-primary",
        )}
      />
      <span className={cx("min-w-0 flex-1 truncate", collapsed && "md:hidden")}>{label}</span>
    </a>
  );
}

/**
 * U2 Collapsed Area Flyout.
 * Daraltılmış ray modunda (56px) alt rotaların kaybolmasını engeller.
 * Hem tıklama (click) hem klavye (Enter / Space / ArrowRight / Tab) ile erişilebilir.
 */
function CollapsedAreaFlyout({
  area,
  modules,
  path,
  params,
  onNavigate,
  onClose,
  triggerRef,
}: {
  area: ProductArea;
  modules: readonly ModuleSpec[];
  path: string;
  params: URLSearchParams;
  onNavigate: () => void;
  onClose: () => void;
  triggerRef: React.RefObject<HTMLButtonElement | null>;
}) {
  const rows = areaRows(area, modules);
  const firstLinkRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    firstLinkRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" || event.key === "ArrowLeft") {
        event.preventDefault();
        event.stopPropagation();
        onClose();
        triggerRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, triggerRef]);

  return (
    <div
      role="menu"
      id={`sidebar-area-flyout-${area.id}`}
      aria-label={`${area.label} menüsü`}
      className="absolute left-[calc(100%+0.375rem)] top-0 z-popover min-w-[13.5rem] rounded-control border border-subtle bg-surface p-1.5 shadow-overlay"
    >
      <div className="mb-1 border-b border-subtle px-2 py-1">
        <p className="text-micro font-medium uppercase tracking-[0.16em] text-muted">{area.label}</p>
      </div>
      <div className="space-y-0.5">
        {rows.map((row, index) => {
          const rowActive = rowIsActive(row, path, params);
          const RowIcon = row.icon ?? LayoutGrid;
          const href = row.query ? `${row.path}?${row.query}` : row.path;
          return (
            <a
              key={`${row.moduleId}-${row.path}-${row.query ?? ""}`}
              ref={index === 0 ? firstLinkRef : undefined}
              role="menuitem"
              href={`#${href}`}
              aria-current={rowActive ? "page" : undefined}
              onClick={(event) => {
                if (!requestNavigation(href)) {
                  event.preventDefault();
                  return;
                }
                onClose();
                onNavigate();
              }}
              className={cx(
                "flex h-8 w-full items-center gap-2 rounded-control px-2 text-meta transition-colors",
                rowActive
                  ? "bg-surface-selected font-medium text-primary"
                  : "text-secondary hover:bg-surface-hover hover:text-primary",
              )}
            >
              <RowIcon size={14} className={cx("shrink-0", rowActive ? "text-primary" : "text-muted")} />
              <span className="truncate">{row.label}</span>
            </a>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Katlanır alan başlığı (Plan, Öğrenme, Kütüphane).
 *
 * Alan adı landing'e gider; ayrı ok alt hedefleri açar. Dar rayda flyout kalır.
 */
function AreaHeader({
  area,
  open,
  collapsed,
  path,
  modules,
  onToggle,
  onNavigate,
  flyoutOpen = false,
  onToggleFlyout,
  buttonRef,
}: {
  area: ProductArea;
  open: boolean;
  collapsed: boolean;
  path: string;
  modules: readonly ModuleSpec[];
  onToggle: () => void;
  onNavigate: () => void;
  flyoutOpen?: boolean;
  onToggleFlyout?: () => void;
  buttonRef?: (el: HTMLButtonElement | null) => void;
}) {
  const active = areaIsActive(area, path, modules);
  const AreaIcon = area.icon ?? LayoutGrid;
  return (
    <div
      onKeyDown={(event) => {
        if (collapsed && (event.key === "ArrowRight" || event.key === "Enter" || event.key === " ")) {
          event.preventDefault();
          onToggleFlyout?.();
        }
      }}
      className={cx(
        "group flex h-9 w-full min-w-0 items-center rounded-control text-body transition-colors",
        collapsed ? "md:justify-center md:px-0" : "gap-2.5 px-2.5",
        active
          ? "bg-surface-selected font-medium text-primary"
          : "text-secondary hover:bg-surface-hover hover:text-primary",
      )}
    >
      <a
        href={`#${area.landing ?? areaRows(area, modules)[0]?.path ?? "/"}`}
        aria-current={active && path === area.landing ? "page" : undefined}
        onClick={(event) => {
          if (!requestNavigation(area.landing ?? "/")) event.preventDefault();
          else onNavigate();
        }}
        className={cx("flex min-w-0 flex-1 items-center gap-2.5", collapsed && "md:hidden")}
        title={collapsed ? area.label : undefined}
      >
        <AreaIcon size={16} className="shrink-0 text-icon group-hover:text-primary" />
        <span className={cx("min-w-0 flex-1 truncate text-left", collapsed && "md:hidden")}>{area.label}</span>
      </a>
      <button
        ref={buttonRef}
        type="button"
        onClick={collapsed ? onToggleFlyout : onToggle}
        aria-label={collapsed ? area.label : `${area.label} alt menüsünü ${open ? "daralt" : "genişlet"}`}
        aria-expanded={collapsed ? flyoutOpen : open}
        aria-haspopup={collapsed ? "menu" : undefined}
        aria-controls={
          collapsed ? (flyoutOpen ? `sidebar-area-flyout-${area.id}` : undefined) : `sidebar-area-${area.id}`
        }
        className={cx(
          "flex h-8 w-7 shrink-0 items-center justify-center rounded-control hover:bg-surface-hover",
          collapsed && "md:w-full",
        )}
      >
        {collapsed && <AreaIcon size={16} aria-hidden className="hidden text-icon md:block" />}
        <ChevronDown
          size={15}
          aria-hidden
          className={cx("text-muted transition-transform", collapsed && "md:hidden", open && "rotate-180")}
        />
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
  const system = areasAt("system");
  const activeArea = areaForPath(path, modules);
  const [openAreas, setOpenAreas] = useState(initialOpenAreas);
  const [flyoutArea, setFlyoutArea] = useState<ProductAreaId | null>(null);
  const flyoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const triggerRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const { data: pinnedViews = [] } = usePinnedSavedViews();
  // Yalnız alt satırı olan alanlar katlanır; tek hedefli alanlar zaten düz satır.
  const collapsibleAreas = primary.filter((area) => areaShape(area, modules) === "section");
  const allExpanded = collapsibleAreas.length > 0 && collapsibleAreas.every((area) => openAreas.has(area.id));

  const clearFlyoutTimer = () => {
    if (flyoutTimerRef.current) {
      clearTimeout(flyoutTimerRef.current);
      flyoutTimerRef.current = null;
    }
  };

  const scheduleCloseFlyout = () => {
    clearFlyoutTimer();
    flyoutTimerRef.current = setTimeout(() => {
      setFlyoutArea(null);
    }, 180);
  };

  useEffect(() => {
    if (!flyoutArea) return;
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as HTMLElement | null;
      if (!target?.closest(`[data-area-flyout="${flyoutArea}"]`)) {
        setFlyoutArea(null);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      clearFlyoutTimer();
    };
  }, [flyoutArea]);

  useEffect(() => {
    if (!collapsed) setFlyoutArea(null);
  }, [collapsed]);

  useEffect(() => {
    // Hangi alan aktifse onu ac: kullanici rotayi dogrudan acsa bile alt
    // satirlar gorunur olur.
    if (!activeArea) return;
    setOpenAreas((current) => {
      if (current.has(activeArea.id)) return current;
      const next = new Set(current).add(activeArea.id);
      localStorage.setItem(OPEN_AREAS_KEY, JSON.stringify([...next]));
      return next;
    });
  }, [activeArea]);

  function storeOpenAreas(next: Set<ProductAreaId>) {
    localStorage.setItem(OPEN_AREAS_KEY, JSON.stringify([...next]));
    return next;
  }

  function toggleArea(area: ProductArea) {
    setOpenAreas((current) => {
      const next = new Set(current);
      if (next.has(area.id)) next.delete(area.id);
      else next.add(area.id);
      return storeOpenAreas(next);
    });
  }

  /** Tek kompakt kontrol: hepsi açıksa kapat, değilse hepsini aç. */
  function toggleAllAreas() {
    setOpenAreas(() =>
      allExpanded
        ? storeOpenAreas(new Set<ProductAreaId>())
        : storeOpenAreas(new Set(collapsibleAreas.map((area) => area.id))),
    );
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
            const nested = rowActive && rows.some((other) => other.depth === 2 && rowIsActive(other, path, params));
            const ModuleSidebar = modules.find((module) => module.id === row.moduleId)?.sidebar;
            return (
              <div key={`${row.moduleId}-${row.path}-${row.query ?? ""}`}>
                <SidebarLink
                  href={row.query ? `${row.path}?${row.query}` : row.path}
                  label={row.label}
                  icon={row.icon}
                  active={rowActive && !nested}
                  collapsed={collapsed}
                  depth={row.depth}
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
          "fixed inset-y-0 left-0 z-drawer flex w-sidebar -translate-x-full flex-col border-r border-subtle bg-sidebar transition-[width,transform] duration-150 ease-out motion-reduce:transition-none md:sticky md:top-0 md:h-dvh md:transform-none",
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

        {/* Komut aramasi TEK yerde: WorkspaceHeader. Sidebar kopyasi kaldirildi;
            yerine alt satirlari topluca acan/kapatan kompakt kontrol durur. */}
        <div className={cx("shrink-0 border-b border-subtle py-1.5", collapsed ? "md:px-2" : "px-2.5")}>
          <button
            type="button"
            onClick={toggleAllAreas}
            title={allExpanded ? "Tümünü daralt" : "Tümünü genişlet"}
            className={cx(
              "flex h-8 w-full items-center rounded-control text-meta text-muted transition hover:bg-surface-hover hover:text-primary",
              collapsed ? "md:justify-center md:px-0" : "gap-2 px-2.5",
            )}
          >
            {allExpanded ? (
              <ChevronsDownUp size={15} className="shrink-0 text-icon" aria-hidden />
            ) : (
              <ChevronsUpDown size={15} className="shrink-0 text-icon" aria-hidden />
            )}
            <span className={cx("min-w-0 flex-1 truncate text-left", collapsed && "md:hidden")}>
              {allExpanded ? "Tümünü daralt" : "Tümünü genişlet"}
            </span>
          </button>
        </div>

        <nav
          className={cx("min-h-0 flex-1 py-3", collapsed ? "md:overflow-visible md:px-2" : "overflow-y-auto px-2.5")}
        >
          <div className="space-y-1">
            {primary.map((area) => {
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
              const isFlyoutOpen = collapsed && flyoutArea === area.id;
              return (
                <div
                  key={area.id}
                  className="relative"
                  data-area-flyout={area.id}
                  onMouseEnter={() => {
                    if (collapsed) {
                      clearFlyoutTimer();
                      setFlyoutArea(area.id);
                    }
                  }}
                  onMouseLeave={() => {
                    if (collapsed) {
                      scheduleCloseFlyout();
                    }
                  }}
                >
                  <AreaHeader
                    area={area}
                    open={open}
                    collapsed={collapsed}
                    flyoutOpen={isFlyoutOpen}
                    path={path}
                    modules={modules}
                    onToggle={() => toggleArea(area)}
                    onNavigate={onCloseMobile}
                    onToggleFlyout={() => {
                      clearFlyoutTimer();
                      setFlyoutArea((curr) => (curr === area.id ? null : area.id));
                    }}
                    buttonRef={(el) => {
                      triggerRefs.current[area.id] = el;
                    }}
                  />
                  {isFlyoutOpen ? (
                    <div onMouseEnter={clearFlyoutTimer} onMouseLeave={scheduleCloseFlyout}>
                      <CollapsedAreaFlyout
                        area={area}
                        modules={modules}
                        path={path}
                        params={params}
                        onNavigate={() => {
                          setFlyoutArea(null);
                          onCloseMobile();
                        }}
                        onClose={() => setFlyoutArea(null)}
                        triggerRef={{
                          get current() {
                            return triggerRefs.current[area.id] ?? null;
                          },
                        }}
                      />
                    </div>
                  ) : null}
                  {!collapsed && renderRows(area, open)}
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
