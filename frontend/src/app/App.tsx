import "@/modules";                 // registry'yi doldurur -- ILK import olmali
import { useQuery } from "@tanstack/react-query";
import { CommandPalette } from "@/core/CommandPalette";
import { allRoutes, enabledModules, hydrateSettings } from "@/core/registry";
import { api } from "@/core/api";
import { cx } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { SourceHealth } from "@/core/types";
import type { AppSettings } from "@/core/types";
import { useHashRoute } from "./router";

function NotFound() {
  return <div className="p-6 text-sm text-neutral-400">Boyle bir sayfa yok.</div>;
}

/** Kural 6: sessiz olum kabul edilemez -- kirik kaynak her ekranda gorunur. */
function SourceAlert() {
  const { data = [] } = useQuery({
    queryKey: ["sources", "health"],
    queryFn: () => api.get<SourceHealth[]>("/sources/health"),
    refetchInterval: 5 * 60_000,
  });
  const broken = data.filter((s) => s.status === "error");
  if (broken.length === 0) return null;
  return (
    <div className="border-b border-amber-900/60 bg-amber-950/40 px-6 py-2 text-xs text-amber-300">
      {broken.length} kaynak hata veriyor: {broken.slice(0, 3).map((s) => s.source).join(", ")}
      {broken.length > 3 && ` +${broken.length - 3}`}
    </div>
  );
}

export default function App() {
  const { path } = useHashRoute();
  const online = useOnline();
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: () => api.get<AppSettings>("/settings") });
  if (settings) hydrateSettings(settings);
  const routes = allRoutes();
  const route = routes.find((r) => r.path === path);
  const Page = route?.element ?? (path === "/" ? routes[0]?.element : NotFound) ?? NotFound;

  return (
    <div className="flex min-h-screen bg-neutral-950 text-neutral-100">
      <nav className="flex w-52 shrink-0 flex-col border-r border-neutral-800 p-4">
        <div className="mb-6 text-sm font-semibold tracking-wide">forkOS</div>
        <ul className="space-y-1 text-sm">
          {enabledModules().map((m) => {
            const target = m.routes[0]?.path ?? "/";
            const active = target === path;
            return (
              <li key={m.id}>
                <a
                  href={`#${target}`}
                  className={cx(
                    "block rounded px-2 py-1 transition",
                    active
                      ? "bg-neutral-800 text-neutral-100"
                      : "text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200",
                  )}
                >
                  {m.title}
                </a>
              </li>
            );
          })}
        </ul>
        {(settings?.["media.links"] ?? []).length > 0 && <div className="mt-5 border-t border-neutral-800 pt-4"><p className="mb-2 text-[10px] uppercase tracking-wider text-neutral-600">Media</p>{settings?.["media.links"].map(link => <a key={link.name} href={link.url} target="_blank" className="block rounded px-2 py-1 text-xs text-neutral-500 hover:bg-neutral-900 hover:text-neutral-200">{link.name} ↗</a>)}</div>}
        <div className="mt-auto space-y-1 pt-6 text-[11px] text-neutral-600">
          <div>
            <kbd className="rounded border border-neutral-800 px-1">Ctrl</kbd>
            {" + "}
            <kbd className="rounded border border-neutral-800 px-1">K</kbd> komutlar
          </div>
          <div className={online ? "text-neutral-600" : "text-amber-500"}>
            {online ? "cevrimici" : "cevrimdisi - salt okunur"}
          </div>
        </div>
      </nav>

      <main className="flex-1 overflow-x-hidden">
        {!online && (
          <div className="border-b border-amber-900/60 bg-amber-950/40 px-6 py-2 text-xs text-amber-300">
            Cevrimdisisin. Kayitli veriler okunabilir, yazma islemleri kapali.
            Tarayici eklentisi kaydettiklerini kuyruga alir.
          </div>
        )}
        <SourceAlert />
        <Page />
      </main>

      <CommandPalette />
    </div>
  );
}
