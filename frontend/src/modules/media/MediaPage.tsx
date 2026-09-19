import { invalidateAfter } from "@/core/invalidation";
import { MEDIA_COLLECTIONS_QUERY_KEY } from "./queries";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Plus, Search, SlidersHorizontal } from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import type { components } from "@/generated/api-schema";
import type { MediaItem, MediaPage as MediaPageResponse } from "@/core/types";
import { Button, Empty, FilterChip, Input, PageFrame, Skeleton, cx } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { useDebounced, useOnline } from "@/lib/hooks";
import {
  EMPTY_MEDIA_FILTERS,
  MediaActiveFilters,
  MediaFilterPanel,
  MediaPosterGrid,
  MediaPosterGridSkeleton,
  type MediaFilterValues,
  type MediaPosterItem,
} from "./MediaPosterGrid";
import { consumptionBody } from "./MediaProgressActions";
import { MediaSearchDialog } from "./MediaSearchDialog";
import { MediaSyncSummary } from "./MediaSyncSummary";
import { Cover, KIND_LABELS, KINDS, mediaCoverUrl, mediaProvider, progressPct, statusLabel } from "./shared";
import { MediaDetailPage } from "./MediaDetailPage";
import { MediaCollectionDetailPage } from "./MediaCollectionDetailPage";
import { MediaCollectionsPage } from "./MediaCollectionsPage";
import { MediaUpcomingPage } from "./MediaUpcomingPage";
import { MediaStatsPage } from "./MediaStatsPage";
import { MediaTrashPage } from "./MediaTrashPage";

type MediaCollection = components["schemas"]["MediaCollectionOut"];

type MediaFocusTarget = { focus?: () => void };

type MediaFocusElement = {
  querySelector: (selector: string) => MediaFocusTarget | null;
  scrollIntoView: (options: ScrollIntoViewOptions) => void;
};

type MediaFocusRoot = {
  getElementById: (id: string) => MediaFocusElement | null;
};

/** Legacy global-focus callers retain this DOM helper while the page routes new focus links to detail. */
export function receiveMediaFocus(
  itemId: string,
  root: MediaFocusRoot = document as unknown as MediaFocusRoot,
): boolean {
  const row = root.getElementById(`media-item-${itemId}`);
  if (!row) return false;
  row.scrollIntoView({ block: "center" });
  row.querySelector('[data-media-focus="true"]')?.focus?.();
  return true;
}

/**
 * Alt görünüm seçimi. Uygulama kabuğu her rota için kayıtlı elementi yeni
 * bağlar (App.tsx `routeForPath`); bu seçim yalnızca MediaPage'in doğrudan
 * çizildiği yerlerde (testler, widget'lar) doğru görünümü verir — bu yüzden
 * yalnızca ilk yüklemedeki yola göre sabitlenir, gezinme kabukta olur.
 */
function mediaViewForPath(path: string): ReactNode {
  if (path.startsWith("/media/")) {
    const rest = path.slice("/media/".length);
    if (rest === "collections") return <MediaCollectionsPage />;
    if (rest.startsWith("collections/")) return <MediaCollectionDetailPage />;
    if (rest === "upcoming") return <MediaUpcomingPage />;
    if (rest === "stats") return <MediaStatsPage />;
    if (rest === "trash") return <MediaTrashPage />;
    if (rest === "library") return <MediaLibraryView />;
    return <MediaDetailPage />;
  }
  return <MediaLibraryView />;
}

/* ══════════════════════════════════════════════════════════════════════
   URL <-> filtre sözleşmesi (geri/ileri tuşu ve doğrudan bağlantı çalışır)
   ══════════════════════════════════════════════════════════════════════ */

/** Filtre alanı -> URL parametresi adı. */
const FILTER_PARAMS: Record<keyof MediaFilterValues, string> = {
  kind: "kind",
  status: "status",
  provider: "provider",
  owned: "owned",
  favorite: "favorite",
  monitored: "monitored",
  collectionId: "collection_id",
  tag: "tag",
  sort: "sort",
};

function readFilters(params: URLSearchParams): MediaFilterValues {
  return {
    kind: params.get("kind") ?? "",
    status: params.get("status") ?? "",
    provider: params.get("provider") ?? "",
    owned: params.get("owned") === "true",
    favorite: params.get("favorite") === "true",
    monitored: params.get("monitored") === "true",
    collectionId: params.get("collection_id") ?? "",
    tag: params.get("tag") ?? "",
    sort: params.get("sort") ?? "",
  };
}

/** Boş değer parametreyi siler; bayraklar `true` yazılır (diğerleri korunur). */
function filterPatch(key: keyof MediaFilterValues, value: string | boolean): Record<string, string | null> {
  return { [FILTER_PARAMS[key]]: typeof value === "boolean" ? (value ? "true" : null) : value || null };
}

/** Kütüphane isteği; backend parametre adları tek yerde derlenir. */
function libraryPath(values: MediaFilterValues, query: string): string {
  const params = new URLSearchParams();
  if (values.kind) params.set("kind", values.kind);
  if (values.status) params.set("status", values.status);
  if (query) params.set("q", query);
  if (values.provider) params.set("provider", values.provider);
  if (values.collectionId) params.set("collection_id", values.collectionId);
  if (values.tag) params.set("tag", values.tag);
  if (values.owned) params.set("owned", "true");
  if (values.favorite) params.set("favorite", "true");
  if (values.monitored) params.set("monitored", "true");
  if (values.sort) params.set("sort", values.sort);
  const serialized = params.toString();
  return serialized ? `/media?${serialized}` : "/media";
}

/**
 * Yazarken yerel tutan, gecikmeden sonra URL'e yazan metin alanı. Her tuşta
 * istek atılmaz; URL dışarıdan değişirse (geri/ileri tuşu, bağlantı) taslak
 * ona uyar.
 */
function useUrlTextField(urlValue: string, commit: (value: string) => void, delay = 250) {
  const [draft, setDraft] = useState(urlValue);
  const debounced = useDebounced(draft.trim(), delay);
  const commitRef = useRef(commit);
  commitRef.current = commit;
  const committed = useRef(urlValue);

  useEffect(() => {
    setDraft(urlValue);
    committed.current = urlValue;
  }, [urlValue]);

  useEffect(() => {
    if (debounced === committed.current) return;
    committed.current = debounced;
    commitRef.current(debounced);
  }, [debounced]);

  return [draft, setDraft] as const;
}

/** "Devam et" şeridi: in_progress kayıtları, başlığın hemen altında. */
function MediaContinueStrip({ items }: { items: MediaPosterItem[] }) {
  return (
    <ul data-media-continue className="flex gap-2 overflow-x-auto pb-1">
      {items.map((item) => {
        const percent = progressPct(item);
        return (
          <li
            key={item.id}
            className="flex w-56 shrink-0 items-center gap-2 rounded-card border border-subtle bg-surface p-2 shadow-card"
          >
            <Cover url={mediaCoverUrl(item)} title={item.title} size="h-12 w-8" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-meta font-medium text-primary" title={item.title}>
                {item.title}
              </p>
              {percent !== null && <p className="numeral text-micro text-muted">%{percent}</p>}
            </div>
            <a
              href={`#/media/${encodeURIComponent(item.id)}`}
              aria-label={`${item.title} kaydına devam et`}
              className="shrink-0 text-meta text-accent transition hover:underline focus:outline-none focus:ring-1 focus:ring-accent"
            >
              Devam et
            </a>
          </li>
        );
      })}
    </ul>
  );
}

/** Kütüphane görünümü: URL filtreleri, sayfalama, arama ve filtre paneli. */
function MediaLibraryView() {
  const online = useOnline();
  const route = useHashRoute();
  const params = route.params;
  const values = readFilters(params);
  const query = params.get("q") ?? "";
  const searchOpen = params.get("search") === "1";

  const [filtersOpen, setFiltersOpen] = useState(false);
  const [extra, setExtra] = useState<MediaItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadMoreError, setLoadMoreError] = useState<string | null>(null);

  /** Mevcut parametreleri koruyarak yazar; diğer parametreler silinmez. */
  function writeParams(patch: Record<string, string | null>, replace = false) {
    const raw = location.hash.replace(/^#/, "") || "/";
    const queryIndex = raw.indexOf("?");
    const path = queryIndex === -1 ? raw : raw.slice(0, queryIndex);
    const next = new URLSearchParams(queryIndex === -1 ? "" : raw.slice(queryIndex + 1));
    for (const [key, value] of Object.entries(patch)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    const serialized = next.toString();
    navigate(serialized ? `${path}?${serialized}` : path, { replace });
  }

  const [draftQuery, setDraftQuery] = useUrlTextField(query, (value) => writeParams({ q: value || null }, true));

  const requestPath = libraryPath(values, query);
  // Devam şeridi ve "N devam ediyor" sayısı API `total` değerinden gelir.
  const continuing = useQuery({
    queryKey: ["media", "continue"],
    queryFn: () => api.get<MediaPageResponse>("/media?status=in_progress&limit=6"),
  });
  const library = useQuery({
    queryKey: ["media", "library", values, query],
    queryFn: () => api.get<MediaPageResponse>(requestPath),
  });
  const collections = useQuery({
    queryKey: MEDIA_COLLECTIONS_QUERY_KEY,
    queryFn: () => api.get<MediaCollection[]>("/media/collections"),
  });

  const refresh = () => invalidateAfter("media.write");
  const quick = useMutation({
    mutationFn: (item: Pick<MediaItem, "id" | "progress_measure">) =>
      api.post(`/media/${encodeURIComponent(item.id)}/consumptions`, consumptionBody("quick", item)),
    onSuccess: refresh,
  });
  const trash = useMutation({
    mutationFn: (item: Pick<MediaItem, "id">) => api.del(`/media/${encodeURIComponent(item.id)}`),
    onSuccess: refresh,
  });

  async function confirmTrash(item: Pick<MediaItem, "id" | "title">) {
    const confirmed = await confirmDialog({
      title: "Kayıt çöpe taşınsın mı?",
      body: (
        <>
          <strong className="font-medium text-primary">{item.title}</strong> çöp kutusundan geri yüklenebilir.
        </>
      ),
      confirmLabel: "Çöpe taşı",
      tone: "danger",
    });
    if (confirmed) trash.mutate(item);
  }

  const baseItems = library.data?.items ?? [];
  const items = [...baseItems, ...extra];
  const total = library.data?.total ?? 0;
  const continueCount = continuing.data?.total ?? 0;
  const continueItems = continuing.data?.items ?? [];
  const showContinue = values.status !== "in_progress" && continueItems.length > 0;

  // Sağlayıcı seçenekleri mevcut kayıtlardan türetilir (legacy `meta.source`
  // dahil); görülen kimlikler birikir, filtre daralsa da seçenek kaybolmaz.
  const providerKey = [...items, ...continueItems]
    .map((item) => mediaProvider(item))
    .filter((provider): provider is string => Boolean(provider))
    .join("\u0000");
  const [providers, setProviders] = useState<string[]>([]);
  useEffect(() => {
    if (!providerKey) return;
    const found = providerKey.split("\u0000");
    setProviders((previous) => {
      const merged = new Set(previous);
      found.forEach((provider) => merged.add(provider));
      return merged.size === previous.length ? previous : [...merged].sort();
    });
  }, [providerKey]);
  const providerOptions =
    values.provider && !providers.includes(values.provider) ? [values.provider, ...providers].sort() : providers;

  const collectionOptions = (collections.data ?? []).map(({ id, title }) => ({ id, title }));

  useEffect(() => {
    setExtra([]);
    setNextCursor(library.data?.next_cursor ?? null);
    setLoadMoreError(null);
  }, [requestPath, library.dataUpdatedAt]);

  async function loadMorePage() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    setLoadMoreError(null);
    try {
      const page = await api.get<MediaPageResponse>(
        `${requestPath}${requestPath.includes("?") ? "&" : "?"}cursor=${encodeURIComponent(nextCursor)}`,
      );
      setExtra((previous) => [...previous, ...page.items]);
      setNextCursor(page.next_cursor ?? null);
    } catch (loadError) {
      setLoadMoreError(loadError instanceof Error ? loadError.message : "Yüklenemedi");
    } finally {
      setLoadingMore(false);
    }
  }

  const applyFilters = (patch: Partial<MediaFilterValues>) => {
    const next: Record<string, string | null> = {};
    for (const [key, value] of Object.entries(patch) as [keyof MediaFilterValues, string | boolean][]) {
      Object.assign(next, filterPatch(key, value));
    }
    writeParams(next);
  };

  const removeFilter = (key: keyof MediaFilterValues | "q") => {
    if (key === "q") writeParams({ q: null });
    else writeParams(filterPatch(key, EMPTY_MEDIA_FILTERS[key]));
  };

  const filtered =
    Boolean(query) ||
    Boolean(values.kind) ||
    Boolean(values.status) ||
    Boolean(values.provider) ||
    Boolean(values.collectionId) ||
    Boolean(values.tag) ||
    Boolean(values.sort) ||
    values.owned ||
    values.favorite ||
    values.monitored;
  const summary = `${total} kayıt${continueCount > 0 ? ` · ${continueCount} devam ediyor` : ""}`;
  const selectedCollection = collectionOptions.find((collection) => collection.id === values.collectionId);

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Medya"
          title="Kütüphane"
          hint={library.isLoading ? "Yükleniyor…" : summary}
          action={
            <Button size="sm" variant="primary" disabled={!online} onClick={() => writeParams({ search: "1" })}>
              <Plus size={14} aria-hidden="true" /> Medya ekle
            </Button>
          }
        >
          <div role="group" aria-label="Tür filtresi" className="flex flex-wrap gap-1.5">
            <FilterChip label="Tümü" active={!values.kind} onClick={() => applyFilters({ kind: "" })} />
            {KINDS.map((kind) => (
              <FilterChip
                key={kind}
                label={KIND_LABELS[kind]}
                active={values.kind === kind}
                onClick={() => applyFilters({ kind: values.kind === kind ? "" : kind })}
              />
            ))}
          </div>
        </WorkspacePaneHeader>

        <WorkspaceScrollArea className="space-y-4 p-3">
          {values.status !== "in_progress" && continuing.isLoading && (
            <div role="status" aria-label="Devam edenler yükleniyor" className="flex gap-2">
              <span className="sr-only">Devam edenler yükleniyor…</span>
              <Skeleton className="h-16 w-56" />
              <Skeleton className="h-16 w-56" />
            </div>
          )}
          {showContinue && <MediaContinueStrip items={continueItems} />}

          <MediaActiveFilters
            values={values}
            query={query}
            collectionTitle={selectedCollection?.title}
            onRemove={removeFilter}
            onClear={() => navigate("/media")}
          />

          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-0 flex-1 sm:max-w-xs">
              <Search
                size={14}
                aria-hidden="true"
                className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted"
              />
              <Input
                value={draftQuery}
                onChange={setDraftQuery}
                ariaLabel="Kütüphanede ara"
                placeholder="Kütüphanede ara"
                type="search"
                className="w-full pl-8"
              />
            </div>
            <Button
              aria-expanded={filtersOpen}
              onClick={() => setFiltersOpen((open) => !open)}
              className={cx(filtersOpen && "border-accent text-accent")}
            >
              <SlidersHorizontal size={14} aria-hidden="true" />
              {filtersOpen ? "Filtreleri kapat" : "Filtreleri aç"}
            </Button>
            <div role="group" aria-label="Durum filtresi" className="flex flex-wrap gap-1.5">
              {["", "in_progress", "planned", "completed"].map((status) => (
                <FilterChip
                  key={status || "all"}
                  label={status ? statusLabel(values.kind, status) : "Tümü"}
                  active={values.status === status}
                  onClick={() => applyFilters({ status: values.status === status ? "" : status })}
                />
              ))}
            </div>
          </div>

          {filtersOpen && (
            <MediaFilterPanel
              values={values}
              onChange={applyFilters}
              providers={providerOptions}
              collections={collectionOptions}
            />
          )}

          {library.isLoading ? (
            <MediaPosterGridSkeleton />
          ) : library.isError ? (
            <Empty
              variant="page"
              action={
                <Button
                  size="sm"
                  disabled={library.isFetching}
                  onClick={() => {
                    void library.refetch();
                  }}
                >
                  Kütüphaneyi yeniden dene
                </Button>
              }
            >
              Kütüphane yüklenemedi: {library.error.message}
            </Empty>
          ) : items.length === 0 ? (
            filtered ? (
              <Empty
                variant="page"
                action={
                  <Button size="sm" onClick={() => navigate("/media")}>
                    Filtreleri temizle
                  </Button>
                }
              >
                Bu filtrelerle kayıt bulunamadı — filtreleri gevşetip yeniden dene.
              </Empty>
            ) : (
              <Empty
                variant="page"
                action={
                  <Button size="sm" variant="primary" disabled={!online} onClick={() => writeParams({ search: "1" })}>
                    Medya ekle
                  </Button>
                }
              >
                <span>Kütüphanen boş</span> — katalogdan ilk kaydını ekleyebilirsin.
              </Empty>
            )
          ) : (
            <MediaPosterGrid
              items={items}
              online={online}
              busy={library.isFetching}
              onQuick={(item) => quick.mutate(item)}
              onTrash={(item) => {
                void confirmTrash(item);
              }}
            />
          )}

          {nextCursor && (
            <div className="flex justify-center">
              <Button
                disabled={!online || loadingMore}
                onClick={() => {
                  void loadMorePage();
                }}
              >
                Daha fazla yükle
              </Button>
            </div>
          )}
          {loadMoreError && (
            <p role="alert" className="text-center text-meta text-danger">
              Daha fazla kayıt yüklenemedi: {loadMoreError}
            </p>
          )}

          {quick.error && (
            <p role="alert" className="text-meta text-danger">
              İlerleme kaydedilemedi: {quick.error.message}
            </p>
          )}
          {trash.error && (
            <p role="alert" className="text-meta text-danger">
              Kayıt çöpe taşınamadı: {trash.error.message}
            </p>
          )}

          <MediaSyncSummary online={online} />
        </WorkspaceScrollArea>
      </Workspace>

      <MediaSearchDialog
        open={searchOpen}
        onClose={() => writeParams({ search: null }, true)}
        initialKind={values.kind || undefined}
      />
    </PageFrame>
  );
}

export function MediaPage() {
  const route = useHashRoute();
  const focusId = route.params.get("focus");
  const [view] = useState(() => mediaViewForPath(route.path));

  useEffect(() => {
    if (focusId) navigate(`/media/${encodeURIComponent(focusId)}`, { replace: true });
  }, [focusId]);

  return view;
}
