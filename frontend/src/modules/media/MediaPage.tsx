import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Plus, SlidersHorizontal, X } from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { ApiError, api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import type {
  GlobalMetadataSearch,
  MediaItem,
  MediaPage as MediaPageResponse,
  MediaStats,
  MetadataResult,
} from "@/core/types";
import { Button, Chip, Empty, Input, PageFrame, RowList, cx } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { useOnline } from "@/lib/hooks";
import { MediaLibraryControls, MediaMetrics, MediaPosterGrid, MediaPosterGridSkeleton } from "./MediaPosterGrid";
import { consumptionBody } from "./MediaProgressActions";
import { MediaSearchComposer, providerCreateBody } from "./MediaSearchComposer";
import { MediaSyncSummary } from "./MediaSyncSummary";
import { Cover, KIND_LABELS, mediaCoverUrl, mediaProvider, providerChip, providerLabel } from "./shared";
import { MediaDetailPage } from "./MediaDetailPage";
import { MediaCollectionsPage } from "./MediaCollectionsPage";
import { MediaUpcomingPage } from "./MediaUpcomingPage";
import { MediaStatsPage } from "./MediaStatsPage";
import { MediaTrashPage } from "./MediaTrashPage";

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
function mediaViewForPath(path: string, initialParams: URLSearchParams): ReactNode {
  if (path.startsWith("/media/")) {
    const rest = path.slice("/media/".length);
    if (rest === "collections") return <MediaCollectionsPage />;
    if (rest === "upcoming") return <MediaUpcomingPage />;
    if (rest === "stats") return <MediaStatsPage />;
    if (rest === "trash") return <MediaTrashPage />;
    if (rest === "library" || rest.includes("/")) return <MediaLibraryView initialParams={initialParams} />;
    return <MediaDetailPage />;
  }
  return <MediaLibraryView initialParams={initialParams} />;
}

/** Provider arama paneli: "Medya ekle" ile açılır, tüm sağlayıcılarda arar. */
function ProviderSearchPanel({ online, onAdded }: { online: boolean; onAdded: () => void }) {
  const [term, setTerm] = useState("");
  const [results, setResults] = useState<MetadataResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duplicate, setDuplicate] = useState<{ term: string } | null>(null);
  const [addError, setAddError] = useState<string | null>(null);

  const add = useMutation({
    mutationFn: ({ hit, term: query }: { hit: MetadataResult; term: string }) =>
      api.post<MediaItem>("/media", providerCreateBody(hit)),
    onSuccess: () => {
      setDuplicate(null);
      setAddError(null);
      onAdded();
    },
    onError: (mutationError: Error, { term: query }: { hit: MetadataResult; term: string }) => {
      if (mutationError instanceof ApiError && mutationError.status === 409) {
        setDuplicate({ term: query });
        setAddError(null);
      } else {
        setAddError("Eklenemedi. Lütfen tekrar deneyin.");
      }
    },
  });

  async function runSearch() {
    const query = term.trim();
    if (query.length < 2) return;
    setSearching(true);
    setError(null);
    setDuplicate(null);
    setAddError(null);
    try {
      const data = await api.get<MetadataResult[] | GlobalMetadataSearch>(
        `/media/search/global?q=${encodeURIComponent(query)}`,
      );
      setResults(Array.isArray(data) ? data : (data.results ?? []));
    } catch {
      setError("Arama yapılamadı. Lütfen tekrar deneyin.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <section aria-label="Sağlayıcıda ara" className="space-y-3">
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-0 flex-1 sm:max-w-md">
          <Input
            value={term}
            onChange={setTerm}
            ariaLabel="Provider'da ara"
            placeholder="TMDB, AniList, OpenLibrary…"
            type="search"
            className="w-full"
          />
        </div>
        <Button
          variant="primary"
          disabled={!online || searching || term.trim().length < 2}
          onClick={() => {
            void runSearch();
          }}
        >
          Ara
        </Button>
      </div>

      {searching && (
        <p role="status" aria-live="polite" className="text-meta text-muted">
          Aranıyor…
        </p>
      )}
      {error && (
        <p role="alert" className="text-meta text-danger">
          {error}
        </p>
      )}
      {addError && (
        <p role="alert" className="text-meta text-danger">
          {addError}
        </p>
      )}

      {results && results.length === 0 && !searching && <Empty>Sağlayıcılarda sonuç bulunamadı.</Empty>}

      {results && results.length > 0 && (
        <RowList as="ul" className="mt-1">
          {results.map((hit) => {
            const coverUrl = mediaCoverUrl({
              cover_path: null,
              cover_url: hit.cover_url ?? null,
              meta: hit.meta,
            });
            return (
              <li key={`${hit.kind}:${hit.provider}:${hit.provider_id}`} className="flex items-center gap-3 py-2">
                <Cover url={coverUrl} title={hit.title} size="h-16 w-11" />
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-body font-medium text-primary">{hit.title}</h3>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5 text-meta text-muted">
                    <Chip identity={"kind-" + hit.kind} variant="outline" size="xs">
                      {KIND_LABELS[hit.kind] ?? hit.kind}
                    </Chip>
                    <span className={cx("rounded border px-1.5 py-0.5", providerChip(hit.provider))}>
                      {providerLabel(hit.provider)}
                    </span>
                    {(hit.subtitle || hit.year) && (
                      <span>
                        {hit.subtitle ?? ""}
                        {hit.year ? ` · ${hit.year}` : ""}
                      </span>
                    )}
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="primary"
                  disabled={!online || add.isPending}
                  onClick={() => add.mutate({ hit, term: term.trim() })}
                >
                  <Plus size={13} aria-hidden="true" /> {hit.title} kütüphaneye ekle
                </Button>
              </li>
            );
          })}
        </RowList>
      )}

      {duplicate && (
        <p role="status" aria-live="polite" className="text-meta text-muted">
          Bu kayıt kütüphanende zaten var.{" "}
          <a href={`#/media/library?q=${encodeURIComponent(duplicate.term)}`} className="text-accent hover:underline">
            Kütüphanede bul
          </a>
        </p>
      )}
    </section>
  );
}

/** Kütüphane görünümü: URL filtreleri, sayfalama, arama ve mobil filtre çekmecesi. */
function MediaLibraryView({ initialParams }: { initialParams: URLSearchParams }) {
  const online = useOnline();
  const [kind, setKind] = useState(initialParams.get("kind") ?? "");
  const [status, setStatus] = useState(initialParams.get("status") ?? "");
  const [query, setQuery] = useState(initialParams.get("q") ?? "");
  const [owned] = useState(initialParams.get("owned") ?? "");
  const [sort] = useState(initialParams.get("sort") ?? "");
  const [searchActive, setSearchActive] = useState(false);
  const [providerOpen, setProviderOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [extra, setExtra] = useState<MediaItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadMoreError, setLoadMoreError] = useState<string | null>(null);
  const queryDirty = useRef(false);

  const requestParams = new URLSearchParams();
  if (kind) requestParams.set("kind", kind);
  if (status) requestParams.set("status", status);
  if (query) requestParams.set("q", query);
  if (owned) requestParams.set("owned", owned);
  if (sort) requestParams.set("sort", sort);
  const requestQuery = requestParams.toString();
  const libraryPath = requestQuery ? `/media?${requestQuery}` : "/media";

  // İstatistik sorgusu önce tanımlanır: kütüphane yüklemesi her zaman son
  // tetiklenen okuma olur (yükleme/boş durum testleri buna güvenir).
  const stats = useQuery({
    queryKey: ["media-stats"],
    queryFn: () => api.get<MediaStats>("/media/stats"),
  });
  const library = useQuery({
    queryKey: ["media", "library", { kind, status, query, owned, sort }],
    queryFn: () => api.get<MediaPageResponse>(libraryPath),
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

  // Kütüphane araması kullanıcı yazdıkça URL'deki q parametresini günceller;
  // diğer filtreler (tür/durum) yerel kalır ve yalnızca isteğe yansır.
  useEffect(() => {
    if (!queryDirty.current) {
      queryDirty.current = true;
      return;
    }
    const raw = location.hash.replace(/^#/, "") || "/";
    const queryIndex = raw.indexOf("?");
    const path = queryIndex === -1 ? raw : raw.slice(0, queryIndex);
    const params = new URLSearchParams(queryIndex === -1 ? "" : raw.slice(queryIndex + 1));
    if (query) params.set("q", query);
    else params.delete("q");
    const serialized = params.toString();
    navigate(serialized ? `${path}?${serialized}` : path, { replace: true });
  }, [query]);

  const filterKey = [kind, status, query, owned, sort].join("\u0000");
  useEffect(() => {
    setExtra([]);
    setNextCursor(library.data?.next_cursor ?? null);
    setLoadMoreError(null);
  }, [filterKey, library.dataUpdatedAt]);

  useEffect(() => {
    if (!filtersOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setFiltersOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [filtersOpen]);

  async function loadMorePage() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    setLoadMoreError(null);
    try {
      const page = await api.get<MediaPageResponse>(
        `${libraryPath}${requestQuery ? "&" : "?"}cursor=${encodeURIComponent(nextCursor)}`,
      );
      setExtra((previous) => [...previous, ...page.items]);
      setNextCursor(page.next_cursor ?? null);
    } catch (loadError) {
      setLoadMoreError(loadError instanceof Error ? loadError.message : "Yüklenemedi");
    } finally {
      setLoadingMore(false);
    }
  }

  const baseItems = library.data?.items ?? [];
  const items = [...baseItems, ...extra];

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Takip"
          title="Medya"
          hint={`${items.length} kayıt`}
          action={
            <Button size="sm" disabled={!online} onClick={() => setProviderOpen((open) => !open)}>
              <Plus size={14} aria-hidden="true" /> Medya ekle
            </Button>
          }
        >
          <MediaMetrics stats={stats.data} />
        </WorkspacePaneHeader>

        <WorkspaceScrollArea className="space-y-4 p-3">
          {stats.isLoading && (
            <p role="status" aria-label="İstatistikler yükleniyor" className="text-meta text-muted">
              İstatistikler yükleniyor…
            </p>
          )}
          {stats.isError && (
            <div role="alert" className="flex flex-wrap items-center gap-3 text-meta text-danger">
              <span>Medya istatistikleri yüklenemedi: {stats.error.message}</span>
              <Button
                size="sm"
                disabled={stats.isFetching}
                onClick={() => {
                  void stats.refetch();
                }}
              >
                İstatistikleri yeniden dene
              </Button>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <Input
              value={query}
              onChange={setQuery}
              ariaLabel="Kütüphanede ara"
              placeholder="Kütüphanede ara"
              type="search"
              className="w-full sm:max-w-xs"
            />
            <Button className="md:hidden" onClick={() => setFiltersOpen(true)}>
              <SlidersHorizontal size={14} aria-hidden="true" /> Filtreleri aç
            </Button>
          </div>

          {filtersOpen && (
            <div
              className="fixed inset-0 z-modal flex items-end justify-center bg-canvas/60 p-4 sm:items-center"
              onClick={() => setFiltersOpen(false)}
            >
              <div
                role="dialog"
                aria-label="Kütüphane filtreleri"
                aria-modal="true"
                onClick={(event) => event.stopPropagation()}
                className="w-full max-w-md rounded-overlay border border-strong bg-surface p-5 shadow-overlay"
              >
                <div className="mb-3 flex items-center justify-between">
                  <h2 className=" text-title text-primary">Kütüphane filtreleri</h2>
                  <button
                    type="button"
                    aria-label="Filtreleri kapat"
                    onClick={() => setFiltersOpen(false)}
                    className="flex h-8 w-8 items-center justify-center rounded-control text-muted transition hover:bg-surface-hover hover:text-primary"
                  >
                    <X size={16} aria-hidden="true" />
                  </button>
                </div>
                <MediaLibraryControls kind={kind} status={status} onKindChange={setKind} onStatusChange={setStatus} />
              </div>
            </div>
          )}

          {providerOpen && <ProviderSearchPanel online={online} onAdded={refresh} />}

          <MediaSearchComposer online={online} onAdded={refresh} onActiveChange={setSearchActive} />

          {!searchActive && (
            <>
              <MediaLibraryControls kind={kind} status={status} onKindChange={setKind} onStatusChange={setStatus} />

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
                  <span>Kütüphanen boş</span> — yukarıdan tüm medyada arayarak ilk kaydını ekleyebilirsin.
                </Empty>
              ) : (
                <MediaPosterGrid
                  items={items}
                  online={online}
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
            </>
          )}

          <MediaSyncSummary online={online} />
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}

export function MediaPage() {
  const route = useHashRoute();
  const focusId = route.params.get("focus");
  const [view] = useState(() => mediaViewForPath(route.path, route.params));

  useEffect(() => {
    if (focusId) navigate(`/media/${encodeURIComponent(focusId)}`, { replace: true });
  }, [focusId]);

  return view;
}
