import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { ApiError, api } from "@/core/api";
import { Button, Input, RowList, cx } from "@/core/ui";
import { useDebounced } from "@/lib/hooks";
import type { GlobalMetadataSearch, MediaItem, MediaPage, MetadataResult } from "@/core/types";
import { Cover, KIND_LABELS, kindChip, mediaCoverUrl, providerChip } from "./shared";

export function providerCreateBody(hit: MetadataResult): Record<string, unknown> {
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
  };
}

function existingId(error: Error): string | null {
  if (!(error instanceof ApiError) || error.status !== 409) return null;
  try {
    const body = JSON.parse(error.message) as { existing_id?: unknown };
    return typeof body.existing_id === "string" && body.existing_id ? body.existing_id : null;
  } catch {
    return null;
  }
}

function hitCoverUrl(hit: MetadataResult): string | null {
  return mediaCoverUrl({ cover_path: null, cover_url: hit.cover_url ?? null, meta: hit.meta });
}

function ResultRow({ hit, action }: { hit: MetadataResult; action?: React.ReactNode }) {
  return (
    <li className="flex items-center gap-3 py-2">
      <Cover url={hitCoverUrl(hit)} title={hit.title} size="h-16 w-11" />
      <div className="min-w-0 flex-1">
        <h3 className="truncate text-body font-medium text-primary">{hit.title}</h3>
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-meta text-muted">
          <span className={cx("rounded border px-1.5 py-0.5", kindChip(hit.kind))}>{KIND_LABELS[hit.kind] ?? hit.kind}</span>
          <span className={cx("rounded border px-1.5 py-0.5", providerChip(hit.provider))}>{hit.provider}</span>
          {(hit.subtitle || hit.year) && <span>{hit.subtitle ?? ""}{hit.year ? ` · ${hit.year}` : ""}</span>}
        </div>
      </div>
      {action}
    </li>
  );
}

export function MediaSearchComposer({ online, onAdded }: { online: boolean; onAdded: () => void }) {
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const [duplicateHref, setDuplicateHref] = useState<string | null>(null);
  const term = useDebounced(search.trim(), 250);
  const enabled = term.length >= 2;
  const encodedTerm = encodeURIComponent(term);

  const library = useQuery({
    queryKey: ["media", "composer", term],
    queryFn: () => api.get<MediaPage>(`/media?q=${encodedTerm}&limit=8`),
    enabled,
  });
  const catalog = useQuery({
    queryKey: ["media-search", "global", term],
    queryFn: () => api.get<GlobalMetadataSearch>(`/media/search/global?q=${encodedTerm}`),
    enabled,
  });

  const add = useMutation({
    mutationFn: (hit: MetadataResult) => api.post<MediaItem>("/media", providerCreateBody(hit)),
    onSuccess: () => {
      setDuplicateHref(null);
      client.invalidateQueries({ queryKey: ["media"] });
      onAdded();
    },
    onError: (error: Error, hit) => {
      if (!(error instanceof ApiError) || error.status !== 409) return;
      const id = existingId(error);
      setDuplicateHref(id
        ? `#/media/${encodeURIComponent(id)}`
        : `#/media?focus=${encodeURIComponent(hit.title)}`);
    },
  });

  const libraryItems = library.data?.items ?? [];
  const hits = catalog.data?.results ?? [];
  const warnings = catalog.data?.warnings ?? [];
  const allProvidersUnavailable = warnings.length > 0 && hits.length === 0;

  return (
    <div className="space-y-3">
      <div className="mx-auto max-w-xl">
        <Input
          value={search}
          onChange={(value) => { setSearch(value); setDuplicateHref(null); }}
          placeholder="Film, dizi, kitap, müzik…"
          ariaLabel="Tüm medyada ara"
          type="search"
          className="w-full"
        />
      </div>

      {enabled && (
        <div className="space-y-4">
          {warnings.length > 0 && (
            <p className="text-meta text-muted">
              {warnings.map((warning) => warning.message).join(" · ")}
              {allProvidersUnavailable && <> <a href="#/settings?section=media-links" className="text-accent hover:underline">Medya bağlantılarını aç</a></>}
            </p>
          )}

          <section aria-labelledby="media-library-results">
            <h2 id="media-library-results" className="label-caps text-secondary">Kütüphanende</h2>
            {library.isFetching ? <p className="mt-2 text-meta text-muted">Aranıyor…</p> : (
              <RowList as="ul" className="mt-1">
                {libraryItems.map((item) => (
                  <li key={item.id} className="flex items-center gap-3 py-2">
                    <Cover url={mediaCoverUrl(item)} title={item.title} size="h-16 w-11" />
                    <div className="min-w-0">
                      <h3 className="truncate text-body font-medium text-primary">{item.title}</h3>
                      <span className={cx("mt-1 inline-block rounded border px-1.5 py-0.5 text-meta", kindChip(item.kind))}>
                        {KIND_LABELS[item.kind] ?? item.kind}
                      </span>
                    </div>
                  </li>
                ))}
              </RowList>
            )}
          </section>

          <section aria-labelledby="media-catalog-results">
            <h2 id="media-catalog-results" className="label-caps text-secondary">Katalog sonuçları</h2>
            {catalog.isFetching ? <p className="mt-2 text-meta text-muted">Aranıyor…</p> : (
              <RowList as="ul" className="mt-1">
                {hits.map((hit) => (
                  <ResultRow
                    key={`${hit.provider}:${hit.provider_id}`}
                    hit={hit}
                    action={(
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={!online || add.isPending}
                        onClick={() => add.mutate(hit)}
                      >
                        <Plus size={13} /> {hit.title} kütüphaneye ekle
                      </Button>
                    )}
                  />
                ))}
              </RowList>
            )}
          </section>

          {duplicateHref && <a href={duplicateHref} className="text-meta text-accent hover:underline">Kütüphanede aç</a>}
        </div>
      )}
    </div>
  );
}
