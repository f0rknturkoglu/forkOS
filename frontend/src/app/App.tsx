import "@/modules";                 // registry'yi doldurur -- ILK import olmali
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ExternalLink, Moon, Search, Sun, WifiOff, X } from "lucide-react";
import { CommandPalette } from "@/core/CommandPalette";
import { DialogHost } from "@/core/dialog";
import {
  allRoutes, groupedModules, hydrateSettings, moduleForPath, pinnedModules,
} from "@/core/registry";
import { api } from "@/core/api";
import { Kbd, ToastProvider, applyTheme, cx, readTheme, useTheme } from "@/core/ui";
import type { Theme } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { AppSettings, ModuleSpec, SourceHealth } from "@/core/types";
import { openCommandPalette } from "@/core/CommandPalette";
import { useHashRoute } from "./router";

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

/* ── Uyari seritleri ─────────────────────────────────────────────────── */

function Banner({
  tone, icon, children, onDismiss,
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
  const names = broken.slice(0, 3).map((s) => s.source).join(", ");
  return (
    <Banner tone="warn" icon={<AlertTriangle size={15} />} onDismiss={() => setDismissed(true)}>
      {broken.length} kaynak hata veriyor: <strong className="font-medium">{names}</strong>
      {broken.length > 3 && ` +${broken.length - 3}`}
      {" — "}
      <a href="#/sources" className="border-b border-warn-border">kaynak sağlığına git</a>
    </Banner>
  );
}

/* ── Sol menu ────────────────────────────────────────────────────────── */

function NavItem({ module, path }: { module: ModuleSpec; path: string }) {
  const target = module.routes[0]?.path ?? "/";
  const active = module.routes.some((r) => r.path === path);
  const Icon = module.icon;
  return (
    <a
      href={`#${target}`}
      aria-current={active ? "page" : undefined}
      className={cx(
        "flex h-8 items-center gap-2.5 rounded-control px-2 text-body transition",
        active
          ? "bg-surface-sunken font-medium text-primary"
          : "text-secondary hover:bg-surface-hover hover:text-primary",
      )}
    >
      {Icon && <Icon size={16} className={active ? "text-accent" : "text-icon"} />}
      <span className="truncate">{module.title}</span>
    </a>
  );
}

function Sidebar({ path, settings }: { path: string; settings?: AppSettings }) {
  const links = settings?.["media.links"] ?? [];
  return (
    <nav className="flex w-[236px] shrink-0 flex-col gap-5 overflow-y-auto border-r border-subtle px-4 py-6">
      <div className="flex items-center gap-2.5 px-2">
        <span className="flex h-[22px] w-[22px] items-center justify-center rounded bg-primary font-serif text-[14px] leading-none text-canvas">
          f
        </span>
        <span className="font-serif text-[18px] leading-none tracking-[-0.01em] text-primary">forkOS</span>
      </div>

      <div className="flex flex-col gap-0.5">
        {pinnedModules().map((m) => <NavItem key={m.id} module={m} path={path} />)}
      </div>

      {groupedModules().map((group) => (
        <div key={group.id} className="flex flex-col gap-0.5">
          <div className="label-caps mb-1.5 px-2">{group.label}</div>
          {group.modules.map((m) => <NavItem key={m.id} module={m} path={path} />)}
        </div>
      ))}

      {links.length > 0 && (
        <div className="flex flex-col gap-0.5">
          <div className="label-caps mb-1.5 px-2">Medya</div>
          {links.map((link) => (
            <a
              key={link.name}
              href={link.url}
              target="_blank"
              rel="noreferrer"
              className="flex h-8 items-center gap-2.5 rounded-control px-2 text-body text-secondary transition hover:bg-surface-hover hover:text-primary"
            >
              <ExternalLink size={16} className="text-icon" />
              <span className="truncate">{link.name}</span>
            </a>
          ))}
        </div>
      )}

      <div className="mt-auto flex flex-col gap-2 px-2 pt-4">
        <OnlineDot />
        <div className="text-meta text-muted">
          <Kbd>Ctrl</Kbd> <Kbd>K</Kbd> <span className="ml-1">komutlar</span>
        </div>
      </div>
    </nav>
  );
}

function OnlineDot() {
  const online = useOnline();
  return (
    <div className="flex items-center gap-2 text-meta text-muted">
      <span className={cx("h-1.5 w-1.5 rounded-full", online ? "bg-ok" : "bg-warn")} />
      <span>{online ? "çevrimiçi · yerel" : "çevrimdışı"}</span>
    </div>
  );
}

/* ── Ust serit ───────────────────────────────────────────────────────── */

function ThemeToggle() {
  const [theme, setTheme] = useTheme();
  const next: Theme = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      onClick={() => setTheme(next)}
      title={next === "dark" ? "Koyu temaya geç" : "Açık temaya geç"}
      aria-label={next === "dark" ? "Koyu temaya geç" : "Açık temaya geç"}
      className="flex h-9 w-9 items-center justify-center rounded-control border border-subtle bg-surface text-muted transition hover:bg-surface-hover hover:text-primary"
    >
      {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
}

function Topbar({ path }: { path: string }) {
  const module = moduleForPath(path);
  const today = new Date().toLocaleDateString("tr-TR", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });
  return (
    <header className="flex h-[68px] shrink-0 items-center gap-6 border-b border-subtle px-8">
      <div className="flex min-w-0 flex-col gap-0.5">
        <h1 className="truncate font-serif text-title text-primary">{module?.title ?? "forkOS"}</h1>
        <p className="text-meta text-muted">{today}</p>
      </div>
      <div className="flex-1" />
      <button
        type="button"
        onClick={openCommandPalette}
        className="flex h-9 w-[320px] items-center gap-2.5 rounded-control border border-subtle bg-surface px-3 text-left text-body text-muted transition hover:border-strong"
      >
        <Search size={15} className="shrink-0 text-icon" />
        <span className="flex-1 truncate">Ara veya komut çalıştır…</span>
        <Kbd>Ctrl K</Kbd>
      </button>
      <ThemeToggle />
    </header>
  );
}

/* ── Kabuk ───────────────────────────────────────────────────────────── */

export default function App() {
  const { path } = useHashRoute();
  const online = useOnline();
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: () => api.get<AppSettings>("/settings") });
  if (settings) hydrateSettings(settings);

  useEffect(() => { applyTheme(readTheme()); }, []);

  const routes = allRoutes();
  const route = routes.find((r) => r.path === path);
  const Page = route?.element ?? (path === "/" ? routes[0]?.element : NotFound) ?? NotFound;

  return (
    <ToastProvider>
      <div className="flex h-screen overflow-hidden bg-canvas text-primary">
        <Sidebar path={path} settings={settings} />

        <main className="flex min-w-0 flex-1 flex-col">
          <Topbar path={path} />
          {!online && (
            <Banner tone="warn" icon={<WifiOff size={15} />}>
              Çevrimdışısın. Kayıtlı veriler okunabilir, yazma işlemleri kapalı.
              Tarayıcı eklentisi kaydettiklerini kuyruğa alır.
            </Banner>
          )}
          <SourceAlert />
          <div className="min-h-0 flex-1 overflow-y-auto">
            <Page />
          </div>
        </main>

        <CommandPalette />
        <DialogHost />
      </div>
    </ToastProvider>
  );
}
