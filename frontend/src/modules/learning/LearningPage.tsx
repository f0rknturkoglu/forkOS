import { invalidateAfter } from "@/core/invalidation";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpen } from "lucide-react";
import { api } from "@/core/api";
import type { Bookmark, Course } from "@/core/types";
import { Button, Empty, Input, PageFrame, PageHeader, Toolbar } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { CoursesTab } from "./CoursesTab";
import { QueueTab } from "./QueueTab";

const tabLabels = { courses: "Kurslar", queue: "Kuyruk" } as const;

/**
 * Ogrenme -- kurslar + tuketim kuyrugu.
 * Kitaplar Faz 11'de media_item'a tasindi; kitap takibi Medya sayfasinda.
 */
export function LearningPage() {
  const [tab, setTab] = useState<"courses" | "queue">("courses");
  const [title, setTitle] = useState("");
  const online = useOnline();
  const { data: courses = [] } = useQuery({
    queryKey: ["courses"],
    queryFn: () => api.get<Course[]>("/courses"),
  });
  const { data: queue = [] } = useQuery({
    queryKey: ["learning-queue"],
    queryFn: () => api.get<Bookmark[]>("/learning/queue"),
  });
  const create = useMutation({
    mutationFn: () => api.post("/courses", { title }),
    onSuccess: () => {
      setTitle("");
      invalidateAfter("learning.write");
    },
  });
  const patchCourse = useMutation({
    mutationFn: ({ id, progress_pct }: { id: string; progress_pct: number }) =>
      api.patch(`/courses/${id}`, {
        progress_pct,
        // %100'e ulasinca kurs bitmis sayilir (backend course.completed atar).
        status: progress_pct >= 100 ? "done" : undefined,
      }),
    onSuccess: () => invalidateAfter("learning.write"),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/courses/${id}`),
    onSuccess: () => invalidateAfter("learning.write"),
  });
  const moveQueue = useMutation({
    mutationFn: ({ id, queue_kind }: { id: string; queue_kind: string }) =>
      api.patch(`/bookmarks/${id}`, { queue_kind }),
    onSuccess: () => invalidateAfter("learning.write"),
  });
  const isEmpty = (tab === "courses" && !courses.length) || (tab === "queue" && !queue.length);
  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Takip" title="Öğrenme" />
      <p className="text-meta text-muted">Kurslar ve yer imi tabanlı tüketim kuyruğu. Kitaplar Medya sayfasında.</p>
      <Toolbar>
        {(["courses", "queue"] as const).map((x) => (
          <Button key={x} variant={tab === x ? "primary" : "ghost"} onClick={() => setTab(x)}>
            {tabLabels[x]}
          </Button>
        ))}
        {tab === "courses" && (
          <form
            className="ml-auto flex min-w-64 flex-1 gap-2 md:max-w-xl"
            onSubmit={(e) => {
              e.preventDefault();
              if (title.trim()) create.mutate();
            }}
          >
            <Input value={title} onChange={setTitle} className="min-w-0 flex-1" placeholder="Yeni kurs" />
            <Button type="submit" variant="primary" disabled={!online || create.isPending}>
              Ekle
            </Button>
          </form>
        )}
        {tab === "queue" && (
          <a
            href="#/media"
            className="ml-auto flex items-center gap-1.5 rounded-control border border-subtle px-3 py-1.5 text-meta text-secondary transition hover:border-strong hover:text-primary"
          >
            <BookOpen size={13} /> Kitaplar Medya'da →
          </a>
        )}
      </Toolbar>
      {tab === "courses" && (
        <CoursesTab
          courses={courses}
          online={online}
          onProgress={(id, progress_pct) => patchCourse.mutate({ id, progress_pct })}
          onRemove={(id) => remove.mutate(id)}
        />
      )}
      {tab === "queue" && (
        <QueueTab queue={queue} online={online} onMove={(id, queue_kind) => moveQueue.mutate({ id, queue_kind })} />
      )}
      {isEmpty && <Empty>Henüz kayıt yok.</Empty>}
    </PageFrame>
  );
}
