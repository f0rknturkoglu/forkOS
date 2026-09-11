import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  Clock,
  Download,
  ExternalLink,
  LayoutGrid,
  List,
  Star,
  StickyNote,
  Trash2,
  Upload,
} from "lucide-react";
import { api, qs } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import {
  Button,
  Checkbox,
  Chip,
  Empty,
  FilterChip,
  IconButton,
  Input,
  PageFrame,
  RowList,
  Select,
  SkeletonRows,
  cx,
  hostOf,
  relativeTime,
} from "@/core/ui";
import {
  Workspace,
  WorkspaceInspectorContent,
  WorkspacePaneHeader,
  WorkspaceRailButton,
  WorkspaceRailContent,
  WorkspaceRailGroup,
  WorkspaceScrollArea,
} from "@/core/workspace/Workspace";
import { useDebounced, useOnline } from "@/lib/hooks";
import { useHashRoute } from "@/app/router";
import { RelatedPanel } from "@/core/RelatedPanel";
import { SavedViewPicker } from "@/core/SavedViewPicker";
import { COLLECTION_LABELS, COLLECTIONS } from "@/core/types";
import type { Bookmark, BookmarkStats, Collection, TagCount } from "@/core/types";
import { BookmarkCard } from "./BookmarkCard";
import { BookmarkReaderModal } from "./BookmarkReaderModal";
import { BookmarkImportModal } from "./BookmarkImportModal";

interface Filter {
  collection?: Collection | "";
  read_status?: string;
  favorite?: boolean;
  source?: string;
  tag?: string;
  q?: string;
}

const READ_STATUSES = ["unread", "reading", "read"] as const;
const READ_STATUS_LABELS: Record<(typeof READ_STATUSES)[number], string> = {
  unread: "Okunmadi",
  reading: "Okuyor",
  read: "Okundu",
};

function safeGetStorage(key: string, fallback: string): string {
  try {
    if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
      return localStorage.getItem(key) || fallback;
    }
  } catch {
    // ignore
  }
  return fallback;
}

function safeSetStorage(key: string, value: string): void {
  try {
    if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
      localStorage.setItem(key, value);
    }
  } catch {
    // ignore
  }
}

function BookmarkRow({
  bookmark,
  focused,
  selected,
  onToggleSelect,
  onOpenReader,
}: {
  bookmark: Bookmark;
  focused: boolean;
  selected: boolean;
  onToggleSelect: () => void;
  onOpenReader: () => void;
}) {
  const online = useOnline();
  const refresh = () => invalidateAfter("bookmark.write");

  const patch = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.patch(`/bookmarks/${bookmark.id}`, body),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: () => api.del(`/bookmarks/${bookmark.id}`),
    onSuccess: refresh,
  });

  const isFavorite = bookmark.favorite;

  return (
    <li
      id={bookmark.id}
      className={cx(
        "group min-w-0 px-2 py-3 transition hover:bg-surface-hover/70 rounded-control",
        focused ? "bg-accent-surface ring-1 ring-inset ring-accent" : "",
        selected ? "bg-accent-surface/50" : "",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0 flex-1">
          <div className="pt-0.5 shrink-0">
            <Checkbox checked={selected} onChange={onToggleSelect} />
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-baseline gap-2">
              <button
                type="button"
                onClick={onOpenReader}
                className={cx(
                  "text-left font-medium truncate text-body hover:underline focus:outline-none transition-colors",
                  bookmark.read_status === "read" ? "text-muted" : "text-primary hover:text-accent",
                )}
              >
                {bookmark.title || bookmark.url}
              </button>
            </div>

            <div className="mt-1 flex flex-wrap items-center gap-2 text-meta text-muted">
              <span className="font-mono">{hostOf(bookmark.url)}</span>
              <span>·</span>
              <span>{relativeTime(bookmark.saved_at)}</span>
              <Chip>{COLLECTION_LABELS[bookmark.collection] || bookmark.collection}</Chip>
              {bookmark.read_status !== "unread" && <Chip tone="ok">{bookmark.read_status}</Chip>}
              {Boolean(bookmark.reading_time_min) && (
                <Chip tone="accent">
                  <Clock size={10} className="mr-1 inline" />
                  {bookmark.reading_time_min} dk
                </Chip>
              )}
              {Boolean(bookmark.scroll_progress && bookmark.scroll_progress > 0) && (
                <span className="text-accent font-sans">%{bookmark.scroll_progress} okundu</span>
              )}
              {bookmark.is_duplicate && (
                <Chip tone="warn">Zaten kayitli: {bookmark.existing_collection || "kutuphane"}</Chip>
              )}
              {bookmark.queue_kind && (
                <a href="#/learning" title="Ogrenme kuyrugunda" className="inline-flex">
                  <Chip tone="accent">Ogrenme kuyrugu</Chip>
                </a>
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
          </div>
        </div>

        {/* Aksiyonlar */}
        <div className="flex flex-wrap items-center justify-end gap-1 shrink-0">
          <IconButton
            title={isFavorite ? "Favoriden cikar" : "Favori yap"}
            disabled={!online}
            onClick={() => patch.mutate({ is_favorite: !isFavorite, favorite: !isFavorite })}
          >
            <Star size={15} className={isFavorite ? "fill-accent text-accent" : ""} />
          </IconButton>

          <Button
            size="sm"
            disabled={!online}
            title={bookmark.read_status === "read" ? "Okunmadi isaretle" : "Okundu isaretle"}
            onClick={() => patch.mutate({ read_status: bookmark.read_status === "read" ? "unread" : "read" })}
          >
            {bookmark.read_status === "read" ? "Okunmadi" : "Okundu"}
          </Button>

          <Select
            disabled={!online}
            ariaLabel="Koleksiyona tasi"
            value={bookmark.collection}
            onChange={(v) => patch.mutate({ collection: v })}
          >
            {COLLECTIONS.map((c) => (
              <option key={c} value={c}>
                {COLLECTION_LABELS[c]}
              </option>
            ))}
          </Select>

          <a
            href={bookmark.url}
            target="_blank"
            rel="noreferrer"
            title="Orijinal sayfayi ac"
            className="inline-flex h-8 w-8 items-center justify-center rounded-control text-muted hover:bg-surface-hover hover:text-primary transition"
          >
            <ExternalLink size={14} />
          </a>

          <IconButton title="Odak Okuma Modunda Ac" onClick={onOpenReader}>
            <BookOpen size={14} />
          </IconButton>

          <IconButton title="Sil" tone="danger" disabled={!online} onClick={() => remove.mutate()}>
            <Trash2 size={15} />
          </IconButton>
        </div>
      </div>
    </li>
  );
}

export function BookmarksPage() {
  const { params } = useHashRoute();
  const focus = params.get("focus");

  const [filter, setFilter] = useState<Filter>({ collection: "" });
  const [search, setSearch] = useState("");
  const q = useDebounced(search, 250);

  const [viewMode, setViewMode] = useState<"grid" | "list">(() => {
    return safeGetStorage("forkos_bookmark_view", "grid") as "grid" | "list";
  });

  const [activeReaderBookmark, setActiveReaderBookmark] = useState<Bookmark | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);

  useEffect(() => {
    safeSetStorage("forkos_bookmark_view", viewMode);
  }, [viewMode]);

  useEffect(() => {
    if (focus) document.getElementById(focus)?.scrollIntoView({ block: "center" });
  }, [focus]);

  const query = { ...filter, q, limit: 100 } as Record<string, string | number | boolean>;
  const { data = [], isLoading } = useQuery({
    queryKey: ["bookmarks", "library", query],
    queryFn: () => api.get<Bookmark[]>(`/bookmarks${qs(query)}`),
  });

  const { data: stats } = useQuery({
    queryKey: ["bookmark-stats"],
    queryFn: () => api.get<BookmarkStats>("/bookmarks/stats"),
  });

  const { data: tags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: () => api.get<TagCount[]>("/tags"),
  });
  const online = useOnline();

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === data.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(data.map((b) => b.id)));
    }
  };

  const bulkAction = useMutation({
    mutationFn: (body: {
      bookmark_ids: string[];
      action: "move" | "delete" | "tag" | "read_status";
      collection?: string;
      tags?: string[];
      read_status?: string;
    }) => api.post("/bookmarks/bulk-action", body),
    onSuccess: () => {
      setSelectedIds(new Set());
      invalidateAfter("bookmark.write");
    },
  });

  const handleExport = () => {
    const exportPath = "/bookmarks/export";
    const a = document.createElement("a");
    a.href = `/api${exportPath}`;
    a.download = "forkos-bookmarks.html";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  function applyView(raw: unknown) {
    const d = (raw ?? {}) as Record<string, unknown>;
    const next: Filter = { collection: "" };
    if (typeof d.collection === "string") next.collection = d.collection as Collection;
    if (typeof d.read_status === "string") next.read_status = d.read_status;
    if (d.favorite === true) next.favorite = true;
    if (typeof d.source === "string") next.source = d.source;
    if (typeof d.tag === "string") next.tag = d.tag;
    setFilter(next);
    setSearch("");
  }

  return (
    <PageFrame className="py-3">
      <Workspace
        rail={
          <WorkspaceRailContent>
            <WorkspaceRailGroup label="Koleksiyonlar">
              <WorkspaceRailButton
                label="Tumu"
                count={stats?.total}
                active={!filter.collection}
                onClick={() => setFilter({ ...filter, collection: "" })}
              />
              {COLLECTIONS.map((collection) => (
                <WorkspaceRailButton
                  key={collection}
                  label={COLLECTION_LABELS[collection]}
                  count={stats?.collections.find((item) => item.collection === collection)?.count}
                  active={filter.collection === collection}
                  onClick={() =>
                    setFilter({ ...filter, collection: filter.collection === collection ? "" : collection })
                  }
                />
              ))}
            </WorkspaceRailGroup>

            <WorkspaceRailGroup label="Okuma durumu">
              <WorkspaceRailButton
                label="Hepsi"
                active={!filter.read_status}
                onClick={() => setFilter({ ...filter, read_status: undefined })}
              />
              {READ_STATUSES.map((status) => (
                <WorkspaceRailButton
                  key={status}
                  label={READ_STATUS_LABELS[status]}
                  active={filter.read_status === status}
                  onClick={() =>
                    setFilter({ ...filter, read_status: filter.read_status === status ? undefined : status })
                  }
                />
              ))}
            </WorkspaceRailGroup>

            <WorkspaceRailGroup label="Etiketler" hint={tags.length}>
              {tags.length === 0 ? (
                <p className="px-2 py-1 text-meta text-muted">Henuz etiket yok.</p>
              ) : (
                tags
                  .slice(0, 20)
                  .map((tag) => (
                    <WorkspaceRailButton
                      key={tag.name}
                      label={`#${tag.name}`}
                      count={tag.count}
                      active={filter.tag === tag.name}
                      onClick={() => setFilter({ ...filter, tag: filter.tag === tag.name ? undefined : tag.name })}
                    />
                  ))
              )}
            </WorkspaceRailGroup>

            <SavedViewPicker module="bookmark" filters={filter} onApply={applyView} />
          </WorkspaceRailContent>
        }
        inspector={
          focus ? (
            <WorkspaceInspectorContent title="Bagli kayitlar">
              <RelatedPanel entityId={focus} title="Iliskiler" />
            </WorkspaceInspectorContent>
          ) : undefined
        }
      >
        <WorkspacePaneHeader title="Kutuphane" eyebrow="Yer Imleri" hint={`${data.length} kayit`}>
          <div className="flex flex-wrap items-center justify-between gap-2 w-full">
            <div className="flex flex-wrap items-center gap-2 flex-1 min-w-0">
              {data.length > 0 && (
                <Button size="sm" variant="ghost" onClick={selectAll} title="Tumunu sec / secimi kaldir">
                  {selectedIds.size === data.length ? "Secimi Kaldir" : "Tumunu Sec"}
                </Button>
              )}
              <Input
                value={search}
                onChange={setSearch}
                placeholder="Ara (baslik, not, icerik)..."
                className="min-w-48 flex-1"
              />
              <FilterChip
                label="Favoriler"
                active={Boolean(filter.favorite)}
                onClick={() => setFilter({ ...filter, favorite: filter.favorite ? undefined : true })}
              />
              <FilterChip
                label="RSS"
                active={filter.source === "rss"}
                onClick={() => setFilter({ ...filter, source: filter.source === "rss" ? undefined : "rss" })}
              />
              {filter.tag && (
                <FilterChip
                  label={`#${filter.tag} x`}
                  active
                  onClick={() => setFilter({ ...filter, tag: undefined })}
                />
              )}
            </div>

            {/* Sag Taraf: Gorunum Gecisi ve Ice/Disa Aktar */}
            <div className="flex items-center gap-1.5 shrink-0">
              {/* Grid / List Gecisi */}
              <div className="flex items-center rounded-control border border-subtle bg-surface-sunken p-0.5">
                <IconButton
                  title="Kart Izgarasi (Grid)"
                  onClick={() => setViewMode("grid")}
                  className={cx(viewMode === "grid" ? "bg-surface text-primary shadow-xs" : "text-muted")}
                >
                  <LayoutGrid size={15} />
                </IconButton>
                <IconButton
                  title="Kompakt Liste (List)"
                  onClick={() => setViewMode("list")}
                  className={cx(viewMode === "list" ? "bg-surface text-primary shadow-xs" : "text-muted")}
                >
                  <List size={15} />
                </IconButton>
              </div>

              <Button
                size="sm"
                variant="ghost"
                title="Yer imlerini ice aktar (Netscape / Pocket)"
                onClick={() => setImportModalOpen(true)}
              >
                <Upload size={14} />
                <span>Ice Aktar</span>
              </Button>

              <Button size="sm" variant="ghost" title="Kutuphaneyi HTML olarak indir" onClick={handleExport}>
                <Download size={14} />
                <span>Disa Aktar</span>
              </Button>
            </div>
          </div>
        </WorkspacePaneHeader>

        <WorkspaceScrollArea className="relative p-3">
          {selectedIds.size > 0 && (
            <div className="sticky top-0 z-sticky mb-3 flex flex-wrap items-center justify-between gap-2 rounded-panel border border-subtle bg-surface-raised p-2.5 shadow-md">
              <div className="flex items-center gap-2 text-meta text-primary font-medium">
                <span>{selectedIds.size} kayit secildi</span>
                <Button size="sm" variant="ghost" onClick={() => setSelectedIds(new Set())}>
                  Temizle
                </Button>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                <Button
                  size="sm"
                  disabled={!online || bulkAction.isPending}
                  onClick={() =>
                    bulkAction.mutate({
                      bookmark_ids: Array.from(selectedIds),
                      action: "move",
                      collection: "archive",
                    })
                  }
                >
                  Arsivle
                </Button>
                <Button
                  size="sm"
                  disabled={!online || bulkAction.isPending}
                  onClick={() =>
                    bulkAction.mutate({
                      bookmark_ids: Array.from(selectedIds),
                      action: "move",
                      collection: "read_later",
                    })
                  }
                >
                  Sonra Oku
                </Button>
                <Button
                  size="sm"
                  disabled={!online || bulkAction.isPending}
                  onClick={() =>
                    bulkAction.mutate({
                      bookmark_ids: Array.from(selectedIds),
                      action: "read_status",
                      read_status: "read",
                    })
                  }
                >
                  Okundu Yap
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  disabled={!online || bulkAction.isPending}
                  onClick={() => {
                    if (window.confirm(`${selectedIds.size} kayit silinsin mi?`)) {
                      bulkAction.mutate({
                        bookmark_ids: Array.from(selectedIds),
                        action: "delete",
                      });
                    }
                  }}
                >
                  Sil
                </Button>
              </div>
            </div>
          )}

          {isLoading ? (
            <SkeletonRows rows={8} />
          ) : data.length === 0 ? (
            <Empty>Bu filtreye uyan kayit yok.</Empty>
          ) : viewMode === "grid" ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3.5">
              {data.map((bookmark) => (
                <BookmarkCard
                  key={bookmark.id}
                  bookmark={bookmark}
                  selected={selectedIds.has(bookmark.id)}
                  onToggleSelect={() => toggleSelect(bookmark.id)}
                  onOpenReader={() => setActiveReaderBookmark(bookmark)}
                />
              ))}
            </div>
          ) : (
            <RowList as="ul">
              {data.map((bookmark) => (
                <BookmarkRow
                  key={bookmark.id}
                  bookmark={bookmark}
                  focused={focus === bookmark.id}
                  selected={selectedIds.has(bookmark.id)}
                  onToggleSelect={() => toggleSelect(bookmark.id)}
                  onOpenReader={() => setActiveReaderBookmark(bookmark)}
                />
              ))}
            </RowList>
          )}
        </WorkspaceScrollArea>
      </Workspace>

      {/* Odak Okuma Modali */}
      <BookmarkReaderModal
        open={Boolean(activeReaderBookmark)}
        bookmark={activeReaderBookmark}
        onClose={() => setActiveReaderBookmark(null)}
      />

      {/* Ice Aktar Modali */}
      <BookmarkImportModal open={importModalOpen} onClose={() => setImportModalOpen(false)} />
    </PageFrame>
  );
}
