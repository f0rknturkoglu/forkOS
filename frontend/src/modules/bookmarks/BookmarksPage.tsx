import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Star, Trash2, X } from "lucide-react";
import { api, qs } from "@/core/api";
import {
  Button,
  Chip,
  Empty,
  IconButton,
  Input,
  PageFrame,
  PageHeader,
  RowList,
  Section,
  Select,
  Toolbar,
  cx,
  hostOf,
  relativeTime,
} from "@/core/ui";
import { useDebounced, useOnline } from "@/lib/hooks";
import { useHashRoute } from "@/app/router";
import { COLLECTION_LABELS, COLLECTIONS } from "@/core/types";
import type { Bookmark, BookmarkStats, Collection, SavedView, TagCount } from "@/core/types";

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
/** Filtre aktif mi? Kayıtlı görünüm çubuğu ve kaydet düğmesi buna bağlı. */
function filterActive(f: Filter): boolean {
  return Boolean(f.collection || f.read_status || f.favorite || f.source || f.tag);
}

/** Kaydedilecek filtre: boş/undefined alanlar atılır (view.filter DSL'i). */
function cleanFilter(f: Filter): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  if (f.collection) out.collection = f.collection;
  if (f.read_status) out.read_status = f.read_status;
  if (f.favorite) out.favorite = true;
  if (f.source) out.source = f.source;
  if (f.tag) out.tag = f.tag;
  return out;
}

/** Görünüm adı -- aktif filtre parçalarından türetilir. */
function viewName(f: Filter): string {
  const parts: string[] = [];
  if (f.collection) parts.push(COLLECTION_LABELS[f.collection]);
  if (f.read_status) parts.push(READ_STATUS_LABELS[f.read_status as (typeof READ_STATUSES)[number]]);
  if (f.favorite) parts.push("Favoriler");
  if (f.source) parts.push("RSS");
  if (f.tag) parts.push(`#${f.tag}`);
  return parts.join(" + ") || "Filtre";
}

/** Basit tek secimli filtre cipi. Sayi verilirse saga yazar (sayaçsız da olur). */
function FilterChip({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count?: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cx(
        "flex h-8 items-center gap-2 rounded-control border px-3 text-meta transition",
        active
          ? "border-accent bg-accent-surface font-medium text-accent"
          : "border-subtle bg-surface text-secondary hover:bg-surface-hover hover:text-primary",
      )}
    >
      <span>{label}</span>
      {count !== undefined && (
        <span className={cx("numeral text-meta", active ? "text-accent" : "text-muted")}>{count}</span>
      )}
    </button>
  );
}

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
  const { data: views = [] } = useQuery({
    queryKey: ["saved-views", "bookmarks"],
    queryFn: () => api.get<SavedView[]>("/views?module=bookmarks"),
  });
  const saveView = useMutation({
    mutationFn: () =>
      api.post<SavedView>("/views", { name: viewName(filter), module: "bookmarks", filter: cleanFilter(filter) }),
    onSuccess: () => invalidateAfter("settings.write"),
  });
  const removeView = useMutation({
    mutationFn: (id: string) => api.del(`/views/${id}`),
    onSuccess: () => invalidateAfter("settings.write"),
  });

  /** Kayıtlı görünümü uygula: temiz filtre + aramayı sıfırla. */
  function applyView(v: SavedView) {
    const next: Filter = { collection: "" };
    const raw = v.filter ?? {};
    if (typeof raw.collection === "string") next.collection = raw.collection as Collection;
    if (typeof raw.read_status === "string") next.read_status = raw.read_status;
    if (raw.favorite === true) next.favorite = true;
    if (typeof raw.source === "string") next.source = raw.source;
    if (typeof raw.tag === "string") next.tag = raw.tag;
    setFilter(next);
    setSearch("");
  }
  const currentViewJson = JSON.stringify(cleanFilter(filter));

  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Kaynaklar" title="Yer İmleri" />
      <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_260px]">
        <div className="min-w-0">
          {/* ── Filtre sırası: arama + chip'ler ── */}
          <Toolbar className="mb-4">
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
                <FilterChip
                  label={`#${filter.tag} ✕`}
                  active
                  onClick={() => setFilter({ ...filter, tag: undefined })}
                />
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Koleksiyona göre filtrele">
              <FilterChip
                label="Tümü"
                count={stats?.total}
                active={!filter.collection}
                onClick={() => setFilter({ ...filter, collection: "" })}
              />
              {COLLECTIONS.map((c) => (
                <FilterChip
                  key={c}
                  label={COLLECTION_LABELS[c]}
                  count={stats?.collections.find((x) => x.collection === c)?.count}
                  active={filter.collection === c}
                  onClick={() => setFilter({ ...filter, collection: filter.collection === c ? "" : c })}
                />
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Okuma durumuna göre filtrele">
              <FilterChip
                label="Hepsi"
                active={!filter.read_status}
                onClick={() => setFilter({ ...filter, read_status: undefined })}
              />
              {READ_STATUSES.map((s) => (
                <FilterChip
                  key={s}
                  label={READ_STATUS_LABELS[s]}
                  active={filter.read_status === s}
                  onClick={() => setFilter({ ...filter, read_status: filter.read_status === s ? undefined : s })}
                />
              ))}
            </div>
          </Toolbar>
          {(views.length > 0 || filterActive(filter)) && (
            <div className="mb-4 flex flex-wrap items-center gap-2 rounded-card border border-subtle bg-surface px-3 py-2">
              <Star size={13} className="text-icon" />
              <span className="text-meta text-muted">Görünümler</span>
              {views.map((v) => (
                <span key={v.id} className="flex items-center gap-0.5">
                  <button
                    type="button"
                    onClick={() => applyView(v)}
                    className={cx(
                      "h-7 rounded-control border px-2 text-meta transition",
                      JSON.stringify(v.filter ?? {}) === currentViewJson
                        ? "border-accent bg-accent-surface font-medium text-accent"
                        : "border-subtle bg-surface text-secondary hover:bg-surface-hover hover:text-primary",
                    )}
                  >
                    {v.name}
                  </button>
                  <button
                    type="button"
                    title="Görünümü sil"
                    aria-label={`"${v.name}" görünümünü sil`}
                    onClick={() => removeView.mutate(v.id)}
                    className="flex h-7 w-6 items-center justify-center rounded-control text-muted opacity-60 transition hover:bg-surface-sunken hover:text-danger"
                  >
                    <X size={12} />
                  </button>
                </span>
              ))}
              {filterActive(filter) && !views.some((v) => JSON.stringify(v.filter ?? {}) === currentViewJson) && (
                <Button size="sm" disabled={!online || saveView.isPending} onClick={() => saveView.mutate()}>
                  Görünümü kaydet
                </Button>
              )}
            </div>
          )}

          {isLoading ? (
            <p className="text-body text-muted">Yükleniyor…</p>
          ) : data.length === 0 ? (
            <Empty>Bu filtreye uyan kayıt yok.</Empty>
          ) : (
            <RowList as="ul">
              {data.map((bookmark) => (
                <BookmarkRow key={bookmark.id} bookmark={bookmark} focused={focus === bookmark.id} />
              ))}
            </RowList>
          )}
        </div>

        <aside className="space-y-4">
          <Section title="Etiketler">
            {tags.length === 0 ? (
              <Empty>Etiket yok.</Empty>
            ) : (
              <div className="flex flex-wrap gap-1">
                {tags.slice(0, 40).map((tag) => (
                  <button
                    key={tag.name}
                    onClick={() => setFilter({ ...filter, tag: tag.name })}
                    className="rounded border border-subtle px-1.5 py-0.5 text-meta text-secondary hover:border-strong hover:text-primary"
                  >
                    #{tag.name} <span className="text-muted">{tag.count}</span>
                  </button>
                ))}
              </div>
            )}
          </Section>
        </aside>
      </div>
    </PageFrame>
  );
}
