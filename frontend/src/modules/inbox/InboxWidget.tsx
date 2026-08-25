import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Empty, RowList, Section, relativeTime } from "@/core/ui";
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
    <Section
      title="Gelen Kutusu"
      action={
        <button onClick={() => navigate("/inbox")} className="text-meta text-muted hover:text-primary">
          {stats?.inbox ?? 0} bekliyor →
        </button>
      }
    >
      {latest.length === 0 ? (
        <Empty>Gelen kutusu temiz.</Empty>
      ) : (
        <RowList>
          {latest.map((bookmark) => (
            <a
              key={bookmark.id}
              href={bookmark.url}
              target="_blank"
              rel="noreferrer"
              className="flex items-baseline justify-between gap-3 py-2 hover:text-accent"
            >
              <span className="truncate text-body text-secondary">{bookmark.title || bookmark.url}</span>
              <span className="shrink-0 text-meta text-muted">{relativeTime(bookmark.saved_at)}</span>
            </a>
          ))}
        </RowList>
      )}
      {stats && (
        <p className="mt-3 text-meta text-muted">
          Bugün {stats.saved_today} kayıt · toplam {stats.total}
        </p>
      )}
    </Section>
  );
}
