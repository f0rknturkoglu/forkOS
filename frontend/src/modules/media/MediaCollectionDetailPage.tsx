import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useMemo, useState } from "react";
import { useInfiniteQuery, useMutation } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { useHashRoute } from "@/app/router";
import { ApiError, api, qs } from "@/core/api";
import type { components } from "@/generated/api-schema";
import { Button, Chip, Empty, Field, Input, PageFrame, Select, Toolbar, cx } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { useDebounced, useOnline } from "@/lib/hooks";
import { Cover, KIND_LABELS, mediaCoverUrl, mediaProvider, providerChip, providerLabel, proxiedCover } from "./shared";

type MediaCollectionDetail = components["schemas"]["MediaCollectionDetailOut"];
type MediaItem = components["schemas"]["MediaItemOut"];

const PAGE_SIZE = 48;
const COLLECTION_PREFIX = "/media/collections/";

const SORTS: [string, string][] = [
  ["updated", "Son güncellenen"],
  ["created", "Son eklenen"],
  ["title", "Başlık"],
  ["score", "Puan"],
  ["progress", "İlerleme"],
];

/** Route `/media/collections/<id>` — kimlik yol parçasından çözülür (prop yok). */
function collectionIdFromPath(path: string): string {
  if (!path.startsWith(COLLECTION_PREFIX)) return "";
  const raw = path.slice(COLLECTION_PREFIX.length);
  if (!raw || raw.includes("/")) return "";
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

function CollectionItemCard({
  item,
  online,
  removing,
  onRemove,
}: {
  item: MediaItem;
  online: boolean;
  removing: boolean;
  onRemove: (item: MediaItem) => void;
}) {
  const href = `#/media/${encodeURIComponent(item.id)}`;
  const provider = mediaProvider(item);
  return (
    <li className="min-w-0">
      <a
        href={href}
        aria-label={`${item.title} detayını aç`}
        className="block rounded-card focus:outline-none focus:ring-2 focus:ring-accent"
      >
        <Cover url={proxiedCover(mediaCoverUrl(item))} title={item.title} size="aspect-[2/3] w-full" />
      </a>
      <div className="mt-2 min-w-0">
        <a
          href={href}
          className="block truncate text-body font-medium text-primary hover:text-accent focus:outline-none focus:underline"
        >
          {item.title}
        </a>
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-meta">
          <Chip identity={"kind-" + item.kind} variant="outline" size="xs">
            {KIND_LABELS[item.kind] ?? item.kind}
          </Chip>
          {provider && (
            <span className={cx("rounded-control border px-1.5 py-0.5", providerChip(provider))}>
              {providerLabel(provider)}
            </span>
          )}
        </div>
        <Button
          size="sm"
          className="mt-2"
          disabled={!online || removing}
          title={`${item.title} kaydını koleksiyondan çıkar`}
          onClick={() => onRemove(item)}
        >
          Koleksiyondan çıkar
        </Button>
      </div>
    </li>
  );
}

export function MediaCollectionDetailPage() {
  const route = useHashRoute();
  const collectionId = collectionIdFromPath(route.path);
  const online = useOnline();
  const [term, setTerm] = useState("");
  const q = useDebounced(term.trim(), 250);
  const [sort, setSort] = useState("updated");
  // Çıkarılan satırlar tazeleme gelene kadar gizlenir; istek başarısız olursa geri gelir.
  const [hidden, setHidden] = useState<string[]>([]);

  const detail = useInfiniteQuery({
    queryKey: ["media", "collection-detail", collectionId, q, sort],
    initialPageParam: "",
    enabled: Boolean(collectionId),
    queryFn: ({ pageParam }) =>
      api.get<MediaCollectionDetail>(
        `/media/collections/${encodeURIComponent(collectionId)}${qs({
          q,
          sort,
          limit: PAGE_SIZE,
          cursor: pageParam || undefined,
        })}`,
      ),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  });

  useEffect(() => {
    setHidden((previous) => (previous.length === 0 ? previous : []));
  }, [detail.dataUpdatedAt, collectionId, q, sort]);

  const remove = useMutation({
    mutationFn: (item: MediaItem) =>
      api.del(`/media/collections/${encodeURIComponent(collectionId)}/items/${encodeURIComponent(item.id)}`),
    onSuccess: () => invalidateAfter("media.write"),
    onError: (_error, item) => setHidden((previous) => previous.filter((id) => id !== item.id)),
  });

  function removeFromCollection(item: MediaItem) {
    setHidden((previous) => [...previous, item.id]);
    remove.mutate(item);
  }

  const collection = detail.data?.pages[0]?.collection;
  const total = detail.data?.pages[0]?.total ?? 0;
  const items = useMemo(() => {
    const seen = new Set<string>();
    const result: MediaItem[] = [];
    for (const page of detail.data?.pages ?? []) {
      for (const item of page.items) {
        if (seen.has(item.id) || hidden.includes(item.id)) continue;
        seen.add(item.id);
        result.push(item);
      }
    }
    return result;
  }, [detail.data, hidden]);

  const notFound = detail.error instanceof ApiError && detail.error.status === 404;

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Medya · Koleksiyon"
          title={collection?.title ?? "Koleksiyon"}
          hint={collection ? `${collection.item_count ?? 0} kayıt` : undefined}
        />
        <WorkspaceScrollArea className="space-y-4 p-3">
          <a
            href="#/media/collections"
            className="inline-flex items-center gap-1.5 rounded-control text-meta text-secondary hover:text-primary focus:outline-none focus:underline"
          >
            <ArrowLeft size={13} aria-hidden="true" /> Koleksiyonlar
          </a>

          {!collectionId || notFound ? (
            <Empty
              variant="page"
              title="Koleksiyon bulunamadı"
              action={
                <span className="flex flex-wrap justify-center gap-2">
                  <a href="#/media/collections" className="text-meta text-accent hover:underline">
                    Koleksiyonlara dön
                  </a>
                  <a href="#/media" className="text-meta text-accent hover:underline">
                    Medya kütüphanesine dön
                  </a>
                </span>
              }
            >
              Bu koleksiyon silinmiş ya da bağlantı geçersiz olabilir.
            </Empty>
          ) : detail.isLoading ? (
            <p role="status" className="text-meta text-muted">
              Koleksiyon yükleniyor…
            </p>
          ) : detail.isError ? (
            <Empty
              variant="page"
              action={
                <Button size="sm" disabled={detail.isFetching} onClick={() => void detail.refetch()}>
                  Yeniden dene
                </Button>
              }
            >
              Koleksiyon yüklenemedi: {detail.error.message}
            </Empty>
          ) : (
            <>
              {collection?.description && (
                <p className="max-w-3xl text-body text-secondary">{collection.description}</p>
              )}

              <Toolbar>
                <Field label="Koleksiyonda ara" className="min-w-0 flex-1 sm:max-w-xs">
                  <Input value={term} onChange={setTerm} ariaLabel="Koleksiyonda ara" className="w-full" />
                </Field>
                <Field label="Sıralama">
                  <Select value={sort} onChange={setSort} ariaLabel="Sıralama">
                    {SORTS.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <span className="ml-auto text-meta tabular-nums text-muted">
                  {items.length} / {total} kayıt
                </span>
              </Toolbar>

              {items.length === 0 ? (
                q ? (
                  <Empty>“{q}” için eşleşen kayıt yok.</Empty>
                ) : (
                  <Empty>Bu koleksiyonda henüz kayıt yok.</Empty>
                )
              ) : (
                <ul className="grid grid-cols-[repeat(auto-fill,minmax(156px,1fr))] gap-x-4 gap-y-6 sm:grid-cols-[repeat(auto-fill,minmax(176px,1fr))]">
                  {items.map((item) => (
                    <CollectionItemCard
                      key={item.id}
                      item={item}
                      online={online}
                      removing={remove.isPending}
                      onRemove={removeFromCollection}
                    />
                  ))}
                </ul>
              )}

              {detail.hasNextPage && (
                <div className="flex justify-center">
                  <Button onClick={() => void detail.fetchNextPage()} disabled={detail.isFetchingNextPage}>
                    {detail.isFetchingNextPage ? "Yükleniyor…" : "Daha fazla yükle"}
                  </Button>
                </div>
              )}

              {remove.error && (
                <p role="alert" className="text-meta text-danger">
                  Koleksiyondan çıkarılamadı: {remove.error.message}
                </p>
              )}
            </>
          )}
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
