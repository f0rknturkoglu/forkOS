import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Empty, Panel, hostOf } from "@/core/ui";
import { navigate } from "@/app/router";
import type { Bookmark } from "@/core/types";

export function ReadingQueueWidget() {
  const { data = [] } = useQuery({
    queryKey: ["bookmarks", "read_later", "widget"],
    queryFn: () =>
      api.get<Bookmark[]>(`/bookmarks${qs({ collection: "read_later", read_status: "unread", limit: 5 })}`),
  });

  return (
    <Panel
      title="Okuma sirasi"
      action={
        <button
          onClick={() => navigate("/bookmarks")}
          className="text-xs text-neutral-500 hover:text-neutral-300"
        >
          tumu →
        </button>
      }
    >
      {data.length === 0 ? (
        <Empty>Read Later bos.</Empty>
      ) : (
        <ul className="space-y-2">
          {data.map((bookmark) => (
            <li key={bookmark.id} className="truncate text-sm text-neutral-300">
              <a href={bookmark.url} target="_blank" rel="noreferrer" className="hover:underline">
                {bookmark.title || bookmark.url}
              </a>
              <span className="ml-2 text-[11px] text-neutral-600">{hostOf(bookmark.url)}</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
