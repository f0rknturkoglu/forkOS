import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Activity,
  Layers,
  Menu,
  Moon,
  MoreHorizontal,
  PanelLeftOpen,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Sun,
} from "lucide-react";
import { api } from "@/core/api";
import { navigate } from "@/app/router";
import { openCommandPalette } from "@/core/CommandPalette";
import { invalidateAfter } from "@/core/invalidation";
import { NotificationPanel } from "@/core/NotificationPanel";
import { ActiveFocusIndicator } from "@/modules/pomodoro/ActiveFocusIndicator";
import { enabledModules, moduleForPath, titleForPath } from "@/core/registry";
import { areaForPath } from "@/core/navigation";
import { useSourceSync } from "@/core/SyncProgress";
import { StatusLed } from "@/core/StatusLed";
import type { ManualRefreshStatus } from "@/core/types";
import { Button, Chip, IconButton, Kbd, Popover, cx, useTheme, useToast } from "@/core/ui";
import { PageInfoButton } from "@/core/onboarding/PageInfoButton";
import { useOnline } from "@/lib/hooks";

/** Yenileme kapsamlari. Etiketler kullanici dilinde; degerler API sozlesmesi. */
const REFRESH_SCOPES = [
  { id: "critical", label: "Kritik kaynaklar", hint: "YLSY, ÖSYM, YÖK ve hızlı panolar" },
  { id: "standard", label: "Standart yenileme", hint: "Opt-in kaynaklar hariç tüm kaynaklar" },
  { id: "full", label: "Tam yenileme", hint: "Katalogun tamamı; yavaş kaynaklar dahil" },
] as const;

type RefreshScope = (typeof REFRESH_SCOPES)[number]["id"];

const SCOPE_STORAGE_KEY = "forkos:refresh-scope";

function scopeLabel(scope: RefreshScope): string {
  return REFRESH_SCOPES.find((option) => option.id === scope)?.label ?? "Standart yenileme";
}

/** Kapsam menusundeki durum ozeti: son sonuc, son basari ya da hata. */
function refreshSummary(status: ManualRefreshStatus | undefined): string {
  if (!status || status.status === "idle") return "Henüz manuel yenileme çalıştırılmadı.";
  if (status.status === "running") {
    const total = status.results?.opportunity_sources ?? 0;
    const estimate = status.results?.opportunity_estimated_seconds ?? 0;
    return `${scopeLabel(status.scope as RefreshScope)} sürüyor · ${total} kaynak · ~${Math.round(estimate / 60)} dk`;
  }
  if (status.status === "interrupted") {
    return "Önceki yenileme yarıda kesildi; yeniden başlatılabilir.";
  }
  const done = status.finished_at ? new Date(status.finished_at).toLocaleString("tr-TR") : "bilinmiyor";
  if (status.status === "completed_with_errors") {
    return `Son yenileme ${done} tarihinde bitti · ${status.errors?.length ?? 0} bölüm hata verdi`;
  }
  return `Son yenileme ${done} tarihinde tamamlandı`;
}

function storedScope(): RefreshScope {
  if (typeof window === "undefined") return "standard";
  const saved = window.localStorage.getItem(SCOPE_STORAGE_KEY);
  return REFRESH_SCOPES.some((scope) => scope.id === saved) ? (saved as RefreshScope) : "standard";
}

export function WorkspaceHeader({
  path,
  onOpenSidebar,
  sidebarCollapsed = false,
  onToggleCollapsed,
}: {
  path: string;
  onOpenSidebar: () => void;
  /** Daraltilmis kenar cubugu: genisletme dugmesi burada, ray basligini kilitler. */
  sidebarCollapsed?: boolean;
  onToggleCollapsed?: () => void;
}) {
  const [theme, setTheme] = useTheme();
  const online = useOnline();
  const toast = useToast();
  const startedHere = useRef(false);
  const [scope, setScope] = useState<RefreshScope>(storedScope);
  const [overflowOpen, setOverflowOpen] = useState(false);
  const overflowAnchor = useRef<HTMLSpanElement>(null);
  const modules = enabledModules();
  const area = areaForPath(path, modules);
  const module = moduleForPath(path);
  const title = titleForPath(path) ?? "forkOS";
  const Icon = module?.icon;
  const refreshStatus = useQuery({
    queryKey: ["system-refresh"],
    queryFn: () => api.get<ManualRefreshStatus>("/system/refresh"),
    refetchInterval: (query) => (query.state.data?.status === "running" ? 2_000 : false),
  });
  const sourceSync = useSourceSync();
  const refresh = useMutation({
    mutationFn: (next: RefreshScope) => api.post<ManualRefreshStatus>("/system/refresh", { scope: next }),
    onSuccess: (value, next) => {
      startedHere.current = value.status === "running";
      void refreshStatus.refetch();
      toast.push(
        value.started ? `${scopeLabel(next)} başlatıldı.` : "Zaten çalışan bir yenileme var; ilerleme üstteki şeritte.",
      );
    },
    // Hata sonrasi buton MUTLAKA yeniden kullanilabilir olmali: isPending burada
    // false'a doner ve durum sorgusu da yeni bir calisma baslatmaz.
    onError: (error) => toast.push(`Yenileme başlatılamadı: ${error.message}`, { tone: "danger" }),
  });

  const start = (next: RefreshScope) => {
    setScope(next);
    if (typeof window !== "undefined") window.localStorage.setItem(SCOPE_STORAGE_KEY, next);
    setOverflowOpen(false);
    refresh.mutate(next);
  };

  const activeSourceBatch = sourceSync.data?.active;
  const isRefreshing = refresh.isPending || refreshStatus.data?.status === "running" || Boolean(activeSourceBatch);
  const summary = useMemo(() => refreshSummary(refreshStatus.data), [refreshStatus.data]);

  useEffect(() => {
    const value = refreshStatus.data;
    if (!startedHere.current || !value || value.status === "running" || value.status === "idle") return;
    startedHere.current = false;
    invalidateAfter("source.sync");
    const total = ["sources", "rss", "calendar", "github", "deadlines"].reduce(
      (sum, key) => sum + (value.results?.[key] ?? 0),
      0,
    );
    toast.push(
      value.status === "completed_with_errors"
        ? `Yenileme tamamlandı; ${value.errors?.length ?? 0} bölüm hata verdi.`
        : `Yenileme tamamlandı; ${total} değişiklik işlendi.`,
      { tone: value.status === "completed_with_errors" ? "warn" : "ok" },
    );
  }, [refreshStatus.data, toast]);

  return (
    <header className="sticky top-0 z-header flex h-workspace-header shrink-0 items-center gap-3 border-b border-subtle bg-canvas/95 px-3 backdrop-blur sm:px-4">
      <button
        type="button"
        onClick={onOpenSidebar}
        title="Kenar çubuğunu aç"
        aria-label="Kenar çubuğunu aç"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-muted transition hover:bg-surface-hover hover:text-primary md:hidden"
      >
        <Menu size={17} />
      </button>

      {sidebarCollapsed && (
        <button
          type="button"
          onClick={onToggleCollapsed}
          title="Kenar çubuğunu genişlet"
          aria-label="Kenar çubuğunu genişlet"
          aria-controls="app-sidebar"
          className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-control text-muted transition hover:bg-surface-hover hover:text-primary md:flex"
        >
          <PanelLeftOpen size={17} />
        </button>
      )}

      {/* Sol: Bağlamsal Sayfa Kimliği (Page Identity & Context) */}
      <div className="flex min-w-0 flex-1 items-center gap-2">
        {Icon && <Icon size={16} className="shrink-0 text-icon" />}
        {area && area.label && area.label !== title ? (
          <div className="flex min-w-0 items-center gap-1.5">
            <span className="shrink-0 text-meta text-secondary">{area.label}</span>
            <span className="shrink-0 text-meta text-muted">/</span>
            <span className="truncate text-heading text-primary">{title}</span>
          </div>
        ) : (
          <span className="truncate text-heading text-primary">{title}</span>
        )}
        {module && title !== module.title && (!area || area.label !== module.title) && (
          <span className="hidden truncate text-meta text-muted sm:inline">{module.title}</span>
        )}
        <PageInfoButton />
      </div>

      {/* Sağ: Sıkı Eylem Bütçesi (Action Budget) */}
      <div className="flex shrink-0 items-center gap-1.5">
        <StatusLed hideWhenHealthy />

        {/* 1. Arama / Komut Tetikleyicisi */}
        <button
          type="button"
          onClick={openCommandPalette}
          className="hidden h-8 w-48 items-center gap-2 rounded-control border border-subtle bg-surface px-2.5 text-left text-meta text-muted transition hover:bg-surface-hover hover:text-primary lg:flex"
        >
          <Search size={14} />
          <span className="flex-1 truncate">Ara veya komut…</span>
          <Kbd>Ctrl K</Kbd>
        </button>
        <button
          type="button"
          onClick={openCommandPalette}
          title="Ara"
          aria-label="Ara"
          className="flex h-8 w-8 items-center justify-center rounded-control text-muted transition hover:bg-surface-hover hover:text-primary lg:hidden"
        >
          <Search size={15} />
        </button>

        {/* 2. Aktif Odak Göstergesi (yalnızca oturum varsa çizilir) */}
        <ActiveFocusIndicator />

        {/* 3. Birincil Eylem: Kaynakları Yenile */}
        <span className="relative inline-flex">
          <IconButton
            title={
              activeSourceBatch
                ? `Kaynaklar çekiliyor: ${activeSourceBatch.items_found} yeni kayıt`
                : isRefreshing
                  ? "Kaynaklar yenileniyor"
                  : `Kaynakları yenile (${scopeLabel(scope)})`
            }
            disabled={!online || isRefreshing}
            onClick={() => start(scope)}
          >
            <RefreshCw size={15} className={cx((isRefreshing || activeSourceBatch) && "animate-spin")} />
          </IconButton>
          {activeSourceBatch && (
            <Chip
              size="xs"
              tone={activeSourceBatch.error_sources > 0 ? "danger" : "ok"}
              className="pointer-events-none absolute -right-2 -top-2 z-10 px-1 tabular-nums"
              aria-label={`${activeSourceBatch.items_found} yeni kayıt`}
            >
              +{activeSourceBatch.items_found}
            </Chip>
          )}
        </span>

        {/* 4. Bildirim Paneli */}
        <NotificationPanel />

        {/* 5. Taşma Menüsü (Overflow): Tema, Kapsam ve Seyrek Araçlar */}
        <span className="relative inline-flex" ref={overflowAnchor}>
          <IconButton
            title="Yenileme kapsamı ve durumu"
            ariaExpanded={overflowOpen}
            onClick={() => setOverflowOpen((open) => !open)}
          >
            <MoreHorizontal size={16} />
          </IconButton>
          <Popover
            open={overflowOpen}
            onClose={() => setOverflowOpen(false)}
            anchorRef={overflowAnchor}
            role="dialog"
            ariaLabel="Diğer araçlar ve ayarlar"
            className="right-0 top-[calc(100%+0.375rem)] w-[min(22rem,calc(100vw-1.5rem))] p-3"
          >
            <div className="stack-y-3">
              {/* Görünüm / Tema */}
              <div className="flex items-center justify-between gap-2 border-b border-subtle pb-2.5">
                <span className="text-body text-secondary">Görünüm</span>
                <button
                  type="button"
                  onClick={() => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark")}
                  title="Temayı değiştir"
                  aria-label="Temayı değiştir"
                  className="flex h-7 items-center gap-1.5 rounded-control border border-subtle bg-surface-sunken px-2.5 text-meta text-primary transition hover:bg-surface-hover"
                >
                  {document.documentElement.dataset.theme === "dark" ? (
                    <>
                      <Sun size={13} className="text-icon" />
                      <span>Açık tema</span>
                    </>
                  ) : (
                    <>
                      <Moon size={13} className="text-icon" />
                      <span>Koyu tema</span>
                    </>
                  )}
                </button>
              </div>

              {/* Yenileme Kapsamı */}
              <header className="stack-y-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-heading text-primary">Yenileme kapsamı</h3>
                  {isRefreshing && <Chip tone="accent">çalışıyor</Chip>}
                </div>
                <p className="text-micro text-muted">
                  Çalışan yenileme:{" "}
                  <span className="text-secondary">
                    {refreshStatus.data?.batch_id ? refreshStatus.data.batch_id.slice(0, 8) : "yok"}
                  </span>
                </p>
              </header>

              <ul className="stack-y-1">
                {REFRESH_SCOPES.map((option) => (
                  <li key={option.id}>
                    <button
                      type="button"
                      disabled={!online || isRefreshing}
                      onClick={() => start(option.id)}
                      className={cx(
                        "w-full rounded-control px-2 py-1.5 text-left transition",
                        "text-body text-primary hover:bg-surface-hover disabled:opacity-50 disabled:hover:bg-transparent",
                        scope === option.id && "bg-surface-sunken",
                      )}
                    >
                      <span className="flex items-center gap-2">
                        {option.label}
                        {scope === option.id && <span className="text-micro text-accent">seçili</span>}
                      </span>
                      <span className="block text-micro text-muted">{option.hint}</span>
                    </button>
                  </li>
                ))}
              </ul>

              <div className="stack-y-1 border-t border-subtle pt-2 text-micro text-muted">
                <p>{summary}</p>
                {!online && <p className="text-warn">Çevrimdışısın: yenileme başlatılamaz.</p>}
              </div>

              {activeSourceBatch && (
                <div className="stack-y-2 border-t border-subtle pt-2" aria-live="polite">
                  <div className="flex flex-wrap items-center gap-2 text-meta">
                    <span className="font-medium text-primary">Kaynak çekimi</span>
                    <Chip tone="accent">%{activeSourceBatch.progress_pct}</Chip>
                    <Chip tone="ok" className="tabular-nums">
                      +{activeSourceBatch.items_found} yeni kayıt
                    </Chip>
                  </div>
                  <p className="text-micro text-muted">
                    {activeSourceBatch.completed_sources}/{activeSourceBatch.total_sources} kaynak tamamlandı
                    {activeSourceBatch.error_sources > 0 ? ` · ${activeSourceBatch.error_sources} hata` : ""}
                  </p>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setOverflowOpen(false);
                      navigate("/sources");
                    }}
                  >
                    Tüm kaynak sürecini aç
                  </Button>
                </div>
              )}

              {/* Hızlı Araçlar */}
              <div className="stack-y-1 border-t border-subtle pt-2">
                <p className="px-1 text-micro font-medium uppercase tracking-[0.16em] text-muted">Hızlı Araçlar</p>
                <button
                  type="button"
                  onClick={() => {
                    setOverflowOpen(false);
                    navigate("/health");
                  }}
                  className="flex h-8 w-full items-center gap-2 rounded-control px-2 text-left text-meta text-secondary transition hover:bg-surface-hover hover:text-primary"
                >
                  <Activity size={14} className="shrink-0 text-icon" />
                  <span>Sistem durumu paneli</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setOverflowOpen(false);
                    navigate("/sources");
                  }}
                  className="flex h-8 w-full items-center gap-2 rounded-control px-2 text-left text-meta text-secondary transition hover:bg-surface-hover hover:text-primary"
                >
                  <Layers size={14} className="shrink-0 text-icon" />
                  <span>Kaynak sağlığı ve akışlar</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setOverflowOpen(false);
                    navigate("/settings");
                  }}
                  className="flex h-8 w-full items-center gap-2 rounded-control px-2 text-left text-meta text-secondary transition hover:bg-surface-hover hover:text-primary"
                >
                  <SlidersHorizontal size={14} className="shrink-0 text-icon" />
                  <span>Ayarlar</span>
                </button>
              </div>
            </div>
          </Popover>
        </span>
      </div>
    </header>
  );
}
