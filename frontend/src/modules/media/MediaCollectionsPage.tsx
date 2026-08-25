import { invalidateAfter } from "@/core/invalidation";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import type { components } from "@/generated/api-schema";
import { Button, Chip, Empty, Field, Input, PageFrame, PageHeader, RowList, Section } from "@/core/ui";
import { useOnline } from "@/lib/hooks";

type MediaCollection = components["schemas"]["MediaCollectionOut"];

export function MediaCollectionsPage() {
  const online = useOnline();
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<MediaCollection | null>(null);
  const [editName, setEditName] = useState("");

  const { data: collections, isLoading, isFetching, isError, error, refetch } = useQuery({
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
      body: <><span>{collection.title}</span> koleksiyonu ve koleksiyon üyelikleri silinecek; kayıtlar kalır.</>,
      confirmLabel: "Koleksiyonu sil",
      tone: "danger",
    });
    if (confirmed) remove.mutate(collection.id);
  }

  return (
    <PageFrame className="space-y-6">
      <PageHeader eyebrow="Takip" title="Koleksiyonlar" />

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
        {create.error && <p role="alert" className="mt-2 text-meta text-danger">Koleksiyon oluşturulamadı: {create.error.message}</p>}
      </Section>

      {isLoading ? (
        <p role="status" className="text-meta text-muted">Koleksiyonlar yükleniyor…</p>
      ) : isError ? (
        <Empty variant="page" action={<Button size="sm" disabled={isFetching} onClick={() => { void refetch(); }}>Yeniden dene</Button>}>
          Koleksiyonlar yüklenemedi: {error.message}
        </Empty>
      ) : !collections || collections.length === 0 ? (
        <Empty>Henüz koleksiyon yok.</Empty>
      ) : (
        <RowList as="ul">
          {collections.map((collection) => (
            <li key={collection.id} className="flex flex-wrap items-center gap-2 py-2.5">
              <Chip identity="kind-movie" variant="outline">{collection.title}</Chip>
              {collection.description && (
                <span className="min-w-0 flex-1 truncate text-meta text-muted">{collection.description}</span>
              )}
              <span className="ml-auto flex shrink-0 items-center gap-1.5">
                <Button size="sm" disabled={!online} onClick={() => { setEditing(collection); setEditName(collection.title); }}>
                  <Pencil size={13} aria-hidden="true" /> {collection.title} koleksiyonunu düzenle
                </Button>
                <Button size="sm" disabled={!online || remove.isPending} onClick={() => { void confirmDelete(collection); }}>
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
              <Input value={editName} onChange={setEditName} disabled={!online || rename.isPending} className="w-full" />
            </Field>
            <Button type="submit" variant="primary" disabled={!online || !editName.trim() || rename.isPending}>
              Koleksiyon değişikliklerini kaydet
            </Button>
            <Button size="md" disabled={rename.isPending} onClick={() => setEditing(null)}>Vazgeç</Button>
          </form>
          {rename.error && <p role="alert" className="mt-2 text-meta text-danger">Koleksiyon güncellenemedi: {rename.error.message}</p>}
        </Section>
      )}

      {remove.error && <p role="alert" className="text-meta text-danger">Koleksiyon silinemedi: {remove.error.message}</p>}
    </PageFrame>
  );
}
