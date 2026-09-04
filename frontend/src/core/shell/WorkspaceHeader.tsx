import { Menu, Moon, Search, Sun } from "lucide-react";
import { openCommandPalette } from "@/core/CommandPalette";
import { NotificationPanel } from "@/core/NotificationPanel";
import { moduleForPath, titleForPath } from "@/core/registry";
import { StatusLed } from "@/core/StatusLed";
import { Kbd, useTheme } from "@/core/ui";

export function WorkspaceHeader({ path, onOpenSidebar }: { path: string; onOpenSidebar: () => void }) {
  const [theme, setTheme] = useTheme();
  const module = moduleForPath(path);
  const title = titleForPath(path) ?? "forkOS";
  const Icon = module?.icon;

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

      <div className="flex min-w-0 flex-1 items-center gap-2">
        {Icon && <Icon size={15} className="shrink-0 text-icon" />}
        <span className="truncate text-heading text-primary">{title}</span>
        {module && title !== module.title && (
          <span className="hidden truncate text-meta text-muted sm:inline">{module.title}</span>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-1">
        <StatusLed />
        <button
          type="button"
          onClick={openCommandPalette}
          className="hidden h-8 w-52 items-center gap-2 rounded-control border border-subtle bg-surface px-2.5 text-left text-meta text-muted transition hover:bg-surface-hover hover:text-primary lg:flex"
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
        <NotificationPanel />
        <button
          type="button"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          title="Temayı değiştir"
          aria-label="Temayı değiştir"
          className="flex h-8 w-8 items-center justify-center rounded-control text-muted transition hover:bg-surface-hover hover:text-primary"
        >
          {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </header>
  );
}
