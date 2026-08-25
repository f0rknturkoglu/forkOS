import { invalidateAfter } from "@/core/invalidation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { RotateCcw, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import type { MediaItem, MediaPage as MediaPageResponse } from "@/core/types";
import { Button, Chip, Empty, PageFrame, PageHeader, RowList } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { KIND_LABELS, mediaProvider, providerLabel, statusLabel } from "./shared";

type TrashItem = Pick<MediaItem, "id" | "title" | "kind" | "status" | "provider" | "meta">;

export function MediaTrashPage() {
  const online = useOnline();
  const { data, isLoading, isFetching, isError, error, refetch } = useQuery({
    queryKey: ["media", "trash"],
    queryFn: () => api.get<MediaPageResponse>("/media?trashed=true"),
  });
  const refresh = () => invalidateAfter("media.write");

  const restore = useMutation({
    mutationFn: (item: TrashItem) => api.post(`/media/${encodeURIComponent(item.id)}/restore`, {}),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (item: TrashItem) => api.del(`/media/${encodeURIComponent(item.id)}/permanent`),
    onSuccess: refresh,
  });

  async function confirmPermanent(item: TrashItem) {
    const confirmed = await confirmDialog({
      title: "Kalıcı olarak sil",
      body: (
        <>
          <span>Bu işlem geri alınamaz.</span> {item.title} kaydı ve tüketim geçmişi silinecek.
        </>
      ),
      confirmLabel: "Kalıcı sil",
      tone: "danger",
    });
    if (confirmed) remove.mutate(item);
  }

  const items = data?.items ?? [];

  return (
    <PageFrame className="space-y-6">
      <PageHeader eyebrow="Takip" title="Çöp kutusu" />

      {isLoading ? (
        <p role="status" className="text-meta text-muted">
          Çöp kutusu yükleniyor…
        </p>
      ) : isError ? (
        <Empty
          variant="page"
          action={
            <Button
              size="sm"
              disabled={isFetching}
              onClick={() => {
                void refetch();
              }}
            >
              Yeniden dene
            </Button>
          }
        >
          Çöp kutusu yüklenemedi: {error.message}
        </Empty>
      ) : items.length === 0 ? (
        <Empty>Çöp kutusu boş.</Empty>
      ) : (
        <RowList as="ul">
          {items.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center gap-3 py-2.5">
              <div className="min-w-0 flex-1">
                <p className="truncate text-body font-medium text-primary">{item.title}</p>
                <div className="mt-1 flex flex-wrap items-center gap-1.5 text-meta text-muted">
                  <Chip identity={"kind-" + item.kind} variant="outline" size="xs">
                    {KIND_LABELS[item.kind] ?? item.kind}
                  </Chip>
                  <span>{statusLabel(item.kind, item.status)}</span>
                  {mediaProvider(item) && (
                    <span className="rounded border px-1.5 py-0.5">{providerLabel(mediaProvider(item))}</span>
                  )}
                </div>
              </div>
              <span className="flex shrink-0 flex-wrap items-center gap-1.5">
                <Button size="sm" disabled={!online || restore.isPending} onClick={() => restore.mutate(item)}>
                  <RotateCcw size={13} aria-hidden="true" /> {item.title} kaydını geri yükle
                </Button>
                <Button
                  size="sm"
                  disabled={!online || remove.isPending}
                  onClick={() => {
                    void confirmPermanent(item);
                  }}
                >
                  <Trash2 size={13} aria-hidden="true" /> {item.title} kaydını kalıcı sil
                </Button>
              </span>
            </li>
          ))}
        </RowList>
      )}

      {restore.error && (
        <p role="alert" className="text-meta text-danger">
          Geri yüklenemedi: {restore.error.message}
        </p>
      )}
      {remove.error && (
        <p role="alert" className="text-meta text-danger">
          Kalıcı silinemedi: {remove.error.message}
        </p>
      )}
    </PageFrame>
  );
}
