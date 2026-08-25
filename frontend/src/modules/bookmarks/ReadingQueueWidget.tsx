import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Empty, RowList, Section, hostOf } from "@/core/ui";
import { navigate } from "@/app/router";
import type { Bookmark } from "@/core/types";

export function ReadingQueueWidget() {
  const { data = [] } = useQuery({
    queryKey: ["bookmarks", "read_later", "widget"],
    queryFn: () =>
      api.get<Bookmark[]>(`/bookmarks${qs({ collection: "read_later", read_status: "unread", limit: 5 })}`),
  });

  return (
    <Section
      title="Okuma sırası"
      action={
        <button onClick={() => navigate("/bookmarks")} className="text-meta text-muted hover:text-primary">
          tümü →
        </button>
      }
    >
      {data.length === 0 ? (
        <Empty>Okuma listesi boş.</Empty>
      ) : (
        <RowList>
          {data.map((bookmark) => (
            <a
              key={bookmark.id}
              href={bookmark.url}
              target="_blank"
              rel="noreferrer"
              className="block min-w-0 py-2 hover:text-accent"
            >
              <span className="block truncate text-body text-secondary">{bookmark.title || bookmark.url}</span>
              <span className="block truncate text-meta text-muted">{hostOf(bookmark.url)}</span>
            </a>
          ))}
        </RowList>
      )}
    </Section>
  );
}
