import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Star, Trash2 } from "lucide-react";
import { api, qs } from "@/core/api";
import {Button, Chip, Empty, IconButton, Input, PageFrame, PageHeader, RowList, Section, Select, Toolbar, cx, hostOf, relativeTime} from "@/core/ui";
import { useDebounced, useInvalidate, useOnline } from "@/lib/hooks";
import { useHashRoute } from "@/app/router";
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

/** Basit tek secimli filtre cipi. Sayi verilirse saga yazar (sayaçsız da olur). */
function FilterChip({
  label, count, active, onClick,
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
  const invalidate = useInvalidate();
  const refresh = () => invalidate("bookmarks", "bookmark-stats", "tags", "activity");

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
            {bookmark.tags.map((tag) => (
              <Chip key={tag}>#{tag}</Chip>
            ))}
          </div>
          {bookmark.note && (
            <p className="mt-2 text-meta text-secondary">{bookmark.note}</p>
          )}
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
            onClick={() =>
              patch.mutate({ read_status: bookmark.read_status === "read" ? "unread" : "read" })
            }
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
                onClick={() =>
                  setFilter({ ...filter, collection: filter.collection === c ? "" : c })
                }
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
                onClick={() =>
                  setFilter({ ...filter, read_status: filter.read_status === s ? undefined : s })
                }
              />
            ))}
          </div>
        </Toolbar>

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
