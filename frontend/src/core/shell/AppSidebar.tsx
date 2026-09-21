import { useEffect, useState } from "react";
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
 * Katlanır alan başlığı (Plan, Öğrenme, Kütüphane).
 *
 * Satırın TAMAMI açar/kapar ve AYRICA gezinmez: "etikete basınca mı, oka
 * basınca mı" belirsizliği böylece ortadan kalkar. Ok yalnız durumu söyler.
 * Geometri tek parça: h-9 satır, içinde ayrı bir tıklama dikdörtgeni YOK.
 */
function AreaHeader({
  area,
  open,
  collapsed,
  path,
  modules,
  onToggle,
}: {
  area: ProductArea;
  open: boolean;
  collapsed: boolean;
  path: string;
  modules: readonly ModuleSpec[];
  onToggle: () => void;
}) {
  const active = areaIsActive(area, path, modules);
  const AreaIcon = area.icon ?? LayoutGrid;
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={open}
      aria-controls={`sidebar-area-${area.id}`}
      title={collapsed ? area.label : undefined}
      className={cx(
        "group flex h-9 w-full min-w-0 items-center rounded-control text-body transition-colors",
        collapsed ? "md:justify-center md:px-0" : "gap-2.5 px-2.5",
        active
          ? "bg-surface-selected font-medium text-primary"
          : "text-secondary hover:bg-surface-hover hover:text-primary",
      )}
    >
      <AreaIcon size={16} className="shrink-0 text-icon group-hover:text-primary" />
      <span className={cx("min-w-0 flex-1 truncate text-left", collapsed && "md:hidden")}>{area.label}</span>
      <ChevronDown
        size={15}
        aria-hidden
        className={cx("shrink-0 text-muted transition-transform", collapsed && "md:hidden", open && "rotate-180")}
      />
    </button>
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
  const { data: pinnedViews = [] } = usePinnedSavedViews();
  // Yalnız alt satırı olan alanlar katlanır; tek hedefli alanlar zaten düz satır.
  const collapsibleAreas = primary.filter((area) => areaShape(area, modules) === "section");
  const allExpanded = collapsibleAreas.length > 0 && collapsibleAreas.every((area) => openAreas.has(area.id));

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

        <nav className={cx("min-h-0 flex-1 overflow-y-auto py-3", collapsed ? "md:px-2" : "px-2.5")}>
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
              return (
                <div key={area.id}>
                  <AreaHeader
                    area={area}
                    open={open}
                    collapsed={collapsed}
                    path={path}
                    modules={modules}
                    onToggle={() => toggleArea(area)}
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
