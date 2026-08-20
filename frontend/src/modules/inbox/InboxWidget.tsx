import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Empty, Panel, relativeTime } from "@/core/ui";
import { navigate } from "@/app/router";
import type { Bookmark, BookmarkStats } from "@/core/types";

export function InboxWidget() {
  const { data: stats } = useQuery({
    queryKey: ["bookmark-stats"],
    queryFn: () => api.get<BookmarkStats>("/bookmarks/stats"),
  });
  const { data: latest = [] } = useQuery({
    queryKey: ["bookmarks", "inbox", "latest"],
    queryFn: () => api.get<Bookmark[]>(`/bookmarks${qs({ collection: "inbox", limit: 5 })}`),
  });

  return (
    <Panel
      title="Inbox"
      action={
        <button
          onClick={() => navigate("/inbox")}
          className="text-xs text-neutral-500 hover:text-neutral-300"
        >
          {stats?.inbox ?? 0} bekliyor →
        </button>
      }
    >
      {latest.length === 0 ? (
        <Empty>Inbox temiz.</Empty>
      ) : (
        <ul className="space-y-2">
          {latest.map((bookmark) => (
            <li key={bookmark.id} className="truncate text-sm text-neutral-300">
              <a href={bookmark.url} target="_blank" rel="noreferrer" className="hover:underline">
                {bookmark.title || bookmark.url}
              </a>
              <span className="ml-2 text-[11px] text-neutral-600">
                {relativeTime(bookmark.saved_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
      {stats && (
        <p className="mt-3 text-[11px] text-neutral-600">
          Bugun {stats.saved_today} kayit · toplam {stats.total}
        </p>
      )}
    </Panel>
  );
}
