import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/core/api";
import { Button, Checkbox, Chip, Empty, Field, Input, Select, Tabs, cx } from "@/core/ui";
import { invalidateAfter } from "@/core/invalidation";
import type { components } from "@/generated/api-schema";
import { useDebounced } from "@/lib/hooks";
import type { GlobalMetadataSearch, MediaItem, MediaPage, MetadataResult } from "@/core/types";
import {
  Cover,
  KIND_LABELS,
  mediaCoverUrl,
  mediaProvider,
  providerChip,
  providerLabel,
  statusLabel,
  ARTWORK_PROXY_PATH,
} from "./shared";

type MediaCollection = components["schemas"]["MediaCollectionOut"];
type SearchWarning = components["schemas"]["MetadataSearchWarning"];

/** Katalog aramasinda tek tur icin istenen sonuc sayisi. */
const CATALOG_LIMIT = 8;
/** Kullanici yazmayi biraktiktan sonra beklenen sure. */
const DEBOUNCE_MS = 300;
/** Tek karakterlik aramalar sonuc getirmez; istek de atilmaz. */
const MIN_TERM = 2;

/** Kapsam sekmeleri: her biri backend'in `kind` suzgecine maplenir.
 *  `kinds === null` kapsam gondermez — provider varyantlari suzulmez. */
const SCOPES = [
  { id: "all", label: "Tüm katalog", kinds: null },
  { id: "screen", label: "Film/dizi", kinds: ["movie", "show"] },
  { id: "anime", label: "Anime/manga", kinds: ["anime", "manga"] },
  { id: "books", label: "Kitap/sesli kitap", kinds: ["book", "audiobook"] },
  { id: "audio", label: "Podcast/müzik", kinds: ["podcast", "music"] },
  { id: "game", label: "Oyun", kinds: ["game"] },
] as const;

type ScopeId = (typeof SCOPES)[number]["id"];

const KIND_SCOPE: Record<string, ScopeId> = {
  movie: "screen",
  show: "screen",
  anime: "anime",
  manga: "anime",
  book: "books",
  audiobook: "books",
  podcast: "audio",
  music: "audio",
  game: "game",
};

/** Katalog aramasi: kapsam birden fazla tur iceriyorsa tur basina ayri istek
 *  atilir (uc `kind`'i tek deger olarak dogrular) ve sonuclar birlestirilir. */
async function searchCatalog(term: string, kinds: readonly string[] | null): Promise<GlobalMetadataSearch> {
  const query = encodeURIComponent(term);
  if (!kinds) {
    return api.get<GlobalMetadataSearch>(`/media/search/global?q=${query}&limit=${CATALOG_LIMIT}`);
  }
  const pages = await Promise.all(
    kinds.map((kind) =>
      api.get<GlobalMetadataSearch>(`/media/search/global?q=${query}&kind=${kind}&limit=${CATALOG_LIMIT}`),
    ),
  );
  const results: MetadataResult[] = [];
  const warnings: SearchWarning[] = [];
  const seen = new Set<string>();
  for (const page of pages) {
    for (const hit of page.results) {
      const key = `${hit.provider}:${hit.provider_id}:${hit.kind}`;
      if (seen.has(key)) continue;
      seen.add(key);
      results.push(hit);
    }
    for (const warning of page.warnings) {
      if (warnings.some((row) => row.provider === warning.provider && row.kind === warning.kind)) continue;
      warnings.push(warning);
    }
  }
  return { results, warnings, cached: pages.every((page) => page.cached) };
}

/** Uzak gorseli backend onbellegine dusurur (host allowlist backend'de);
 *  yerel `/api/media/assets/...` yollari dogrudan servis edilir. */
function coverSource(hit: MetadataResult): string | null {
  const url = mediaCoverUrl({ cover_path: null, cover_url: hit.cover_url ?? null, meta: hit.meta });
  if (!url) return null;
  return /^https?:\/\//i.test(url) ? `${ARTWORK_PROXY_PATH}?url=${encodeURIComponent(url)}` : url;
}

/** Ayni satirin iki kez acilmamasi icin katalog satiri anahtari. */
function hitKey(hit: MetadataResult): string {
  return `${hit.provider}:${hit.provider_id}:${hit.kind}`;
}

/** Ekleme panosunun varsayilanlari; gonderimde de bu degerler kullanilir. */
interface AddDraft {
  status: "planned" | "in_progress";
  collectionId: string;
  owned: boolean;
  favorite: boolean;
  monitored: boolean;
}

const EMPTY_DRAFT: AddDraft = {
  status: "planned",
  collectionId: "",
  owned: false,
  favorite: false,
  monitored: false,
};

type AddRequest = { hit: MetadataResult; draft: AddDraft; term: string };

export function providerCreateBody(hit: MetadataResult, draft: AddDraft = EMPTY_DRAFT): Record<string, unknown> {
  return {
    source: "provider",
    title: hit.title,
    kind: hit.kind,
    provider: hit.provider,
    provider_id: hit.provider_id,
    provider_ids: hit.provider_ids,
    summary: hit.summary,
    total: hit.total,
    progress_measure: hit.progress_measure,
    cover_url: hit.cover_url,
    backdrop_url: hit.backdrop_url,
    meta: hit.meta,
    status: draft.status,
    favorite: draft.favorite,
    owned: draft.owned,
    monitored: draft.monitored,
  };
}

/** Kutuphane kaydi ile katalog sonucunun ayni saglayici kimligini tasiyip
 *  tasimadigi. tmdb kimlikleri "movie:99" / "99" gibi iki bicimde gezebilir. */
function sameProviderIdentity(item: MediaItem, hit: MetadataResult): boolean {
  if (mediaProvider(item) !== hit.provider) return false;
  const candidates = new Set<string>([hit.provider_id]);
  if (hit.provider === "tmdb") {
    const [, raw] = hit.provider_id.split(":");
    if (raw) candidates.add(raw);
  }
  const ids = [item.provider_id, ...Object.values(item.provider_ids ?? {})]
    .map((value) => (typeof value === "string" || typeof value === "number" ? String(value) : ""))
    .filter(Boolean);
  return ids.some((id) => candidates.has(id));
}

function ResultRow({
  hit,
  action,
  children,
}: {
  hit: MetadataResult;
  action: React.ReactNode;
  children?: React.ReactNode;
}) {
  const summary = hit.summary?.trim() || null;
  return (
    <li className="border-b border-subtle py-2.5 last:border-b-0">
      <div className="flex items-start gap-3">
        <Cover url={coverSource(hit)} title={hit.title} size="h-16 w-11" />
        <div className="min-w-0 flex-1">
          <h3 className="line-clamp-2 text-body font-medium text-primary">{hit.title}</h3>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-meta text-muted">
            <Chip identity={"kind-" + hit.kind} variant="outline" size="xs">
              {KIND_LABELS[hit.kind] ?? hit.kind}
            </Chip>
            <span className={cx("rounded border px-1.5 py-0.5", providerChip(hit.provider))}>
              {providerLabel(hit.provider)}
            </span>
            {hit.year && <span className="tabular-nums">{hit.year}</span>}
            {hit.subtitle && <span className="truncate">{hit.subtitle}</span>}
          </div>
          {summary && <p className="mt-1 line-clamp-2 text-meta text-muted">{summary}</p>}
        </div>
        {action}
      </div>
      {children}
    </li>
  );
}

/**
 * Katalog arama diyalogunun govdesi: kapsam sekmeleri, debounce'lu arama,
 * yerel eslesmeler, saglayici sonuclari ve satir ici ekleme panosu.
 *
 * `MediaSearchDialog` bunu `Modal` icinde render eder; dogrudan sayfaya
 * gomulmez (eski satir ici iki kutu kaldirildi).
 */
export function MediaSearchComposer({
  online,
  initialKind,
  onAdded,
}: {
  online: boolean;
  /** Diyalogu acan yuzeyin aktif tur filtresi; kapsam sekmesine cevrilir. */
  initialKind?: string;
  onAdded: (item: MediaItem) => void;
}) {
  const [scope, setScope] = useState<ScopeId>(() => {
    if (!initialKind) return "all";
    if (SCOPES.some((item) => item.id === initialKind)) return initialKind as ScopeId;
    return KIND_SCOPE[initialKind] ?? "all";
  });
  const [search, setSearch] = useState("");
  const searchRef = useRef(search);
  searchRef.current = search;
  const [addTarget, setAddTarget] = useState<MetadataResult | null>(null);
  const [draft, setDraft] = useState<AddDraft>(EMPTY_DRAFT);
  const [duplicate, setDuplicate] = useState<{ term: string; hit: MetadataResult } | null>(null);
  const [addError, setAddError] = useState<string | null>(null);

  const term = useDebounced(search.trim(), DEBOUNCE_MS);
  const termRef = useRef(term);
  termRef.current = term;
  const enabled = term.length >= MIN_TERM;

  const library = useQuery({
    queryKey: ["media", "composer", "library", term],
    queryFn: () => api.get<MediaPage>(`/media?q=${encodeURIComponent(term)}&limit=8`),
    enabled,
  });
  const catalog = useQuery({
    queryKey: ["media-search", "global", term, scope],
    queryFn: () => searchCatalog(term, SCOPES.find((item) => item.id === scope)?.kinds ?? null),
    enabled,
  });
  const collections = useQuery({
    queryKey: ["media", "collections"],
    queryFn: () => api.get<MediaCollection[]>("/media/collections"),
    enabled: addTarget !== null,
  });

  const libraryItems = library.data?.items ?? [];
  const hits = catalog.data?.results ?? [];
  const warnings = catalog.data?.warnings ?? [];

  const duplicateLookup = useQuery({
    queryKey: ["media", "composer", "duplicate", duplicate?.hit.provider_id ?? "", duplicate?.term ?? ""],
    queryFn: () => api.get<MediaPage>(`/media?q=${encodeURIComponent(duplicate!.hit.title)}&limit=10`),
    enabled: duplicate !== null,
    retry: false,
  });
  const existing = duplicate
    ? ([...libraryItems, ...(duplicateLookup.data?.items ?? [])].find((item) =>
        sameProviderIdentity(item, duplicate.hit),
      ) ?? null)
    : null;

  const add = useMutation({
    mutationFn: async ({ hit, draft: values }: AddRequest) => {
      const item = await api.post<MediaItem>("/media", providerCreateBody(hit, values));
      if (values.collectionId) {
        await api.post(`/media/collections/${encodeURIComponent(values.collectionId)}/items/${item.id}`);
      }
      return item;
    },
    onMutate: () => setAddError(null),
    onSuccess: (item) => {
      setDuplicate(null);
      setAddTarget(null);
      setDraft(EMPTY_DRAFT);
      invalidateAfter("media.write");
      onAdded(item);
    },
    onError: (error: Error, { hit, term: initiatedTerm }: AddRequest) => {
      // Geciken yanit yeni aramanın altina dusmesin.
      if (termRef.current !== initiatedTerm || searchRef.current.trim() !== initiatedTerm) return;
      if (error instanceof ApiError && error.status === 409) {
        setDuplicate({ term: initiatedTerm, hit });
        add.reset();
        return;
      }
      setAddError("Eklenemedi. Lütfen tekrar deneyin.");
    },
  });

  const duplicateVisible = duplicate !== null && duplicate.term === term && duplicate.term === search.trim();
  // "Sonuc yok" yalnizca sorgu gercekten bitti ve bos donduyse yazilir.
  const libraryEmpty = library.isSuccess && libraryItems.length === 0;
  const catalogEmpty = catalog.isSuccess && hits.length === 0;

  function openAddPanel(hit: MetadataResult) {
    setAddError(null);
    setDuplicate(null);
    add.reset();
    setAddTarget((current) => (current && hitKey(current) === hitKey(hit) ? null : hit));
    setDraft(EMPTY_DRAFT);
  }

  return (
    <div className="space-y-3">
      <Input
        value={search}
        onChange={(value) => {
          setSearch(value);
          setAddTarget(null);
          setDuplicate(null);
          setAddError(null);
        }}
        placeholder="Film, dizi, kitap, müzik…"
        ariaLabel="Katalogda ara"
        type="search"
        className="w-full"
      />

      <Tabs
        value={scope}
        onChange={setScope}
        ariaLabel="Katalog kapsamı"
        items={SCOPES.map((item) => ({ id: item.id, label: item.label }))}
      />

      {!enabled ? (
        <Empty variant="inline">Aramak için en az {MIN_TERM} karakter yaz.</Empty>
      ) : (
        <div className="space-y-4">
          {(library.isFetching || catalog.isFetching) && (
            <p role="status" aria-live="polite" className="text-meta text-muted">
              Aranıyor…
            </p>
          )}

          {warnings.length > 0 && (
            <ul role="status" aria-live="polite" className="space-y-0.5 text-meta text-warn">
              {warnings.map((warning) => (
                <li key={`${warning.provider}:${warning.kind}:${warning.message}`}>
                  {warning.message}{" "}
                  <a href="#/settings?section=media-links" className="text-accent hover:underline">
                    Sağlayıcı anahtarlarını aç
                  </a>
                </li>
              ))}
            </ul>
          )}

          {addError && (
            <p role="alert" className="text-meta text-danger">
              {addError}
            </p>
          )}

          {duplicateVisible && (
            <p role="status" aria-live="polite" className="text-meta text-muted">
              Kütüphanende var: {duplicate.hit.title}.{" "}
              {existing ? (
                <a href={`#/media/${encodeURIComponent(existing.id)}`} className="text-accent hover:underline">
                  Kütüphanede aç
                </a>
              ) : duplicateLookup.isFetching ? (
                <span>Kayıt aranıyor…</span>
              ) : (
                <a href="#/media" className="text-accent hover:underline">
                  Kütüphane
                </a>
              )}
            </p>
          )}

          <section aria-labelledby="media-library-results">
            <h2 id="media-library-results" className="label-caps text-secondary">
              Kütüphanende
            </h2>
            {library.isError ? (
              <p role="alert" className="mt-2 text-meta text-danger">
                Kütüphane sonuçları yüklenemedi.
              </p>
            ) : libraryEmpty ? (
              <Empty variant="inline">Kütüphanende eşleşme yok.</Empty>
            ) : (
              <ul className="mt-1">
                {libraryItems.map((item) => (
                  <li key={item.id} className="flex items-center gap-3 py-2">
                    <Cover url={mediaCoverUrl(item)} title={item.title} size="h-16 w-11" />
                    <div className="min-w-0 flex-1">
                      <h3 className="line-clamp-2 text-body font-medium text-primary">{item.title}</h3>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5 text-meta">
                        <Chip identity={"kind-" + item.kind} variant="outline" size="xs">
                          {KIND_LABELS[item.kind] ?? item.kind}
                        </Chip>
                        {mediaProvider(item) && (
                          <span className={cx("rounded border px-1.5 py-0.5", providerChip(mediaProvider(item)))}>
                            {providerLabel(mediaProvider(item))}
                          </span>
                        )}
                      </div>
                    </div>
                    <a
                      href={`#/media/${encodeURIComponent(item.id)}`}
                      aria-label={`${item.title} detayını aç`}
                      className="shrink-0 text-meta font-medium text-accent hover:underline focus:outline-none focus:underline"
                    >
                      Aç
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-labelledby="media-catalog-results">
            <h2 id="media-catalog-results" className="label-caps text-secondary">
              Katalog sonuçları
            </h2>
            {catalog.isError ? (
              <p role="alert" className="mt-2 text-meta text-danger">
                Katalog sonuçları yüklenemedi.
              </p>
            ) : catalogEmpty ? (
              <Empty variant="inline">Sonuç bulunamadı.</Empty>
            ) : (
              <ul className="mt-1">
                {hits.map((hit) => {
                  const selected = addTarget !== null && hitKey(addTarget) === hitKey(hit);
                  return (
                    <ResultRow
                      key={hitKey(hit)}
                      hit={hit}
                      action={
                        <Button
                          size="sm"
                          variant="primary"
                          disabled={!online || add.isPending}
                          ariaLabel={`${hit.title} kaydını ekle`}
                          ariaExpanded={selected}
                          onClick={() => openAddPanel(hit)}
                        >
                          Ekle
                        </Button>
                      }
                    >
                      {selected && (
                        <div className="mt-2 space-y-2 rounded-control border border-subtle bg-surface-sunken p-3">
                          <Field label="Başlangıç durumu">
                            <Select
                              value={draft.status}
                              onChange={(value) =>
                                setDraft((current) => ({
                                  ...current,
                                  status: value === "in_progress" ? "in_progress" : "planned",
                                }))
                              }
                            >
                              <option value="planned">{statusLabel(hit.kind, "planned")}</option>
                              <option value="in_progress">{statusLabel(hit.kind, "in_progress")}</option>
                            </Select>
                          </Field>
                          <Field label="Koleksiyon">
                            <Select
                              value={draft.collectionId}
                              disabled={collections.isLoading}
                              onChange={(value) => setDraft((current) => ({ ...current, collectionId: value }))}
                            >
                              <option value="">Koleksiyon yok</option>
                              {(collections.data ?? []).map((collection) => (
                                <option key={collection.id} value={collection.id}>
                                  {collection.title}
                                </option>
                              ))}
                            </Select>
                          </Field>
                          <div className="flex flex-wrap items-center gap-3">
                            <Checkbox
                              checked={draft.owned}
                              onChange={(checked) => setDraft((current) => ({ ...current, owned: checked }))}
                              label="Sahiplik"
                            />
                            <Checkbox
                              checked={draft.favorite}
                              onChange={(checked) => setDraft((current) => ({ ...current, favorite: checked }))}
                              label="Favori"
                            />
                            <Checkbox
                              checked={draft.monitored}
                              onChange={(checked) => setDraft((current) => ({ ...current, monitored: checked }))}
                              label="Yeni yayınları takip et"
                            />
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              size="sm"
                              variant="primary"
                              disabled={!online || add.isPending}
                              ariaLabel={`${hit.title} kaydını kütüphaneye ekle`}
                              onClick={() => add.mutate({ hit, draft, term })}
                            >
                              Kütüphaneye ekle
                            </Button>
                            <Button size="sm" onClick={() => setAddTarget(null)}>
                              Vazgeç
                            </Button>
                          </div>
                        </div>
                      )}
                    </ResultRow>
                  );
                })}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
