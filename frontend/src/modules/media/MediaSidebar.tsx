import { BarChart3, CalendarClock, Library, ListVideo, Trash2 } from "lucide-react";
import { useHashRoute } from "@/app/router";
import { requestNavigation } from "@/core/navigationGuard";
import { cx } from "@/core/ui";

const VIEWS = [
  { path: "/media", label: "Kütüphane", icon: Library },
  { path: "/media/collections", label: "Koleksiyonlar", icon: ListVideo },
  { path: "/media/upcoming", label: "Yaklaşanlar", icon: CalendarClock },
  { path: "/media/stats", label: "İstatistikler", icon: BarChart3 },
  { path: "/media/trash", label: "Çöp", icon: Trash2 },
] as const;

export function MediaSidebar({ onNavigate }: { collapsed: boolean; onNavigate: () => void }) {
  const route = useHashRoute();
  const activePath = route.path === "/media/library" ? "/media" : route.path;

  return (
    <div className="ml-6 mt-1 space-y-0.5 border-l border-subtle pl-2">
      {VIEWS.map(({ path, label, icon: Icon }) => {
        const active =
          path === "/media"
            ? activePath === "/media" ||
              (activePath.startsWith("/media/") && !VIEWS.some((view) => view.path === activePath))
            : activePath === path;
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
