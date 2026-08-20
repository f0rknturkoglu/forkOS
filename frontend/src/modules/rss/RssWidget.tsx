import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Empty, Panel, relativeTime } from "@/core/ui";
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
    <Panel
      title="RSS"
      action={
        <button
          onClick={() => navigate("/rss")}
          className="text-xs text-neutral-500 hover:text-neutral-300"
        >
          {stats?.unread ?? 0} okunmamis →
        </button>
      }
    >
      {items.length === 0 ? (
        <Empty>Yeni yazi yok.</Empty>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id} className="truncate text-sm text-neutral-300">
              {item.url ? (
                <a href={item.url} target="_blank" rel="noreferrer" className="hover:underline">
                  {item.title}
                </a>
              ) : (
                item.title
              )}
              <span className="ml-2 text-[11px] text-neutral-600">
                {item.feed_title}
                {item.published_at && ` · ${relativeTime(item.published_at)}`}
              </span>
            </li>
          ))}
        </ul>
      )}
      {stats && stats.failing_feeds > 0 && (
        <p className="mt-3 text-[11px] text-amber-500">
          {stats.failing_feeds} feed hata veriyor veya kapali.
        </p>
      )}
    </Panel>
  );
}
