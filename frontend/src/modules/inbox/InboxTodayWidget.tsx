import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Archive, CheckSquare, Clock, ExternalLink, Sparkles } from "lucide-react";
import { api, qs } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Chip, Empty, IconButton, RowList, Section, hostOf, relativeTime, useToast } from "@/core/ui";
import { useHashRoute } from "@/app/router";
import type { Bookmark, BookmarkStats } from "@/core/types";
import { InboxFocusTriageModal } from "./InboxFocusTriageModal";

export function InboxTodayWidget() {
  const toast = useToast();
  const [triageOpen, setTriageOpen] = useState(false);
  const route = useHashRoute();

  // Home derin baglantisi `#/?triage=inbox` odak modunu acar. `/inbox` sayfasi
  // triyaj tahtasinin kendisidir; bu widget orada mount edilmez.
  useEffect(() => {
    if (route.params.get("triage") === "inbox") setTriageOpen(true);
  }, [route.params]);

  const { data: stats } = useQuery({
    queryKey: ["bookmark-stats"],
    queryFn: () => api.get<BookmarkStats>("/bookmarks/stats"),
  });

  const { data: latest = [], refetch } = useQuery({
    queryKey: ["bookmarks", "inbox", "widget-latest"],
    queryFn: () => api.get<Bookmark[]>(`/bookmarks${qs({ collection: "inbox", limit: 5 })}`),
  });

  const move = useMutation({
    mutationFn: ({ id, collection }: { id: string; collection: string }) =>
      api.patch(`/bookmarks/${id}/collection${qs({ collection })}`),
    onSuccess: () => {
      invalidateAfter("bookmark.write");
      toast.push("Kayit tasindi", { tone: "ok" });
      refetch();
    },
  });

  const convertToTask = useMutation({
    mutationFn: (id: string) => api.post<{ todo_id: string }>(`/bookmarks/${id}/convert-to-task`, { priority: 2 }),
    onSuccess: () => {
      invalidateAfter("bookmark.write", "todo.write", "link.write");
      toast.push("Goreve donusturuldu ve arsivlendi", { tone: "ok" });
      refetch();
    },
  });

  const count = stats?.inbox ?? latest.length;

  return (
    <>
      <Section
        title="Gelen Kutusu"
        action={
          count > 0 ? (
            <button
              type="button"
              onClick={() => setTriageOpen(true)}
              className="text-meta text-muted hover:text-accent font-medium transition"
            >
              {count} bekleyen → Triage
            </button>
          ) : undefined
        }
      >
        {latest.length === 0 ? (
          <Empty>Gelen kutusu temiz. Bekleyen kayit yok.</Empty>
        ) : (
          <div className="stack-y-3">
            <RowList>
              {latest.map((bookmark) => (
                <div
                  key={bookmark.id}
                  className="flex items-center justify-between gap-3 py-2 border-b border-subtle last:border-b-0"
                >
                  <div className="min-w-0 flex-1">
                    <a
                      href={bookmark.url}
                      target="_blank"
                      rel="noreferrer"
                      className="block truncate text-body text-primary hover:underline"
                    >
                      {bookmark.title || bookmark.url}
                    </a>
                    <div className="mt-0.5 flex items-center gap-2 text-meta text-muted">
                      <span>{hostOf(bookmark.url)}</span>
                      <span>·</span>
                      <span>{relativeTime(bookmark.saved_at)}</span>
                      {bookmark.note && <Chip tone="accent">Not var</Chip>}
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-1">
                    <IconButton title="Goreve donustur" onClick={() => convertToTask.mutate(bookmark.id)}>
                      <CheckSquare size={14} className="text-accent" />
                    </IconButton>
                    <IconButton
                      title="Sonra oku"
                      onClick={() => move.mutate({ id: bookmark.id, collection: "read_later" })}
                    >
                      <Clock size={14} />
                    </IconButton>
                    <IconButton title="Arsivle" onClick={() => move.mutate({ id: bookmark.id, collection: "archive" })}>
                      <Archive size={14} />
                    </IconButton>
                  </div>
                </div>
              ))}
            </RowList>

            <Button variant="secondary" size="sm" className="w-full" onClick={() => setTriageOpen(true)}>
              <Sparkles size={13} />
              <span>Tumunu Ayikla (Triage Modu)</span>
            </Button>
          </div>
        )}
      </Section>

      <InboxFocusTriageModal open={triageOpen} onClose={() => setTriageOpen(false)} />
    </>
  );
}
