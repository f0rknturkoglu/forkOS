import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import type { DragEndEvent } from "@dnd-kit/core";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { ArrowRight, CheckSquare, StickyNote, Tag, Trash2 } from "lucide-react";
import {
  ActionMenu,
  Button,
  Chip,
  Empty,
  IconButton,
  Input,
  Kbd,
  PageFrame,
  RowList,
  cx,
  hostOf,
  relativeTime,
  useToast,
  SkeletonRows,
} from "@/core/ui";
import {
  Workspace,
  WorkspaceInspectorContent,
  WorkspacePaneHeader,
  WorkspaceScrollArea,
  WorkspaceToolbar,
} from "@/core/workspace/Workspace";
import { useOnline } from "@/lib/hooks";
import { COLLECTION_LABELS, COLLECTIONS } from "@/core/types";
import type { Bookmark, Collection } from "@/core/types";

const TARGETS: Collection[] = COLLECTIONS.filter((c) => c !== "inbox");

function InboxCard({
  bookmark,
  disabled,
  selected,
  onSelect,
  onMove,
  registerRef,
}: {
  bookmark: Bookmark;
  disabled: boolean;
  selected: boolean;
  onSelect: () => void;
  onMove: (collection: Collection) => void;
  registerRef: (node: HTMLLIElement | null) => void;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: bookmark.id,
    disabled,
  });
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(bookmark.tags.join(", "));
  const [titleDraft, setTitleDraft] = useState(bookmark.title || bookmark.url);
  // Duzenleme formu acikken kart kisayollarini yut, yoksa "1" yazamazsin.
  const swallow = (e: React.KeyboardEvent) => {
    if (editing) e.stopPropagation();
  };

  const remove = useMutation({
    mutationFn: () => api.del(`/bookmarks/${bookmark.id}`),
    onSuccess: () => {
      invalidateAfter("bookmark.write");
      toast.push("Yer imi silindi", { tone: "neutral" });
    },
  });

  const setTags = useMutation({
    mutationFn: (tags: string[]) => api.patch(`/bookmarks/${bookmark.id}`, { tags }),
    onSuccess: () => invalidateAfter("bookmark.write"),
  });

  const updateTitle = useMutation({
    mutationFn: (title: string) => api.patch(`/bookmarks/${bookmark.id}`, { title }),
    onSuccess: () => invalidateAfter("bookmark.write"),
  });

  const convertToTask = useMutation({
    mutationFn: () => api.post(`/bookmarks/${bookmark.id}/convert-to-task`, { priority: 2 }),
    onSuccess: () => {
      invalidateAfter("bookmark.write", "todo.write", "link.write");
      toast.push("Goreve donusturuldu ve arsivlendi", { tone: "ok" });
    },
  });

  return (
    <li
      ref={(node) => {
        setNodeRef(node);
        registerRef(node);
      }}
      tabIndex={0}
      aria-current={selected ? "true" : undefined}
      onFocus={onSelect}
      onClick={onSelect}
      className={cx(
        "group min-w-0 rounded-control px-2.5 py-2.5 transition",
        selected ? "bg-surface-selected ring-1 ring-inset ring-accent" : "hover:bg-surface-hover",
        isDragging && "opacity-40",
      )}
    >
      <div className="flex items-start gap-2">
        <button
          {...listeners}
          {...attributes}
          disabled={disabled}
          title={disabled ? "Cevrimdisi — tasima kapali" : "Surukle"}
          className="mt-0.5 cursor-grab text-muted hover:text-secondary disabled:cursor-not-allowed"
        >
          ⠿
        </button>
        <div className="min-w-0 flex-1">
          <a
            href={bookmark.url}
            target="_blank"
            rel="noreferrer"
            className="block truncate text-body text-primary hover:underline"
          >
            {bookmark.title || bookmark.url}
          </a>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-meta text-muted">
            <span>{hostOf(bookmark.url)}</span>
            <span>·</span>
            <span>{relativeTime(bookmark.saved_at)}</span>
            <Chip>{bookmark.source}</Chip>
            {bookmark.is_duplicate && (
              <Chip tone="warn">Zaten kayitli: {bookmark.existing_collection || "kutuphane"}</Chip>
            )}
            {bookmark.tags.map((tag) => (
              <Chip key={tag}>#{tag}</Chip>
            ))}
          </div>

          {bookmark.note && (
            <div className="mt-2 flex items-start gap-1.5 rounded-control border border-subtle bg-surface-sunken p-2 text-meta text-primary">
              <StickyNote size={14} className="mt-0.5 shrink-0 text-muted" />
              <p className="whitespace-pre-line">{bookmark.note}</p>
            </div>
          )}

          {bookmark.selection && (
            <p className="mt-2 border-l-2 border-strong pl-2 text-meta italic text-secondary">
              {bookmark.selection.slice(0, 220)}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <IconButton title="Goreve donustur" disabled={disabled} onClick={() => convertToTask.mutate()}>
            <CheckSquare size={15} className="text-accent" />
          </IconButton>
          <ActionMenu
            ariaLabel="Kart eylemleri"
            items={[
              {
                id: "convert-task",
                label: "Göreve dönüştür",
                icon: CheckSquare,
                disabled,
                onSelect: () => convertToTask.mutate(),
              },
              {
                id: "edit",
                label: editing ? "Düzenlemeyi kapat" : "Başlık ve etiketleri düzenle",
                icon: Tag,
                disabled,
                onSelect: () => setEditing((v) => !v),
              },
              ...TARGETS.map((target) => ({
                id: `move-${target}`,
                label: `${COLLECTION_LABELS[target]} içine taşı`,
                icon: ArrowRight,
                disabled,
                onSelect: () => onMove(target),
              })),
              {
                id: "delete",
                label: "Sil",
                icon: Trash2,
                danger: true,
                disabled,
                onSelect: () => remove.mutate(),
              },
            ]}
          />
        </div>
      </div>

      {editing && (
        <form
          onKeyDown={swallow}
          className="mt-3 stack-y-2 border-t border-subtle pt-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (titleDraft.trim() && titleDraft !== bookmark.title) {
              updateTitle.mutate(titleDraft.trim());
            }
            setTags.mutate(
              draft
                .split(",")
                .map((t) => t.trim())
                .filter(Boolean),
            );
            setEditing(false);
          }}
        >
          <Input
            value={titleDraft}
            onChange={setTitleDraft}
            ariaLabel="Baslik"
            placeholder="Baslik"
            className="w-full"
          />
          <div className="flex gap-2">
            <Input
              autoFocus
              value={draft}
              onChange={setDraft}
              ariaLabel="Etiketler, virgulle ayrilmis"
              placeholder="etiketler, virgulle"
              className="flex-1"
              onKeyDown={(e) => {
                if (e.key === "Escape") setEditing(false);
              }}
            />
            <Button type="submit" variant="primary" size="sm">
              Kaydet
            </Button>
            <Button size="sm" onClick={() => setEditing(false)}>
              Vazgec
            </Button>
          </div>
        </form>
      )}
    </li>
  );
}

/**
 * Hem birakma hedefi (fare) hem buton (klavye).
 *
 * Surukle-birak tek yol olamaz: dnd-kit sensoru klavyeyle serbest surukleme
 * verse de hedefi tutturmak isabetsiz. Sec-ve-tikla ayni isi yapar, ekran
 * okuyucuya anlatilabilir ve rakam kisayoluyla da calisir.
 */
function DropTarget({
  collection,
  count,
  index,
  hasSelection,
  onMove,
}: {
  collection: Collection;
  count: number;
  index: number;
  hasSelection: boolean;
  onMove: () => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: collection });
  return (
    <button
      type="button"
      ref={setNodeRef}
      onClick={onMove}
      disabled={!hasSelection}
      title={hasSelection ? `Seçili kaydı ${COLLECTION_LABELS[collection]} içine taşı` : "Önce bir kart seç"}
      className={cx(
        "flex w-full items-center gap-3 rounded-control border px-3 text-left text-body transition",
        "h-touch",
        isOver
          ? "border-accent bg-accent-surface text-accent"
          : hasSelection
            ? "border-strong bg-surface text-primary hover:bg-surface-hover"
            : "cursor-not-allowed border-dashed border-subtle text-muted",
      )}
    >
      <Kbd>{index + 1}</Kbd>
      <span className="flex-1 truncate">{COLLECTION_LABELS[collection]}</span>
      <span className="numeral text-heading text-secondary">{count}</span>
    </button>
  );
}

function QuickCapture() {
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const online = useOnline();

  const toast = useToast();

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
      invalidateAfter("bookmark.write");
      toast.push(result.duplicate ? "Bu URL zaten kayıtlıydı — yine de eklendi." : "Gelen kutusuna eklendi", {
        tone: result.duplicate ? "warn" : "ok",
      });
    },
  });

  return (
    <form
      className="flex w-full flex-wrap gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (url.trim()) capture.mutate();
      }}
    >
      <Input value={url} onChange={setUrl} placeholder="https://..." className="min-w-48 flex-1" />
      <Input
        value={title}
        onChange={setTitle}
        placeholder="Başlık (isteğe bağlı)"
        className="min-w-44 flex-1 sm:max-w-64"
      />
      <Button type="submit" variant="primary" disabled={!online || capture.isPending}>
        Kaydet
      </Button>
    </form>
  );
}

export function InboxPage() {
  const online = useOnline();
  const [dragging, setDragging] = useState<Bookmark | null>(null);
  const [showInspector, setShowInspector] = useState(true);
  /** Klavye yolunun oznesi: uzerinde islem yapilacak kart. */
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const cardRefs = useRef(new Map<string, HTMLLIElement>());
  const toast = useToast();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor),
  );

  const { data = [], isLoading } = useQuery({
    queryKey: ["bookmarks", "inbox"],
    queryFn: () => api.get<Bookmark[]>(`/bookmarks${qs({ collection: "inbox", limit: 200 })}`),
  });

  const { data: stats } = useQuery({
    queryKey: ["bookmark-stats"],
    queryFn: () => api.get<{ collections: { collection: Collection; count: number }[] }>("/bookmarks/stats"),
  });

  const move = useMutation({
    mutationFn: ({ id, collection }: { id: string; collection: Collection }) =>
      api.patch(`/bookmarks/${id}/collection${qs({ collection })}`),
    onSuccess: () => invalidateAfter("bookmark.write"),
  });

  const onDragEnd = (event: DragEndEvent) => {
    setDragging(null);
    const collection = event.over?.id as Collection | undefined;
    if (collection && TARGETS.includes(collection)) {
      move.mutate({ id: String(event.active.id), collection });
    }
  };

  const countOf = (collection: Collection) => stats?.collections.find((c) => c.collection === collection)?.count ?? 0;

  /** Tasima/silme sonrasi odaklanilacak sira. Liste tazelenince kullanilir. */
  const restoreIndex = useRef<number | null>(null);

  useEffect(() => {
    // Listeden dusen kart secili kalmasin.
    if (selectedId && !data.some((b) => b.id === selectedId)) setSelectedId(null);

    // Kart listeden cikinca odak body'ye duserdi; ayni siradaki bir sonrakine
    // geri koy ki klavyeyle ust uste tasima yapilabilsin.
    if (restoreIndex.current !== null && data.length > 0) {
      focusCard(restoreIndex.current);
      restoreIndex.current = null;
    }
  }, [data]); // eslint-disable-line react-hooks/exhaustive-deps

  function focusCard(index: number) {
    const target = data[Math.max(0, Math.min(index, data.length - 1))];
    if (!target) return;
    setSelectedId(target.id);
    cardRefs.current.get(target.id)?.focus();
  }

  function moveCard(id: string, collection: Collection) {
    if (!online) return;
    const bookmark = data.find((b) => b.id === id);
    if (!bookmark) return;
    const index = data.findIndex((b) => b.id === id);
    move.mutate({ id, collection });
    toast.push(`“${(bookmark.title || bookmark.url).slice(0, 40)}” ${COLLECTION_LABELS[collection]} içine taşındı`, {
      tone: "ok",
      action: { label: "Geri al", run: () => move.mutate({ id, collection: "inbox" }) },
    });
    restoreIndex.current = index;
  }

  function moveSelected(collection: Collection) {
    if (selectedId) moveCard(selectedId, collection);
  }

  /** Liste uzerindeki kisayollar. Kart odaktayken calisir. */
  function onListKeyDown(event: React.KeyboardEvent<HTMLElement>) {
    if (!selectedId) return;
    const index = data.findIndex((b) => b.id === selectedId);
    const key = event.key;

    if (key === "ArrowDown" || key === "j") {
      event.preventDefault();
      focusCard(index + 1);
      return;
    }
    if (key === "ArrowUp" || key === "k") {
      event.preventDefault();
      focusCard(index - 1);
      return;
    }

    const slot = Number(key);
    if (Number.isInteger(slot) && slot >= 1 && slot <= TARGETS.length) {
      event.preventDefault();
      moveSelected(TARGETS[slot - 1]);
    }
  }

  return (
    <DndContext
      sensors={sensors}
      onDragStart={(e) => setDragging(data.find((b) => b.id === e.active.id) ?? null)}
      onDragCancel={() => setDragging(null)}
      onDragEnd={onDragEnd}
    >
      <Workspace
        inspector={
          showInspector ? (
            <WorkspaceInspectorContent
              title="Taşı"
              hint={selectedId ? "1 kart seçili" : "önce kart seç"}
              onClose={() => setShowInspector(false)}
            >
              <div className="stack-y-2">
                {TARGETS.map((collection, index) => (
                  <DropTarget
                    key={collection}
                    collection={collection}
                    index={index}
                    count={countOf(collection)}
                    hasSelection={Boolean(selectedId) && online}
                    onMove={() => moveSelected(collection)}
                  />
                ))}
              </div>
              <dl className="mt-4 stack-y-1.5 border-t border-subtle pt-3 text-meta text-muted">
                {[
                  ["↑ ↓", "kartlar arasında gez"],
                  [`1–${TARGETS.length}`, "seçili kartı taşı"],
                ].map(([keys, what]) => (
                  <div key={keys} className="flex items-center gap-2">
                    <dt>
                      <Kbd>{keys}</Kbd>
                    </dt>
                    <dd>{what}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-3 text-meta text-muted">Sürükle, hedefe tıkla veya sayı tuşlarını kullan.</p>
            </WorkspaceInspectorContent>
          ) : undefined
        }
      >
        <WorkspacePaneHeader
          title="Bekleyenler"
          eyebrow="Gelen Kutusu"
          hint={`${data.length} kayıt`}
          action={
            !showInspector ? (
              <Button size="sm" variant="ghost" onClick={() => setShowInspector(true)}>
                Hedefleri göster
              </Button>
            ) : undefined
          }
        />
        <WorkspaceToolbar className="h-auto py-2">
          <QuickCapture />
        </WorkspaceToolbar>
        <WorkspaceScrollArea className="p-4">
          {isLoading ? (
            <SkeletonRows rows={6} />
          ) : data.length === 0 ? (
            <Empty>Gelen kutusu boş. Tarayıcıdan Ctrl+Shift+S ile kaydet.</Empty>
          ) : (
            <RowList as="ul" onKeyDown={onListKeyDown}>
              {data.map((bookmark) => (
                <InboxCard
                  key={bookmark.id}
                  bookmark={bookmark}
                  disabled={!online}
                  selected={selectedId === bookmark.id}
                  onSelect={() => setSelectedId(bookmark.id)}
                  onMove={(target) => moveCard(bookmark.id, target)}
                  registerRef={(node) => {
                    if (node) cardRefs.current.set(bookmark.id, node);
                    else cardRefs.current.delete(bookmark.id);
                  }}
                />
              ))}
            </RowList>
          )}
        </WorkspaceScrollArea>
      </Workspace>

      <DragOverlay>
        {dragging && (
          <div className="rounded border border-accent-border bg-surface px-3 py-2 text-body shadow-overlay">
            {dragging.title || dragging.url}
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
