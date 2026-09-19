import { useMemo, useState } from "react";
import { MEDIA_COLLECTIONS_QUERY_KEY } from "./queries";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, Library, Plus } from "lucide-react";

import { api, qs } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import type { components } from "@/generated/api-schema";
import { Button, Checkbox, Chip, Input, Popover, cx } from "@/core/ui";
import { useOnline } from "@/lib/hooks";

type MediaCollection = components["schemas"]["MediaCollectionOut"];

/**
 * Kaydi birden fazla koleksiyona ekleyip cikarabilen arama destekli secici.
 *
 * Ayni akistan yeni koleksiyon olusturulabilir. Uc yuzey bunu kullanir
 * (detay sayfasi, poster karti menusu, ekleme akisi) -- kural 17: uc noktalar
 * (`POST/DELETE /media/collections/{cid}/items/{item_id}`) tek yerden cagrilir.
 */
export function CollectionPicker({
  itemId,
  currentIds,
  size = "sm",
  align = "left",
  label = "Koleksiyona ekle",
  onChanged,
  open: controlledOpen,
  onOpenChange,
  hideTrigger = false,
}: {
  itemId: string;
  currentIds: string[];
  size?: "sm" | "md";
  align?: "left" | "right";
  label?: string;
  onChanged?: () => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  hideTrigger?: boolean;
}) {
  const online = useOnline();
  const [internalOpen, setInternalOpen] = useState(false);
  const open = controlledOpen !== undefined ? controlledOpen : internalOpen;
  const setOpen = (value: boolean | ((prev: boolean) => boolean)) => {
    const next = typeof value === "function" ? value(open) : value;
    if (controlledOpen === undefined) setInternalOpen(next);
    onOpenChange?.(next);
  };
  const [term, setTerm] = useState("");
  const [newTitle, setNewTitle] = useState("");

  const collections = useQuery({
    queryKey: MEDIA_COLLECTIONS_QUERY_KEY,
    queryFn: () => api.get<MediaCollection[]>("/media/collections"),
    enabled: open,
  });

  const refresh = () => {
    // Koleksiyon listesi ["media","collections"] anahtariyla durur; "media.write"
    // ailesi ["media"] onekini tazeledigi icin ek tazeleme GEREKMEZ
    // (kural 14: ham invalidateQueries yasak).
    invalidateAfter("media.write");
    onChanged?.();
  };

  const membership = useMemo(() => new Set(currentIds.map((id) => id.toLowerCase())), [currentIds]);

  const add = useMutation({
    mutationFn: (collectionId: string) =>
      api.post(`/media/collections/${encodeURIComponent(collectionId)}/items/${encodeURIComponent(itemId)}`, {}),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (collectionId: string) =>
      api.del(`/media/collections/${encodeURIComponent(collectionId)}/items/${encodeURIComponent(itemId)}`),
    onSuccess: refresh,
  });
  const create = useMutation({
    mutationFn: async (title: string) => {
      const created = await api.post<MediaCollection>("/media/collections", { title });
      await api.post(`/media/collections/${encodeURIComponent(created.id)}/items/${encodeURIComponent(itemId)}`, {});
      return created;
    },
    onSuccess: () => {
      setNewTitle("");
      refresh();
    },
  });

  const busy = add.isPending || remove.isPending || create.isPending;
  const failure = add.error ?? remove.error ?? create.error;
  const visible = (collections.data ?? []).filter((collection) =>
    collection.title.toLocaleLowerCase("tr").includes(term.trim().toLocaleLowerCase("tr")),
  );

  function toggle(collection: MediaCollection) {
    if (busy || !online) return;
    if (membership.has(collection.id.toLowerCase())) remove.mutate(collection.id);
    else add.mutate(collection.id);
  }

  return (
    <span className="relative inline-flex">
      {!hideTrigger && (
        <Button
          size={size}
          aria-haspopup="dialog"
          aria-expanded={open}
          aria-label={label}
          title={label}
          disabled={!online}
          onClick={() => setOpen((prev) => !prev)}
        >
          <Library size={13} aria-hidden="true" />
          {label}
        </Button>
      )}
      <Popover
        open={open}
        onClose={() => setOpen(false)}
        role="dialog"
        ariaLabel={label}
        className={cx("mt-1 w-72 p-2", align === "right" ? "right-0" : "left-0")}
      >
        <Input
          value={term}
          onChange={setTerm}
          placeholder="Koleksiyon ara"
          ariaLabel="Koleksiyon ara"
          className="mb-2 w-full"
        />
        {collections.isLoading ? (
          <p role="status" className="px-1 py-2 text-meta text-muted">
            Koleksiyonlar yükleniyor…
          </p>
        ) : collections.isError ? (
          <p role="alert" className="px-1 py-2 text-meta text-danger">
            Koleksiyonlar yüklenemedi: {collections.error.message}
          </p>
        ) : visible.length === 0 ? (
          <p className="px-1 py-2 text-meta text-muted">
            {term.trim() ? "Eşleşen koleksiyon yok." : "Henüz koleksiyon yok."}
          </p>
        ) : (
          <ul className="max-h-56 space-y-0.5 overflow-y-auto">
            {visible.map((collection) => {
              const checked = membership.has(collection.id.toLowerCase());
              return (
                <li key={collection.id}>
                  <Checkbox
                    checked={checked}
                    disabled={busy || !online}
                    onChange={() => toggle(collection)}
                    className="w-full rounded-control px-1.5 py-1 hover:bg-surface-hover"
                    label={
                      <span className="flex min-w-0 flex-1 items-center gap-2">
                        <span className="min-w-0 flex-1 truncate">{collection.title}</span>
                        {collection.item_count > 0 && (
                          <Chip tone="neutral" variant="outline" size="sm">
                            {collection.item_count}
                          </Chip>
                        )}
                        {checked && <Check size={13} aria-hidden="true" className="text-ok" />}
                      </span>
                    }
                  />
                </li>
              );
            })}
          </ul>
        )}

        <form
          className="mt-2 flex items-center gap-1.5 border-t border-subtle pt-2"
          onSubmit={(event) => {
            event.preventDefault();
            const title = newTitle.trim();
            if (!title || busy || !online) return;
            create.mutate(title);
          }}
        >
          <Input
            value={newTitle}
            onChange={setNewTitle}
            placeholder="Yeni koleksiyon adı"
            ariaLabel="Yeni koleksiyon adı"
            disabled={!online || busy}
            className="min-w-0 flex-1"
          />
          <Button
            type="submit"
            size="sm"
            variant="primary"
            disabled={!online || busy || !newTitle.trim()}
            aria-label="Koleksiyon oluştur ve ekle"
            title="Koleksiyon oluştur ve ekle"
          >
            <Plus size={13} aria-hidden="true" />
          </Button>
        </form>

        {!online && (
          <p role="status" className="mt-1 px-1 text-micro text-muted">
            Çevrimdışıyken koleksiyon değiştirilemez.
          </p>
        )}
        {failure && (
          <p role="alert" className="mt-1 px-1 text-meta text-danger">
            {failure.message}
          </p>
        )}
      </Popover>
    </span>
  );
}
