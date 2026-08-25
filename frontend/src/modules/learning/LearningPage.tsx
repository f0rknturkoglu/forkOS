import { invalidateAfter } from "@/core/invalidation";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { Book, Bookmark, Course } from "@/core/types";
import { Button, Empty, Input, PageFrame, PageHeader, Toolbar } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { BooksTab } from "./BooksTab";
import { CoursesTab } from "./CoursesTab";
import { QueueTab } from "./QueueTab";

const tabLabels = { courses: "Kurslar", books: "Kitaplar", queue: "Kuyruk" } as const;

export function LearningPage() {
  const [tab, setTab] = useState<"courses" | "books" | "queue">("courses");
  const [title, setTitle] = useState("");
  const online = useOnline();
  const { data: courses = [] } = useQuery({
    queryKey: ["courses"],
    queryFn: () => api.get<Course[]>("/courses"),
  });
  const { data: books = [] } = useQuery({
    queryKey: ["books"],
    queryFn: () => api.get<Book[]>("/books"),
  });
  const { data: queue = [] } = useQuery({
    queryKey: ["learning-queue"],
    queryFn: () => api.get<Bookmark[]>("/learning/queue"),
  });
  const create = useMutation({
    mutationFn: () => (tab === "courses" ? api.post("/courses", { title }) : api.post("/books", { title })),
    onSuccess: () => {
      setTitle("");
      invalidateAfter("learning.write");
    },
  });
  const patchCourse = useMutation({
    mutationFn: ({ id, progress_pct }: { id: string; progress_pct: number }) =>
      api.patch(`/courses/${id}`, {
        progress_pct,
        status: progress_pct === 100 ? "done" : "active",
      }),
    onSuccess: () => invalidateAfter("learning.write"),
  });
  const patchBook = useMutation({
    mutationFn: ({ id, current_page }: { id: string; current_page: number }) =>
      api.patch(`/books/${id}`, { current_page }),
    onSuccess: () => invalidateAfter("learning.write"),
  });
  const remove = useMutation({
    mutationFn: ({ id, kind }: { id: string; kind: "courses" | "books" }) => api.del(`/${kind}/${id}`),
    onSuccess: () => invalidateAfter("learning.write"),
  });
  const moveQueue = useMutation({
    mutationFn: ({ id, queue_kind }: { id: string; queue_kind: string }) =>
      api.patch(`/bookmarks/${id}`, { queue_kind }),
    onSuccess: () => invalidateAfter("learning.write"),
  });
  const isEmpty =
    (tab === "courses" && !courses.length) || (tab === "books" && !books.length) || (tab === "queue" && !queue.length);
  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Takip" title="Öğrenme" />
      <p className="text-meta text-muted">Kurslar, kitaplar ve yer imi tabanlı tüketim kuyruğu.</p>
      <Toolbar>
        {(["courses", "books", "queue"] as const).map((x) => (
          <Button key={x} variant={tab === x ? "primary" : "ghost"} onClick={() => setTab(x)}>
            {tabLabels[x]}
          </Button>
        ))}
        {tab !== "queue" && (
          <form
            className="ml-auto flex min-w-64 flex-1 gap-2 md:max-w-xl"
            onSubmit={(e) => {
              e.preventDefault();
              if (title.trim()) create.mutate();
            }}
          >
            <Input
              value={title}
              onChange={setTitle}
              className="min-w-0 flex-1"
              placeholder={tab === "courses" ? "Yeni kurs" : "Yeni kitap"}
            />
            <Button type="submit" variant="primary" disabled={!online || create.isPending}>
              Ekle
            </Button>
          </form>
        )}
      </Toolbar>
      {tab === "courses" && (
        <CoursesTab
          courses={courses}
          online={online}
          onProgress={(id, progress_pct) => patchCourse.mutate({ id, progress_pct })}
          onRemove={(id) => remove.mutate({ id, kind: "courses" })}
        />
      )}
      {tab === "books" && (
        <BooksTab
          books={books}
          online={online}
          onPage={(id, current_page) => patchBook.mutate({ id, current_page })}
          onRemove={(id) => remove.mutate({ id, kind: "books" })}
        />
      )}
      {tab === "queue" && (
        <QueueTab queue={queue} online={online} onMove={(id, queue_kind) => moveQueue.mutate({ id, queue_kind })} />
      )}
      {isEmpty && <Empty>Henüz kayıt yok.</Empty>}
    </PageFrame>
  );
}
