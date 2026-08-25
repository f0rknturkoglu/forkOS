import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { navigate, useHashRoute } from "@/app/router";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import type { MediaItem, MediaPage as MediaPageResponse, MediaStats } from "@/core/types";
import { Button, Empty, PageFrame, PageHeader } from "@/core/ui";
import { useInvalidate, useOnline } from "@/lib/hooks";
import {
  MediaLibraryControls,
  MediaMetrics,
  MediaPosterGrid,
} from "./MediaPosterGrid";
import {
  consumptionBody,
  MEDIA_PROGRESS_REFRESH_KEYS,
} from "./MediaProgressActions";
import { MediaSearchComposer } from "./MediaSearchComposer";
import { MediaSyncSummary } from "./MediaSyncSummary";

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

/** Compatibility export; all page mutations share the append-only progress invalidation contract. */
export const MEDIA_REFRESH_KEYS = MEDIA_PROGRESS_REFRESH_KEYS;

export function MediaPage() {
  const route = useHashRoute();
  const focusId = route.params.get("focus");
  const online = useOnline();
  const invalidate = useInvalidate();
  const [kind, setKind] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    if (focusId) navigate(`/media/${encodeURIComponent(focusId)}`);
  }, [focusId]);

  const filters = new URLSearchParams();
  if (kind) filters.set("kind", kind);
  if (status) filters.set("status", status);
  const filterQuery = filters.toString();
  const libraryPath = filterQuery ? `/media?${filterQuery}` : "/media";

  const library = useQuery({
    queryKey: ["media", { kind, status }],
    queryFn: () => api.get<MediaPageResponse>(libraryPath),
  });
  const stats = useQuery({
    queryKey: ["media-stats"],
    queryFn: () => api.get<MediaStats>("/media/stats"),
  });

  const refresh = () => invalidate(...MEDIA_REFRESH_KEYS);
  const quick = useMutation({
    mutationFn: (item: Pick<MediaItem, "id" | "progress_measure">) =>
      api.post(
        `/media/${encodeURIComponent(item.id)}/consumptions`,
        consumptionBody("quick", item),
      ),
    onSuccess: refresh,
  });
  const trash = useMutation({
    mutationFn: (item: Pick<MediaItem, "id">) => api.del(`/media/${encodeURIComponent(item.id)}`),
    onSuccess: refresh,
  });

  async function confirmTrash(item: Pick<MediaItem, "id" | "title">) {
    const confirmed = await confirmDialog({
      title: "Kayıt çöpe taşınsın mı?",
      body: <><strong className="font-medium text-primary">{item.title}</strong> çöp kutusundan geri yüklenebilir.</>,
      confirmLabel: "Çöpe taşı",
      tone: "danger",
    });
    if (confirmed) trash.mutate(item);
  }

  const items = library.data?.items ?? [];

  return (
    <PageFrame className="space-y-6">
      <PageHeader eyebrow="Takip" title="Medya" />

      <div className="space-y-2">
        <MediaMetrics stats={stats.data} />
        {stats.isLoading && <p role="status" aria-label="İstatistikler yükleniyor" className="text-meta text-muted">İstatistikler yükleniyor…</p>}
        {stats.isError && (
          <div role="alert" className="flex flex-wrap items-center gap-3 text-meta text-danger">
            <span>Medya istatistikleri yüklenemedi: {stats.error.message}</span>
            <Button size="sm" disabled={stats.isFetching} onClick={() => { void stats.refetch(); }}>İstatistikleri yeniden dene</Button>
          </div>
        )}
      </div>

      <MediaSearchComposer online={online} onAdded={refresh} />

      <MediaLibraryControls
        kind={kind}
        status={status}
        onKindChange={setKind}
        onStatusChange={setStatus}
      />

      {library.isLoading ? (
        <p role="status" aria-label="Kütüphane yükleniyor" className="py-8 text-center text-meta text-muted">Kütüphane yükleniyor…</p>
      ) : library.isError ? (
        <Empty variant="page" action={<Button size="sm" disabled={library.isFetching} onClick={() => { void library.refetch(); }}>Kütüphaneyi yeniden dene</Button>}>
          Kütüphane yüklenemedi: {library.error.message}
        </Empty>
      ) : items.length === 0 ? (
        <Empty>Kütüphanen boş — yukarıdan tüm medyada arayarak ilk kaydını ekleyebilirsin.</Empty>
      ) : (
        <MediaPosterGrid
          items={items}
          online={online}
          onQuick={(item) => quick.mutate(item)}
          onTrash={(item) => { void confirmTrash(item); }}
        />
      )}

      {quick.error && <p role="alert" className="text-meta text-danger">İlerleme kaydedilemedi: {quick.error.message}</p>}
      {trash.error && <p role="alert" className="text-meta text-danger">Kayıt çöpe taşınamadı: {trash.error.message}</p>}

      <MediaSyncSummary online={online} />
    </PageFrame>
  );
}
