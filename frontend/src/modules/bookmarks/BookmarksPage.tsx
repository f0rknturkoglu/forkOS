import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Star, Trash2 } from "lucide-react";
import { api, qs } from "@/core/api";
import {
  Button,
  Chip,
  Empty,
  FilterChip,
  IconButton,
  Input,
  PageFrame,
  RowList,
  Select,
  cx,
  hostOf,
  relativeTime,
  SkeletonRows,
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

interface Filter {
  collection?: Collection | "";
  read_status?: string;
  favorite?: boolean;
  source?: string;
  tag?: string;
  q?: string;
}

/** Okuma durumu chipleri — degerler /bookmarks filtresiyle birebir. */
const READ_STATUSES = ["unread", "reading", "read"] as const;
const READ_STATUS_LABELS: Record<(typeof READ_STATUSES)[number], string> = {
  unread: "Okunmadı",
  reading: "Okuyor",
  read: "Okundu",
};

function BookmarkRow({ bookmark, focused }: { bookmark: Bookmark; focused: boolean }) {
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

  return (
    <li
      id={bookmark.id}
      className={cx(
        "group min-w-0 px-1 py-3 transition hover:bg-surface-hover",
        focused ? "bg-accent-surface ring-1 ring-inset ring-accent" : "",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <a
            href={bookmark.url}
            target="_blank"
            rel="noreferrer"
            className={cx(
              "block truncate text-body hover:underline",
              bookmark.read_status === "read" ? "text-muted" : "text-primary",
            )}
          >
            {bookmark.title || bookmark.url}
          </a>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-meta text-muted">
            <span>{hostOf(bookmark.url)}</span>
            <span>·</span>
            <span>{relativeTime(bookmark.saved_at)}</span>
            <Chip>{COLLECTION_LABELS[bookmark.collection]}</Chip>
            {bookmark.read_status !== "unread" && <Chip tone="ok">{bookmark.read_status}</Chip>}
            {bookmark.queue_kind && (
              <a href="#/learning" title="Öğrenme kuyruğunda" className="inline-flex">
                <Chip tone="accent">Öğrenme kuyruğu</Chip>
              </a>
            )}
            {bookmark.tags.map((tag) => (
              <Chip key={tag}>#{tag}</Chip>
            ))}
          </div>
          {bookmark.note && <p className="mt-2 text-meta text-secondary">{bookmark.note}</p>}
        </div>

        {/* Aksiyonlar tek boyutta: ikon butonlar 32px, metin buton h-8; select standart h-9. */}
        <div className="flex flex-wrap items-center justify-end gap-1">
          <IconButton
            title={bookmark.favorite ? "Favoriden çıkar" : "Favori yap"}
            disabled={!online}
            onClick={() => patch.mutate({ favorite: !bookmark.favorite })}
          >
            <Star size={15} className={bookmark.favorite ? "fill-current text-accent" : ""} />
          </IconButton>
          <Button
            size="sm"
            disabled={!online}
            title={bookmark.read_status === "read" ? "Okunmadı işaretle" : "Okundu işaretle"}
            onClick={() => patch.mutate({ read_status: bookmark.read_status === "read" ? "unread" : "read" })}
          >
            {bookmark.read_status === "read" ? "Okunmadı" : "Okundu"}
          </Button>
          <Select
            disabled={!online}
            ariaLabel="Koleksiyona taşı"
            value={bookmark.collection}
            onChange={(v) => patch.mutate({ collection: v })}
          >
            {COLLECTIONS.map((c) => (
              <option key={c} value={c}>
                {COLLECTION_LABELS[c]}
              </option>
            ))}
          </Select>
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

  useEffect(() => {
    if (focus) document.getElementById(focus)?.scrollIntoView({ block: "center" });
  }, [focus]);

  const query = { ...filter, q, limit: 100 } as Record<string, string | number | boolean>;
  const { data = [], isLoading } = useQuery({
    queryKey: ["bookmarks", "library", query],
    queryFn: () => api.get<Bookmark[]>(`/bookmarks${qs(query)}`),
  });

  /** Chip sayilari Inbox ile ayni query key'i paylasir — tek istek, paylasilan cache. */
  const { data: stats } = useQuery({
    queryKey: ["bookmark-stats"],
    queryFn: () => api.get<BookmarkStats>("/bookmarks/stats"),
  });

  const { data: tags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: () => api.get<TagCount[]>("/tags"),
  });
  const online = useOnline();

  /** Kayıtlı görünümü uygula: tanınan anahtarları filtreye aktar, gerisini yok say. */
  function applyView(raw: unknown) {
    const data = (raw ?? {}) as Record<string, unknown>;
    const next: Filter = { collection: "" };
    if (typeof data.collection === "string") next.collection = data.collection as Collection;
    if (typeof data.read_status === "string") next.read_status = data.read_status;
    if (data.favorite === true) next.favorite = true;
    if (typeof data.source === "string") next.source = data.source;
    if (typeof data.tag === "string") next.tag = data.tag;
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
                label="Tümü"
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
                <p className="px-2 py-1 text-meta text-muted">Henüz etiket yok.</p>
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
            <WorkspaceInspectorContent title="Bağlı kayıtlar">
              <RelatedPanel entityId={focus} title="İlişkiler" />
            </WorkspaceInspectorContent>
          ) : undefined
        }
      >
        <WorkspacePaneHeader title="Kütüphane" eyebrow="Yer İmleri" hint={`${data.length} kayıt`}>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              value={search}
              onChange={setSearch}
              placeholder="Ara (başlık, not, seçim)…"
              className="min-w-48 flex-1"
            />
            <FilterChip
              label="★ Favoriler"
              active={Boolean(filter.favorite)}
              onClick={() => setFilter({ ...filter, favorite: filter.favorite ? undefined : true })}
            />
            <FilterChip
              label="RSS"
              active={filter.source === "rss"}
              onClick={() => setFilter({ ...filter, source: filter.source === "rss" ? undefined : "rss" })}
            />
            {filter.tag && (
              <FilterChip label={`#${filter.tag} ✕`} active onClick={() => setFilter({ ...filter, tag: undefined })} />
            )}
          </div>
        </WorkspacePaneHeader>
        <WorkspaceScrollArea className="p-3">
          {isLoading ? (
            <SkeletonRows rows={8} />
          ) : data.length === 0 ? (
            <Empty>Bu filtreye uyan kayıt yok.</Empty>
          ) : (
            <RowList as="ul">
              {data.map((bookmark) => (
                <BookmarkRow key={bookmark.id} bookmark={bookmark} focused={focus === bookmark.id} />
              ))}
            </RowList>
          )}
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
