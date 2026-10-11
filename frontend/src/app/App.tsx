import "@/modules"; // registry yi doldurur -- ILK import olmali
import { useSourceHealth } from "@/core/runtimeQueries";
import { LegacyVaultLink } from "@/core/LegacyVaultLink";
import { Suspense, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, WifiOff, X } from "lucide-react";
import { CommandPalette } from "@/core/CommandPalette";
import { DialogHost } from "@/core/dialog";
import { DropCapture } from "@/core/DropCapture";
import { CaptureDialog } from "@/core/CaptureDialog";
import { DesktopNotificationBridge } from "@/core/DesktopNotificationBridge";
import { allGlobalSurfaces, allRoutes, hydrateSettings } from "@/core/registry";
import { hydrateEntityRegistry } from "@/core/entityRegistry";
import type { EntityTypeSpec } from "@/core/entityRegistry";
import { api } from "@/core/api";
import { sourceLabel } from "@/core/labels";
import { runStateView } from "@/core/sourceStatus";
import { Kbd, ToastProvider, applyTheme, cx, readTheme } from "@/core/ui";
import { AppSidebar, WorkspaceHeader } from "@/core/shell";
import type { AppSettings, SourceHealth } from "@/core/types";
import type { ModuleSpec } from "@/core/types";
import { useOnline } from "@/lib/hooks";
import { findRouteMatch, navigate, useHashRoute } from "./router";

export function routeForPath(routes: ModuleSpec["routes"], path: string) {
  return findRouteMatch(routes, path);
}

function NotFound() {
  return (
    <div className="p-10">
      <p className=" text-title text-primary">Böyle bir sayfa yok</p>
      <p className="mt-1 text-body text-secondary">
        Adres yanlış olabilir. <Kbd>Ctrl</Kbd> <Kbd>K</Kbd> ile aramayı dene.
      </p>
    </div>
  );
}

function PageLoading() {
  return (
    <div className="px-8 py-10 text-body text-muted" role="status">
      Sayfa yükleniyor…
    </div>
  );
}

/* ── Uyari seritleri ─────────────────────────────────────────────────── */

function Banner({
  tone,
  icon,
  children,
  onDismiss,
}: {
  tone: "warn" | "danger";
  icon: React.ReactNode;
  children: React.ReactNode;
  onDismiss?: () => void;
}) {
  return (
    <div
      role="status"
      className={cx(
        "flex items-center gap-2.5 border-b px-8 py-2 text-meta",
        tone === "warn"
          ? "border-warn-border bg-warn-surface text-warn"
          : "border-danger-border bg-danger-surface text-danger",
      )}
    >
      <span className="shrink-0">{icon}</span>
      <span className="min-w-0 flex-1">{children}</span>
      {onDismiss && (
        <button type="button" onClick={onDismiss} aria-label="Kapat" className="shrink-0 opacity-70 hover:opacity-100">
          <X size={14} />
        </button>
      )}
    </div>
  );
}

/** Kural 6: sessiz olum kabul edilemez -- kirik kaynak her ekranda gorunur. */
function SourceAlert() {
  const [dismissed, setDismissed] = useState(false);
  // Kaynak sagligi kabukta TEK anahtarla tutulur (bkz. core/runtimeQueries):
  // ayri anahtar ayni ucu ikinci kez yoklardi.
  const query = useSourceHealth();
  const sources = query.data ?? [];
  const attention = sources.filter((run) => runStateView(run.status).attention);
  if (dismissed) return null;

  // "Sorun yok" demek icin VERI gerekir: sorgu dustugunde sessiz kalmak
  // saglikli gorunmek olurdu. O yuzden bilinmeyen durum ayrica bildirilir.
  if (query.isError && sources.length === 0) {
    return (
      <Banner tone="warn" icon={<AlertTriangle size={15} />} onDismiss={() => setDismissed(true)}>
        Kaynak durumu alınamadı — bu, sorun olmadığı anlamına gelmez.{" "}
        <a href="#/sources" className="border-b border-warn-border">
          kaynak sağlığına git
        </a>
      </Banner>
    );
  }

  if (attention.length === 0) return null;
  const names = attention
    .slice(0, 3)
    .map((run) => sourceLabel(run.source))
    .join(", ");
  return (
    <Banner tone="warn" icon={<AlertTriangle size={15} />} onDismiss={() => setDismissed(true)}>
      {attention.length} kaynak ilgi istiyor: <strong className="font-medium">{names}</strong>
      {attention.length > 3 && ` +${attention.length - 3}`}
      {" — "}
      <a href="#/sources" className="border-b border-warn-border">
        kaynak sağlığına git
      </a>
    </Banner>
  );
}

/* ── Kabuk ───────────────────────────────────────────────────────────── */

export default function App() {
  const { path, params } = useHashRoute();
  const online = useOnline();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => localStorage.getItem("forkos.sidebar.collapsed") === "1",
  );
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: () => api.get<AppSettings>("/settings") });
  const { data: entityTypes } = useQuery({
    queryKey: ["entity-types"],
    queryFn: () => api.get<EntityTypeSpec[]>("/registry/entity-types"),
    staleTime: 60 * 60_000,
  });

  useEffect(() => {
    applyTheme(readTheme());
    if (settings) hydrateSettings(settings);
    if (entityTypes) hydrateEntityRegistry(entityTypes);
  }, [settings, entityTypes]);

  useEffect(() => {
    setSidebarOpen(false);
  }, [path]);

  function toggleSidebar() {
    setSidebarCollapsed((current) => {
      const next = !current;
      localStorage.setItem("forkos.sidebar.collapsed", next ? "1" : "0");
      return next;
    });
  }

  useEffect(() => {
    const root = path.split("/")[1];
    if ((root === "notes" || root === "knowledge") && params.has("focus")) return;
    if (["media", "finance", "documents", "notes", "knowledge"].includes(root)) {
      navigate(
        root === "documents"
          ? "/opportunities?tab=applications"
          : root === "notes" || root === "knowledge"
            ? "/settings?tab=brain"
            : "/",
        { replace: true },
      );
    }
  }, [path, params]);

  const routes = allRoutes();
  const globalSurfaces = allGlobalSurfaces();
  const route = routeForPath(routes, path);
  const Page = ["/notes", "/knowledge"].includes(path)
    ? LegacyVaultLink
    : (route?.element ?? (path === "/" ? routes[0]?.element : NotFound) ?? NotFound);

  return (
    <ToastProvider>
      <div className="flex min-h-dvh bg-canvas text-primary">
        <AppSidebar
          path={path}
          params={params}
          collapsed={sidebarCollapsed}
          mobileOpen={sidebarOpen}
          onToggleCollapsed={toggleSidebar}
          onCloseMobile={() => setSidebarOpen(false)}
        />

        <div className="flex min-h-dvh min-w-0 flex-1 flex-col bg-canvas">
          <WorkspaceHeader
            path={path}
            onOpenSidebar={() => setSidebarOpen(true)}
            sidebarCollapsed={sidebarCollapsed}
            onToggleCollapsed={toggleSidebar}
          />

          <main id="main-content" className="min-h-0 min-w-0 flex-1">
            {!online && (
              <Banner tone="warn" icon={<WifiOff size={15} />}>
                Çevrimdışısın. Kayıtlı veriler okunabilir, yazma işlemleri kapalı. Tarayıcı eklentisi kaydettiklerini
                kuyruğa alır.
              </Banner>
            )}
            <SourceAlert />
            <Suspense fallback={<PageLoading />}>
              <Page />
            </Suspense>
          </main>
        </div>

        <CommandPalette />
        <DialogHost />
        <DropCapture />
        <CaptureDialog />
        <DesktopNotificationBridge />
        {globalSurfaces.map((Surface, index) => (
          <Surface key={`${Surface.displayName ?? Surface.name ?? "surface"}-${index}`} />
        ))}
      </div>
    </ToastProvider>
  );
}
