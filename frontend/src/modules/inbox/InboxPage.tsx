import { useState } from "react";
import { DndContext, DragOverlay, PointerSensor, useDraggable, useDroppable, useSensor, useSensors } from "@dnd-kit/core";
import type { DragEndEvent } from "@dnd-kit/core";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Badge, Button, Empty, Panel, cx, hostOf, relativeTime } from "@/core/ui";
import { useInvalidate, useOnline } from "@/lib/hooks";
import { COLLECTION_LABELS, COLLECTIONS } from "@/core/types";
import type { Bookmark, Collection } from "@/core/types";

const TARGETS: Collection[] = COLLECTIONS.filter((c) => c !== "inbox");

function InboxCard({ bookmark, disabled }: { bookmark: Bookmark; disabled: boolean }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: bookmark.id,
    disabled,
  });
  const invalidate = useInvalidate();

  const remove = useMutation({
    mutationFn: () => api.del(`/bookmarks/${bookmark.id}`),
    onSuccess: () => invalidate("bookmarks", "bookmark-stats", "activity"),
  });

  const setTags = useMutation({
    mutationFn: (tags: string[]) => api.patch(`/bookmarks/${bookmark.id}`, { tags }),
    onSuccess: () => invalidate("bookmarks", "tags"),
  });

  return (
    <li
      ref={setNodeRef}
      className={cx(
        "rounded border border-neutral-800 bg-neutral-900/40 p-3",
        isDragging && "opacity-40",
      )}
    >
      <div className="flex items-start gap-2">
        <button
          {...listeners}
          {...attributes}
          disabled={disabled}
          title={disabled ? "Cevrimdisi - tasima kapali" : "Surukle"}
          className="mt-0.5 cursor-grab text-neutral-600 hover:text-neutral-400 disabled:cursor-not-allowed"
        >
          ⠿
        </button>
        <div className="min-w-0 flex-1">
          <a
            href={bookmark.url}
            target="_blank"
            rel="noreferrer"
            className="block truncate text-sm text-neutral-100 hover:underline"
          >
            {bookmark.title || bookmark.url}
          </a>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-neutral-500">
            <span>{hostOf(bookmark.url)}</span>
            <span>·</span>
            <span>{relativeTime(bookmark.saved_at)}</span>
            <Badge>{bookmark.source}</Badge>
            {bookmark.tags.map((tag) => (
              <Badge key={tag}>#{tag}</Badge>
            ))}
          </div>
          {bookmark.selection && (
            <p className="mt-2 border-l-2 border-neutral-700 pl-2 text-xs italic text-neutral-400">
              {bookmark.selection.slice(0, 220)}
            </p>
          )}
        </div>
        <div className="flex shrink-0 gap-1">
          <Button
            disabled={disabled}
            title="Etiket ekle"
            onClick={() => {
              const input = prompt("Etiketler (virgulle)", bookmark.tags.join(", "));
              if (input !== null) {
                setTags.mutate(input.split(",").map((t) => t.trim()).filter(Boolean));
              }
            }}
          >
            #
          </Button>
          <Button variant="danger" disabled={disabled} onClick={() => remove.mutate()}>
            sil
          </Button>
        </div>
      </div>
    </li>
  );
}

function DropTarget({ collection, count }: { collection: Collection; count: number }) {
  const { setNodeRef, isOver } = useDroppable({ id: collection });
  return (
    <div
      ref={setNodeRef}
      className={cx(
        "flex items-center justify-between rounded border px-3 py-3 text-sm transition",
        isOver
          ? "border-sky-600 bg-sky-900/30 text-sky-200"
          : "border-dashed border-neutral-800 text-neutral-400",
      )}
    >
      <span>{COLLECTION_LABELS[collection]}</span>
      <span className="text-xs text-neutral-600">{count}</span>
    </div>
  );
}

function QuickCapture() {
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const online = useOnline();
  const invalidate = useInvalidate();

  const capture = useMutation({
    mutationFn: () =>
      api.post<{ id: string; duplicate: boolean }>("/capture", {
        url: url.trim(),
        title: title.trim(),
        collection: "inbox",
        source: "manual",
        client_uuid: crypto.randomUUID(),
      }),
    onSuccess: (result) => {
      setUrl("");
      setTitle("");
      invalidate("bookmarks", "bookmark-stats", "activity");
      if (result.duplicate) alert("Bu URL zaten kayitli -- yine de eklendi.");
    },
  });

  return (
    <form
      className="mb-4 flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (url.trim()) capture.mutate();
      }}
    >
      <input
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="https://..."
        className="flex-1 rounded border border-neutral-800 bg-neutral-900 px-3 py-1.5 text-sm outline-none focus:border-neutral-600"
      />
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Baslik (istege bagli)"
        className="w-56 rounded border border-neutral-800 bg-neutral-900 px-3 py-1.5 text-sm outline-none focus:border-neutral-600"
      />
      <Button type="submit" variant="primary" disabled={!online || capture.isPending}>
        Kaydet
      </Button>
    </form>
  );
}

export function InboxPage() {
  const online = useOnline();
  const invalidate = useInvalidate();
  const [dragging, setDragging] = useState<Bookmark | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  const { data = [], isLoading } = useQuery({
    queryKey: ["bookmarks", "inbox"],
    queryFn: () => api.get<Bookmark[]>(`/bookmarks${qs({ collection: "inbox", limit: 200 })}`),
  });

  const { data: stats } = useQuery({
    queryKey: ["bookmark-stats"],
    queryFn: () => api.get<{ collections: { collection: Collection; count: number }[] }>(
      "/bookmarks/stats",
    ),
  });

  const move = useMutation({
    mutationFn: ({ id, collection }: { id: string; collection: Collection }) =>
      api.patch(`/bookmarks/${id}/collection${qs({ collection })}`),
    onSuccess: () => invalidate("bookmarks", "bookmark-stats", "activity"),
  });

  const onDragEnd = (event: DragEndEvent) => {
    setDragging(null);
    const collection = event.over?.id as Collection | undefined;
    if (collection && TARGETS.includes(collection)) {
      move.mutate({ id: String(event.active.id), collection });
    }
  };

  const countOf = (collection: Collection) =>
    stats?.collections.find((c) => c.collection === collection)?.count ?? 0;

  return (
    <div className="p-6">
      <header className="mb-4 flex items-baseline justify-between">
        <h1 className="text-xl font-semibold">Inbox</h1>
        <span className="text-xs text-neutral-500">{data.length} kayit</span>
      </header>

      <QuickCapture />

      <DndContext
        sensors={sensors}
        onDragStart={(e) => setDragging(data.find((b) => b.id === e.active.id) ?? null)}
        onDragCancel={() => setDragging(null)}
        onDragEnd={onDragEnd}
      >
        <div className="grid gap-4 lg:grid-cols-[1fr_240px]">
          <div>
            {isLoading ? (
              <p className="text-sm text-neutral-500">Yukleniyor...</p>
            ) : data.length === 0 ? (
              <Empty>Inbox bos. Ctrl+Shift+S ile tarayicidan kaydet.</Empty>
            ) : (
              <ul className="space-y-2">
                {data.map((bookmark) => (
                  <InboxCard key={bookmark.id} bookmark={bookmark} disabled={!online} />
                ))}
              </ul>
            )}
          </div>

          <Panel title="Tasi" className="h-fit">
            <div className="space-y-2">
              {TARGETS.map((collection) => (
                <DropTarget
                  key={collection}
                  collection={collection}
                  count={countOf(collection)}
                />
              ))}
            </div>
            <p className="mt-3 text-[11px] text-neutral-600">
              Surukle-birak tek UPDATE'tir; link ve event'ler kopmaz.
            </p>
          </Panel>
        </div>

        <DragOverlay>
          {dragging && (
            <div className="rounded border border-sky-700 bg-neutral-900 px-3 py-2 text-sm shadow-xl">
              {dragging.title || dragging.url}
            </div>
          )}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
