import { BarChart3, CalendarClock, ListVideo, Trash2 } from "lucide-react";
import { useHashRoute } from "@/app/router";
import { requestNavigation } from "@/core/navigationGuard";
import { cx } from "@/core/ui";

// Modül kökü kütüphanedir (`/media`); "Kütüphane" girdisi parent ile aynı
// rotaya çıktığı için listede tekrar edilmez, yalnız alt görünümler kalır.
const VIEWS = [
  { path: "/media/collections", label: "Koleksiyonlar", icon: ListVideo },
  { path: "/media/upcoming", label: "Yaklaşanlar", icon: CalendarClock },
  { path: "/media/stats", label: "İstatistikler", icon: BarChart3 },
  { path: "/media/trash", label: "Çöp", icon: Trash2 },
] as const;

export function MediaSidebar({ onNavigate }: { collapsed: boolean; onNavigate: () => void }) {
  const route = useHashRoute();
  // Eski `/media/library` bağlantısı kütüphaneye gider; hiçbir alt görünüm aktif değildir.
  const activePath = route.path === "/media/library" ? "/media" : route.path;

  return (
    <div className="ml-6 mt-1 space-y-0.5 border-l border-subtle pl-2">
      {VIEWS.map(({ path, label, icon: Icon }) => {
        const active = activePath === path || activePath.startsWith(`${path}/`);
        return (
          <a
            key={path}
            href={`#${path}`}
            aria-current={active ? "page" : undefined}
            onClick={(event) => {
              if (!requestNavigation(path)) {
                event.preventDefault();
                return;
              }
              onNavigate();
            }}
            className={cx(
              "flex h-8 min-w-0 items-center gap-2 rounded-control px-2 text-meta transition",
              active
                ? "bg-surface-selected font-medium text-primary"
                : "text-muted hover:bg-surface-hover hover:text-primary",
            )}
          >
            <Icon size={13} className="shrink-0" />
            <span className="truncate">{label}</span>
          </a>
        );
      })}
    </div>
  );
}
