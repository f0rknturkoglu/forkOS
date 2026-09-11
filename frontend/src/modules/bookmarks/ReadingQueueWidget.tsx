import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, Clock, ExternalLink } from "lucide-react";
import { api, qs } from "@/core/api";
import { Chip, Empty, IconButton, RowList, Section, hostOf } from "@/core/ui";
import { navigate } from "@/app/router";
import type { Bookmark } from "@/core/types";
import { BookmarkReaderModal } from "./BookmarkReaderModal";

export function ReadingQueueWidget() {
  const [activeBookmark, setActiveBookmark] = useState<Bookmark | null>(null);

  const { data = [] } = useQuery({
    queryKey: ["bookmarks", "read_later", "widget"],
    queryFn: () =>
      api.get<Bookmark[]>(`/bookmarks${qs({ collection: "read_later", read_status: "unread", limit: 5 })}`),
  });

  return (
    <>
      <Section
        title="Okuma sirasi"
        action={
          <button
            type="button"
            onClick={() => navigate("/bookmarks")}
            className="text-meta text-muted hover:text-primary transition"
          >
            tumu →
          </button>
        }
      >
        {data.length === 0 ? (
          <Empty>Okuma listesi bos.</Empty>
        ) : (
          <RowList>
            {data.map((bookmark) => (
              <div
                key={bookmark.id}
                className="group flex items-center justify-between gap-3 py-2 transition hover:bg-surface-hover/50 rounded-control px-1"
              >
                <button
                  type="button"
                  onClick={() => setActiveBookmark(bookmark)}
                  className="min-w-0 flex-1 text-left focus:outline-none"
                >
                  <span className="block truncate text-body font-medium text-primary group-hover:text-accent transition-colors">
                    {bookmark.title || bookmark.url}
                  </span>
                  <div className="flex items-center gap-2 text-meta text-muted font-mono mt-0.5">
                    <span className="truncate">{hostOf(bookmark.url)}</span>
                    {Boolean(bookmark.reading_time_min) && (
                      <>
                        <span>·</span>
                        <Chip tone="accent">
                          <Clock size={10} className="mr-1 inline" />
                          {bookmark.reading_time_min} dk
                        </Chip>
                      </>
                    )}
                    {Boolean(bookmark.scroll_progress && bookmark.scroll_progress > 0) && (
                      <>
                        <span>·</span>
                        <span className="text-accent font-sans">%{bookmark.scroll_progress} okundu</span>
                      </>
                    )}
                  </div>
                </button>

                <div className="flex items-center gap-1 shrink-0 opacity-80 group-hover:opacity-100 transition-opacity">
                  <a
                    href={bookmark.url}
                    target="_blank"
                    rel="noreferrer"
                    title="Orijinal sayfayi ac"
                    className="inline-flex h-7 w-7 items-center justify-center rounded-control text-muted hover:bg-surface-hover hover:text-primary transition"
                  >
                    <ExternalLink size={13} />
                  </a>
                  <IconButton
                    title="Odak Okuma Modunda Ac"
                    onClick={() => setActiveBookmark(bookmark)}
                  >
                    <BookOpen size={14} />
                  </IconButton>
                </div>
              </div>
            ))}
          </RowList>
        )}
      </Section>

      <BookmarkReaderModal
        open={Boolean(activeBookmark)}
        bookmark={activeBookmark}
        onClose={() => setActiveBookmark(null)}
      />
    </>
  );
}
