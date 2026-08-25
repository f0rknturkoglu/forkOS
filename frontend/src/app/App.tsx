import "@/modules"; // registry yi doldurur -- ILK import olmali
import { Suspense, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, WifiOff, X } from "lucide-react";
import { AppHeader } from "@/core/AppHeader";
import { CommandPalette } from "@/core/CommandPalette";
import { DialogHost } from "@/core/dialog";
import { DropCapture } from "@/core/DropCapture";
import { allRoutes, hydrateSettings } from "@/core/registry";
import { hydrateEntityRegistry } from "@/core/entityRegistry";
import type { EntityTypeSpec } from "@/core/entityRegistry";
import { api } from "@/core/api";
import { Kbd, ToastProvider, applyTheme, cx, readTheme } from "@/core/ui";
import type { AppSettings, SourceHealth } from "@/core/types";
import type { ModuleSpec } from "@/core/types";
import { useOnline } from "@/lib/hooks";
import { findRouteMatch, useHashRoute } from "./router";

export function routeForPath(routes: ModuleSpec["routes"], path: string) {
  return findRouteMatch(routes, path);
}

function NotFound() {
  return (
    <div className="p-10">
      <p className="font-serif text-title text-primary">Böyle bir sayfa yok</p>
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
  const { data = [] } = useQuery({
    queryKey: ["sources", "health"],
    queryFn: () => api.get<SourceHealth[]>("/sources/health"),
    refetchInterval: 5 * 60_000,
  });
  const broken = data.filter((s) => s.status === "error");
  if (broken.length === 0 || dismissed) return null;
  const names = broken
    .slice(0, 3)
    .map((s) => s.source)
    .join(", ");
  return (
    <Banner tone="warn" icon={<AlertTriangle size={15} />} onDismiss={() => setDismissed(true)}>
      {broken.length} kaynak hata veriyor: <strong className="font-medium">{names}</strong>
      {broken.length > 3 && ` +${broken.length - 3}`}
      {" — "}
      <a href="#/sources" className="border-b border-warn-border">
        kaynak sağlığına git
      </a>
    </Banner>
  );
}

/* ── Kabuk ───────────────────────────────────────────────────────────── */

export default function App() {
  const { path } = useHashRoute();
  const online = useOnline();
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: () => api.get<AppSettings>("/settings") });
  if (settings) hydrateSettings(settings);
  const { data: entityTypes } = useQuery({
    queryKey: ["entity-types"],
    queryFn: () => api.get<EntityTypeSpec[]>("/registry/entity-types"),
    staleTime: 60 * 60_000,
  });
  if (entityTypes) hydrateEntityRegistry(entityTypes);

  useEffect(() => {
    applyTheme(readTheme());
  }, []);

  const routes = allRoutes();
  const route = routeForPath(routes, path);
  const Page = route?.element ?? (path === "/" ? routes[0]?.element : NotFound) ?? NotFound;

  return (
    <ToastProvider>
      <div className="flex min-h-dvh flex-col bg-canvas text-primary">
        <AppHeader path={path} />

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

        <CommandPalette />
        <DialogHost />
        <DropCapture />
      </div>
    </ToastProvider>
  );
}
