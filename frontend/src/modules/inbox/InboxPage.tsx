import { useEffect, useRef, useState } from "react";
import { DndContext, DragOverlay, KeyboardSensor, PointerSensor, useDraggable, useDroppable, useSensor, useSensors } from "@dnd-kit/core";
import type { DragEndEvent } from "@dnd-kit/core";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Tag, Trash2 } from "lucide-react";
import { Badge, Button, Empty, IconButton, Input, Kbd, PageFrame, PageHeader, RowList, Section, Toolbar, cx, hostOf, relativeTime, useToast } from "@/core/ui";
import { useInvalidate, useOnline } from "@/lib/hooks";
import { COLLECTION_LABELS, COLLECTIONS } from "@/core/types";
import type { Bookmark, Collection } from "@/core/types";

const TARGETS: Collection[] = COLLECTIONS.filter((c) => c !== "inbox");

function InboxCard({
  bookmark, disabled, selected, onSelect, registerRef,
}: {
  bookmark: Bookmark;
  disabled: boolean;
  selected: boolean;
  onSelect: () => void;
  registerRef: (node: HTMLLIElement | null) => void;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: bookmark.id,
    disabled,
  });
  const invalidate = useInvalidate();
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(bookmark.tags.join(", "));
  // Duzenleme formu acikken kart kisayollarini yut, yoksa "1" yazamazsin.
  const swallow = (e: React.KeyboardEvent) => { if (editing) e.stopPropagation(); };

  const remove = useMutation({
    mutationFn: () => api.del(`/bookmarks/${bookmark.id}`),
    onSuccess: () => {
      invalidate("bookmarks", "bookmark-stats", "activity");
      toast.push("Yer imi silindi", { tone: "neutral" });
    },
  });

  const setTags = useMutation({
    mutationFn: (tags: string[]) => api.patch(`/bookmarks/${bookmark.id}`, { tags }),
    onSuccess: () => invalidate("bookmarks", "tags"),
  });

  return (
    <li
      ref={(node) => { setNodeRef(node); registerRef(node); }}
      // Klavye yolu: kart odaklanabilir; secim ok tuslariyla gezer,
      // tasima 1-4 ile yapilir. Sayfanin altindaki lejant bunu anlatir.
      tabIndex={0}
      aria-current={selected ? "true" : undefined}
      onFocus={onSelect}
      onClick={onSelect}
      className={cx(
        "group min-w-0 px-1 py-3 transition hover:bg-surface-hover",
        selected ? "bg-accent-surface ring-1 ring-inset ring-accent" : "",
        isDragging && "opacity-40",
      )}
    >
      <div className="flex items-start gap-2">
        <button
          {...listeners}
          {...attributes}
          disabled={disabled}
          title={disabled ? "Çevrimdışı — taşıma kapalı" : "Sürükle"}
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
            <Badge>{bookmark.source}</Badge>
            {bookmark.tags.map((tag) => (
              <Badge key={tag}>#{tag}</Badge>
            ))}
          </div>
          {bookmark.selection && (
            <p className="mt-2 border-l-2 border-strong pl-2 text-meta italic text-secondary">
              {bookmark.selection.slice(0, 220)}
            </p>
          )}
        </div>
        <div className="flex shrink-0 gap-1">
          <IconButton
            title="Etiketleri düzenle"
            disabled={disabled}
            onClick={() => setEditing((v) => !v)}
          >
            <Tag size={15} />
          </IconButton>
          <IconButton title="Sil" tone="danger" disabled={disabled} onClick={() => remove.mutate()}>
            <Trash2 size={15} />
          </IconButton>
        </div>
      </div>

      {editing && (
        <form
          onKeyDown={swallow}
          className="mt-3 flex gap-2 border-t border-subtle pt-3"
          onSubmit={(e) => {
            e.preventDefault();
            setTags.mutate(draft.split(",").map((t) => t.trim()).filter(Boolean));
            setEditing(false);
          }}
        >
          <Input
            autoFocus
            value={draft}
            onChange={setDraft}
            ariaLabel="Etiketler, virgülle ayrılmış"
            placeholder="etiketler, virgülle"
            className="flex-1"
            onKeyDown={(e) => { if (e.key === "Escape") setEditing(false); }}
          />
          <Button type="submit" variant="primary" size="sm">Kaydet</Button>
          <Button size="sm" onClick={() => setEditing(false)}>Vazgeç</Button>
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
  collection, count, index, hasSelection, onMove,
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
      <span className="numeral text-[15px] text-secondary">{count}</span>
    </button>
  );
}

function QuickCapture() {
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const online = useOnline();
  const invalidate = useInvalidate();

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
      invalidate("bookmarks", "bookmark-stats", "activity");
      toast.push(
        result.duplicate ? "Bu URL zaten kayıtlıydı — yine de eklendi." : "Gelen kutusuna eklendi",
        { tone: result.duplicate ? "warn" : "ok" },
      );
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
      <input
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="https://..."
        className="min-w-48 flex-1 rounded border border-subtle bg-surface px-3 py-1.5 text-body outline-none focus:border-accent"
      />
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Başlık (isteğe bağlı)"
        className="min-w-44 flex-1 rounded border border-subtle bg-surface px-3 py-1.5 text-body outline-none sm:max-w-64 focus:border-accent"
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

  function moveSelected(collection: Collection) {
    if (!selectedId || !online) return;
    const bookmark = data.find((b) => b.id === selectedId);
    if (!bookmark) return;
    const index = data.findIndex((b) => b.id === selectedId);
    move.mutate({ id: selectedId, collection });
    toast.push(`“${(bookmark.title || bookmark.url).slice(0, 40)}” ${COLLECTION_LABELS[collection]} içine taşındı`, {
      tone: "ok",
      action: { label: "Geri al", run: () => move.mutate({ id: selectedId, collection: "inbox" }) },
    });
    restoreIndex.current = index;
  }

  /** Liste uzerindeki kisayollar. Kart odaktayken calisir. */
  function onListKeyDown(event: React.KeyboardEvent<HTMLElement>) {
    if (!selectedId) return;
    const index = data.findIndex((b) => b.id === selectedId);
    const key = event.key;

    if (key === "ArrowDown" || key === "j") { event.preventDefault(); focusCard(index + 1); return; }
    if (key === "ArrowUp"   || key === "k") { event.preventDefault(); focusCard(index - 1); return; }

    const slot = Number(key);
    if (Number.isInteger(slot) && slot >= 1 && slot <= TARGETS.length) {
      event.preventDefault();
      moveSelected(TARGETS[slot - 1]);
    }
  }

  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Kaynaklar" title="Gelen Kutusu" />
      <Toolbar><QuickCapture /></Toolbar>

      <DndContext
        sensors={sensors}
        onDragStart={(e) => setDragging(data.find((b) => b.id === e.active.id) ?? null)}
        onDragCancel={() => setDragging(null)}
        onDragEnd={onDragEnd}
      >
        <div className="grid min-w-0 divide-y divide-subtle border-y border-subtle lg:grid-cols-[minmax(0,1fr)_240px] lg:divide-x lg:divide-y-0">
          <div className="min-w-0 py-3 lg:pr-4">
            <div className="mb-2 flex items-center justify-between"><span className="label-caps">Bekleyenler</span><span className="text-meta text-muted">{data.length} kayıt</span></div>
            {isLoading ? (
              <p className="text-body text-muted">Yükleniyor…</p>
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
                    registerRef={(node) => {
                      if (node) cardRefs.current.set(bookmark.id, node);
                      else cardRefs.current.delete(bookmark.id);
                    }}
                  />
                ))}
              </RowList>
            )}
          </div>

          <Section
            title="Taşı"
            action={<span className="text-meta text-muted">{selectedId ? "1 kart seçili" : "önce kart seç"}</span>}
            className="h-fit py-3 lg:pl-4"
          >
            <div className="space-y-2">
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
            <dl className="mt-4 space-y-1.5 border-t border-subtle pt-3 text-meta text-muted">
              {[
                ["↑ ↓", "kartlar arasında gez"],
                [`1–${TARGETS.length}`, "seçili kartı taşı"],
              ].map(([keys, what]) => (
                <div key={keys} className="flex items-center gap-2">
                  <dt><Kbd>{keys}</Kbd></dt>
                  <dd>{what}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-3 text-meta text-muted">
              Taşıma tek UPDATE’tir; link ve event kayıtları kopmaz.
            </p>
          </Section>
        </div>

        <DragOverlay>
          {dragging && (
            <div className="rounded border border-accent-border bg-surface px-3 py-2 text-body shadow-xl">
              {dragging.title || dragging.url}
            </div>
          )}
        </DragOverlay>
      </DndContext>
    </PageFrame>
  );
}
