import { invalidateAfter } from "@/core/invalidation";
import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Bookmark, Star, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { savedViewsKey } from "@/core/savedViews";
import { Button, IconButton, Input, Popover, cx } from "@/core/ui";

/** Kayıtlı görünüm satırı — GET /views yanıtıyla birebir. */
export interface SavedViewRow {
  id: string;
  name: string;
  module: string;
  filter: Record<string, unknown>;
  sort: string | null;
  pinned: boolean;
  position: number;
}

interface SavedViewPickerProps {
  /**
   * Görünümlerin bağlı olduğu modül kimliği = FRONTEND registry kimliği
   * ("bookmarks", "todo", "opportunity"...). Sidebar aynı kimliği
   * modül rotasına çevirir; backend bu alanı opak taşır.
   */
  module: string;
  /** Kaydedilecek mevcut filtre durumu (düz nesne; modüle özgü anahtarlar). */
  filters: unknown;
  /** Kayıtlı görünüm seçilince filtresi uygulanır; görünüm de verilir. */
  onApply: (filters: Record<string, unknown>, view: SavedViewRow) => void;
}

/** Kaydedilebilir filtre: düz nesneye indir; boş/undefined değerleri at. */
function cleanFilters(filters: unknown): Record<string, unknown> {
  if (!filters || typeof filters !== "object" || Array.isArray(filters)) return {};
  return Object.fromEntries(
    Object.entries(filters as Record<string, unknown>).filter(
      ([, value]) => value !== undefined && value !== null && value !== "",
    ),
  );
}

/**
 * Kayıtlı görünüm seçici. Toolbar'a gömülen küçük popover: mevcut filtreyi
 * ad vererek kaydeder, kayıtlı görünümleri uygular, sabitler ve siler.
 * Filtre DSL'i modüle özgüdür — bu bileşen opak davranır; sayfa onApply ile
 * tanıdığı anahtarları kendi state'ine uygular (bilinmeyenler yok sayılır).
 */
export function SavedViewPicker({ module, filters, onApply }: SavedViewPickerProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  const { data } = useQuery({
    queryKey: savedViewsKey(module),
    queryFn: () => api.get<SavedViewRow[]>(`/views?module=${encodeURIComponent(module)}`),
  });
  // Beklenmeyen gövde (nesne/null) çalışma alanını çökertmez: liste boş sayılır.
  const views = Array.isArray(data) ? data : [];

  const refresh = () => invalidateAfter("views.write");

  const saveView = useMutation({
    mutationFn: (payload: { name: string }) =>
      api.post<SavedViewRow>("/views", {
        name: payload.name,
        module,
        filter: cleanFilters(filters),
      }),
    onSuccess: () => {
      setName("");
      setOpen(false);
      refresh();
    },
  });
  const togglePin = useMutation({
    mutationFn: (view: SavedViewRow) => api.patch<SavedViewRow>(`/views/${view.id}`, { pinned: !view.pinned }),
    onSuccess: refresh,
  });
  const removeView = useMutation({
    mutationFn: (id: string) => api.del(`/views/${id}`),
    onSuccess: refresh,
  });

  /** Görünüm silme geri alınamaz (çöp kutusu yok): onay ister (§54). */
  async function requestRemove(view: SavedViewRow) {
    const ok = await confirmDialog({
      title: `"${view.name}" görünümü silinsin mi?`,
      body: "Kayıtlı filtre silinir; aynı filtreyi yeniden kaydetmen gerekir.",
      confirmLabel: "Görünümü sil",
    });
    if (ok) removeView.mutate(view.id);
  }

  const activeFilter = JSON.stringify(cleanFilters(filters));

  return (
    <div ref={rootRef} className="relative">
      <Button size="sm" ariaLabel="Kayıtlı görünümler" onClick={() => setOpen((value) => !value)}>
        <Bookmark size={14} className="text-icon" />
        Görünümler
        {views.length > 0 && (
          <span className="rounded border border-accent-border bg-accent-surface px-1.5 text-micro leading-5 text-accent">
            {views.length}
          </span>
        )}
      </Button>

      <Popover
        open={open}
        onClose={() => setOpen(false)}
        anchorRef={rootRef}
        ariaLabel="Kayıtlı görünümler"
        className="right-0 top-11 w-80"
      >
        <div className="flex items-center gap-2 border-b border-subtle px-3 py-2.5">
          <Star size={13} className="text-icon" />
          <span className="text-heading text-primary">Görünümler</span>
        </div>

        {/* Mevcut filtreyi ad vererek kaydet */}
        <div className="flex items-center gap-2 border-b border-subtle px-3 py-2.5">
          <Input
            value={name}
            onChange={setName}
            placeholder="Görünüm adı…"
            ariaLabel="Görünüm adı"
            className="min-w-0 flex-1"
            onKeyDown={(e) => {
              if (e.key === "Enter" && name.trim()) saveView.mutate({ name: name.trim() });
            }}
          />
          <Button
            size="sm"
            disabled={!name.trim() || saveView.isPending}
            onClick={() => saveView.mutate({ name: name.trim() })}
          >
            Kaydet
          </Button>
        </div>

        {/* Kayıtlı görünümler */}
        {views.length === 0 ? (
          <p className="px-3 py-3 text-meta text-muted">Kayıtlı görünüm yok.</p>
        ) : (
          <ul className="max-h-72 overflow-y-auto py-1">
            {views.map((view) => {
              const active = JSON.stringify(view.filter ?? {}) === activeFilter;
              return (
                <li key={view.id} className="group flex items-center gap-1 px-2 py-1">
                  <button
                    type="button"
                    onClick={() => {
                      onApply(view.filter ?? {}, view);
                      setOpen(false);
                    }}
                    className={cx(
                      "h-8 min-w-0 flex-1 truncate rounded-control px-2 text-left text-meta transition",
                      active
                        ? "bg-accent-surface font-medium text-accent"
                        : "text-secondary hover:bg-surface-hover hover:text-primary",
                    )}
                  >
                    {view.name}
                  </button>
                  <IconButton
                    title={view.pinned ? "Sabitlemeyi kaldır" : "Sabitle"}
                    disabled={togglePin.isPending}
                    onClick={() => togglePin.mutate(view)}
                  >
                    <Star size={14} className={view.pinned ? "fill-current text-accent" : ""} />
                  </IconButton>
                  <IconButton
                    title={`"${view.name}" görünümünü sil`}
                    tone="danger"
                    disabled={removeView.isPending}
                    onClick={() => void requestRemove(view)}
                  >
                    <Trash2 size={14} />
                  </IconButton>
                </li>
              );
            })}
          </ul>
        )}
      </Popover>
    </div>
  );
}
