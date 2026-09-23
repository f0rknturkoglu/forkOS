import { invalidateAfter } from "@/core/invalidation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { RotateCcw, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import type { MediaItem, MediaPage as MediaPageResponse } from "@/core/types";
import { Button, Chip, Empty, IconButton, PageFrame, RowList, cx } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { useOnline } from "@/lib/hooks";
import { Cover, KIND_LABELS, mediaCoverUrl, mediaProvider, providerChip, providerLabel, statusLabel } from "./shared";

type TrashItem = Pick<
  MediaItem,
  "id" | "title" | "kind" | "status" | "provider" | "meta" | "archived_at" | "cover_path" | "cover_url"
>;

/** Arşivlenme tarihi; gecersiz degerde satir tarih gostermez. */
function archivedLabel(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
}

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
          <strong className="font-medium text-primary">{item.title}</strong> kaydı ve tüketim geçmişi silinecek.
          <span className="mt-1 block">Bu işlem geri alınamaz.</span>
        </>
      ),
      confirmLabel: "Kalıcı sil",
      tone: "danger",
    });
    if (confirmed) remove.mutate(item);
  }

  const items = data?.items ?? [];

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader eyebrow="Medya" title="Çöp kutusu" hint={`${items.length} kayıt`} />
        <WorkspaceScrollArea className="space-y-4 p-4">
          {isLoading ? (
            <p role="status" className="text-meta text-muted">
              Çöp kutusu yükleniyor…
            </p>
          ) : isError ? (
            <div role="alert">
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
            </div>
          ) : items.length === 0 ? (
            <Empty>Çöp kutusu boş.</Empty>
          ) : (
            <RowList as="ul">
              {items.map((item) => {
                const archived = archivedLabel(item.archived_at);
                return (
                  <li key={item.id} className="flex items-center gap-3 py-2.5">
                    <Cover url={mediaCoverUrl(item)} title={item.title} size="h-14 w-10" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-body font-medium text-primary" title={item.title}>
                        {item.title}
                      </p>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5 text-meta text-muted">
                        <Chip identity={"kind-" + item.kind} variant="outline" size="xs">
                          {KIND_LABELS[item.kind] ?? item.kind}
                        </Chip>
                        <span>{statusLabel(item.kind, item.status)}</span>
                        {mediaProvider(item) && (
                          <span className={cx("rounded border px-1.5 py-px", providerChip(mediaProvider(item)))}>
                            {providerLabel(mediaProvider(item))}
                          </span>
                        )}
                        {archived && <span title="Silinme tarihi">{archived}</span>}
                      </div>
                    </div>
                    <span className="flex shrink-0 items-center gap-1.5">
                      <Button
                        size="sm"
                        disabled={!online || restore.isPending}
                        onClick={() => restore.mutate(item)}
                        ariaLabel={`${item.title} kaydını geri yükle`}
                      >
                        <RotateCcw size={13} aria-hidden="true" /> Geri yükle
                      </Button>
                      <IconButton
                        title={`${item.title} kaydını kalıcı sil`}
                        tone="danger"
                        disabled={!online || remove.isPending}
                        onClick={() => {
                          void confirmPermanent(item);
                        }}
                      >
                        <Trash2 size={14} aria-hidden="true" />
                      </IconButton>
                    </span>
                  </li>
                );
              })}
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
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
