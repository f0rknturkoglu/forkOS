import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Empty, RowList, Section, relativeTime } from "@/core/ui";
import { navigate } from "@/app/router";
import type { FeedItem, RssStats } from "@/core/types";

export function RssWidget() {
  const { data: stats } = useQuery({
    queryKey: ["rss-stats"],
    queryFn: () => api.get<RssStats>("/rss/stats"),
  });
  const { data: items = [] } = useQuery({
    queryKey: ["items", "widget"],
    queryFn: () => api.get<FeedItem[]>(`/rss/items${qs({ unread_only: true, limit: 5 })}`),
  });

  return (
    <Section
      title="RSS"
      action={
        <button
          onClick={() => navigate("/rss")}
          className="text-meta text-muted hover:text-primary"
        >
          {stats?.unread ?? 0} okunmamış →
        </button>
      }
    >
      {items.length === 0 ? (
        <Empty>Yeni yazı yok.</Empty>
      ) : (
        <RowList>
          {items.map((item) => (
            <div key={item.id} className="min-w-0 py-2 text-body text-secondary">
              {item.url ? (
                <a href={item.url} target="_blank" rel="noreferrer" className="block truncate hover:text-accent">
                  {item.title}
                </a>
              ) : (
                item.title
              )}
              <span className="block truncate text-meta text-muted">
                {item.feed_title}
                {item.published_at && ` · ${relativeTime(item.published_at)}`}
              </span>
            </div>
          ))}
        </RowList>
      )}
      {stats && stats.failing_feeds > 0 && (
        <p className="mt-3 text-meta text-warn">
          {stats.failing_feeds} feed hata veriyor veya kapali.
        </p>
      )}
    </Section>
  );
}
