import { invalidateAfter } from "@/core/invalidation";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Library, Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import type { components } from "@/generated/api-schema";
import { Button, Empty, Field, Input, PageFrame, RowList, Section, relativeTime } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { useOnline } from "@/lib/hooks";
import { proxiedCover } from "./shared";

type MediaCollection = components["schemas"]["MediaCollectionOut"];

/** Koleksiyon kartındaki en yeni dört kapak; kapak yoksa kesikli yer tutucu. */
function CoverMosaic({ covers }: { covers: string[] }) {
  const [broken, setBroken] = useState<string[]>([]);
  const urls = covers.slice(0, 4);
  if (urls.length === 0) {
    return (
      <span
        aria-hidden="true"
        className="flex h-16 w-14 shrink-0 items-center justify-center rounded-control border border-dashed border-subtle bg-surface-sunken text-muted"
      >
        <Library size={16} />
      </span>
    );
  }
  return (
    <span
      aria-hidden="true"
      className="grid h-16 w-14 shrink-0 grid-cols-2 gap-px overflow-hidden rounded-control border border-subtle bg-surface-sunken"
    >
      {urls.map((cover, index) => {
        const src = proxiedCover(cover);
        if (!src || broken.includes(cover)) {
          return <span key={`${cover}-${index}`} className="h-full w-full bg-surface-sunken" />;
        }
        return (
          <img
            key={`${cover}-${index}`}
            src={src}
            alt=""
            loading="lazy"
            onError={() => setBroken((previous) => [...previous, cover])}
            className="h-full w-full object-cover"
          />
        );
      })}
    </span>
  );
}

export function MediaCollectionsPage() {
  const online = useOnline();
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<MediaCollection | null>(null);
  const [editName, setEditName] = useState("");

  const {
    data: collections,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["media", "collections"],
    queryFn: () => api.get<MediaCollection[]>("/media/collections"),
  });
  const refresh = () => invalidateAfter("media.write");

  const create = useMutation({
    mutationFn: (title: string) => api.post<MediaCollection>("/media/collections", { title }),
    onSuccess: () => {
      setName("");
      refresh();
    },
  });
  const rename = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      api.patch<MediaCollection>(`/media/collections/${encodeURIComponent(id)}`, { title }),
    onSuccess: () => {
      setEditing(null);
      refresh();
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/media/collections/${encodeURIComponent(id)}`),
    onSuccess: refresh,
  });

  async function confirmDelete(collection: MediaCollection) {
    const confirmed = await confirmDialog({
      title: "Koleksiyon silinsin mi?",
      body: (
        <>
          <span>{collection.title}</span> koleksiyonu ve koleksiyon üyelikleri silinecek; kayıtlar kalır.
        </>
      ),
      confirmLabel: "Koleksiyonu sil",
      tone: "danger",
    });
    if (confirmed) remove.mutate(collection.id);
  }

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Medya"
          title="Koleksiyonlar"
          hint={collections ? `${collections.length} koleksiyon` : undefined}
        />
        <WorkspaceScrollArea className="space-y-4 p-3">
          <Section title="Yeni koleksiyon" className="max-w-xl">
            <form
              className="flex flex-wrap items-end gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (!name.trim() || !online) return;
                create.mutate(name.trim());
              }}
            >
              <Field label="Koleksiyon adı" className="min-w-0 flex-1">
                <Input value={name} onChange={setName} disabled={!online || create.isPending} className="w-full" />
              </Field>
              <Button type="submit" variant="primary" disabled={!online || !name.trim() || create.isPending}>
                <Plus size={13} aria-hidden="true" /> Koleksiyon oluştur
              </Button>
            </form>
            {create.error && (
              <p role="alert" className="mt-2 text-meta text-danger">
                Koleksiyon oluşturulamadı: {create.error.message}
              </p>
            )}
          </Section>

          {isLoading ? (
            <p role="status" className="text-meta text-muted">
              Koleksiyonlar yükleniyor…
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
              Koleksiyonlar yüklenemedi: {error.message}
            </Empty>
          ) : !collections || collections.length === 0 ? (
            <Empty>Henüz koleksiyon yok.</Empty>
          ) : (
            <RowList as="ul">
              {collections.map((collection) => (
                <li key={collection.id} className="flex flex-wrap items-center gap-3 py-2.5">
                  <a
                    href={`#/media/collections/${encodeURIComponent(collection.id)}`}
                    aria-label={`${collection.title} koleksiyonunu aç`}
                    className="flex min-w-0 flex-1 items-center gap-3 rounded-control p-1 transition hover:bg-surface-hover focus:outline-none focus:ring-2 focus:ring-accent"
                  >
                    <CoverMosaic covers={collection.covers ?? []} />
                    <span className="min-w-0 flex-1">
                      <span className="flex min-w-0 items-center gap-1.5">
                        {collection.color && (
                          <span
                            aria-hidden="true"
                            // Kullanıcı verisi: renk noktası yalnız kayıttan gelir, token'a bağlanmaz.
                            style={{ background: collection.color }}
                            className="h-2.5 w-2.5 shrink-0 rounded-full border border-subtle"
                          />
                        )}
                        <span className="truncate text-body font-medium text-primary">{collection.title}</span>
                      </span>
                      {collection.description && (
                        <span className="mt-0.5 block truncate text-meta text-muted">{collection.description}</span>
                      )}
                      <span className="mt-0.5 block text-meta text-muted">
                        {collection.item_count ?? 0} kayıt
                        {collection.updated_at ? ` · ${relativeTime(collection.updated_at)}` : ""}
                      </span>
                    </span>
                  </a>
                  <span className="flex shrink-0 items-center gap-1.5">
                    <Button
                      size="sm"
                      disabled={!online}
                      onClick={() => {
                        setEditing(collection);
                        setEditName(collection.title);
                      }}
                    >
                      <Pencil size={13} aria-hidden="true" /> {collection.title} koleksiyonunu düzenle
                    </Button>
                    <Button
                      size="sm"
                      disabled={!online || remove.isPending}
                      onClick={() => {
                        void confirmDelete(collection);
                      }}
                    >
                      <Trash2 size={13} aria-hidden="true" /> {collection.title} koleksiyonunu sil
                    </Button>
                  </span>
                </li>
              ))}
            </RowList>
          )}

          {editing && (
            <Section title="Koleksiyonu düzenle" className="max-w-xl">
              <form
                className="flex flex-wrap items-end gap-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (!editName.trim() || !online) return;
                  rename.mutate({ id: editing.id, title: editName.trim() });
                }}
              >
                <Field label="Koleksiyon adını düzenle" className="min-w-0 flex-1">
                  <Input
                    value={editName}
                    onChange={setEditName}
                    disabled={!online || rename.isPending}
                    className="w-full"
                  />
                </Field>
                <Button type="submit" variant="primary" disabled={!online || !editName.trim() || rename.isPending}>
                  Koleksiyon değişikliklerini kaydet
                </Button>
                <Button size="md" disabled={rename.isPending} onClick={() => setEditing(null)}>
                  Vazgeç
                </Button>
              </form>
              {rename.error && (
                <p role="alert" className="mt-2 text-meta text-danger">
                  Koleksiyon güncellenemedi: {rename.error.message}
                </p>
              )}
            </Section>
          )}

          {remove.error && (
            <p role="alert" className="text-meta text-danger">
              Koleksiyon silinemedi: {remove.error.message}
            </p>
          )}
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
