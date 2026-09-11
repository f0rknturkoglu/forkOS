import { BookOpen, Clock, ExternalLink, Star, Trash2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import type { Bookmark } from "@/core/types";
import { COLLECTION_LABELS } from "@/core/types";
import {
  Button,
  Checkbox,
  Chip,
  IconButton,
  cx,
  hostOf,
  relativeTime,
} from "@/core/ui";
import { useOnline } from "@/lib/hooks";

export interface BookmarkCardProps {
  bookmark: Bookmark;
  selected: boolean;
  onToggleSelect: () => void;
  onOpenReader: () => void;
}

export function BookmarkCard({
  bookmark,
  selected,
  onToggleSelect,
  onOpenReader,
}: BookmarkCardProps) {
  const online = useOnline();

  const toggleFavorite = useMutation({
    mutationFn: () =>
      api.patch(`/bookmarks/${bookmark.id}`, { favorite: !isFavorite }),
    onSuccess: () => invalidateAfter("bookmark.write"),
  });

  const toggleReadStatus = useMutation({
    mutationFn: () =>
      api.patch(`/bookmarks/${bookmark.id}`, {
        read_status: bookmark.read_status === "read" ? "unread" : "read",
      }),
    onSuccess: () => invalidateAfter("bookmark.write"),
  });

  const remove = useMutation({
    mutationFn: () => api.del(`/bookmarks/${bookmark.id}`),
    onSuccess: () => invalidateAfter("bookmark.write"),
  });

  const isRead = bookmark.read_status === "read";
  const isFavorite = bookmark.is_favorite ?? bookmark.favorite;
  const host = hostOf(bookmark.url);
  const initial = (host || "B").charAt(0).toUpperCase();

  return (
    <article
      id={bookmark.id}
      className={cx(
        "group relative flex flex-col rounded-card border bg-surface transition overflow-hidden shadow-xs hover:border-strong hover:shadow-sm",
        selected ? "border-accent ring-1 ring-accent" : "border-subtle",
      )}
    >
      {/* Kapak Gorseli / Yer Tutucu */}
      <div className="relative h-44 w-full overflow-hidden bg-surface-sunken border-b border-subtle shrink-0">
        {bookmark.hero_image_url ? (
          <img
            src={bookmark.hero_image_url}
            alt={bookmark.title || host}
            loading="lazy"
            className="h-full w-full object-cover transition duration-300 group-hover:scale-105 cursor-pointer"
            onClick={onOpenReader}
          />
        ) : (
          <button
            type="button"
            onClick={onOpenReader}
            className="flex h-full w-full items-center justify-center bg-surface-sunken hover:bg-surface-hover transition cursor-pointer"
          >
            <span className="text-display-lg font-serif font-bold text-muted/30 uppercase select-none">
              {initial}
            </span>
          </button>
        )}

        {/* Coklu Secim Kutusu */}
        <div className="absolute top-2 left-2 z-sticky rounded-control bg-surface/80 backdrop-blur-xs p-1">
          <Checkbox checked={selected} onChange={onToggleSelect} />
        </div>

        {/* Okuma Suresi Rozeti */}
        {Boolean(bookmark.reading_time_min) && (
          <div className="absolute top-2 right-2 z-sticky">
            <Chip tone="accent">
              <Clock size={10} className="mr-1 inline" />
              {bookmark.reading_time_min} dk
            </Chip>
          </div>
        )}

        {/* Kaydirma Ilerleme Cubugu */}
        {Boolean(bookmark.scroll_progress && bookmark.scroll_progress > 0) && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-surface-sunken">
            <div
              className="h-full bg-accent transition-all"
              style={{ width: `${bookmark.scroll_progress}%` }}
            />
          </div>
        )}
      </div>

      {/* Kart Govdesi */}
      <div className="flex flex-1 flex-col justify-between p-3.5 space-y-3">
        <div className="space-y-1.5">
          {/* Alan Adi ve Tarih */}
          <div className="flex items-center gap-1.5 text-micro text-muted font-mono truncate">
            <span className="truncate">{host}</span>
            <span>·</span>
            <span>{relativeTime(bookmark.saved_at)}</span>
            {bookmark.highlights_count ? (
              <>
                <span>·</span>
                <span className="text-accent">{bookmark.highlights_count} vurgu</span>
              </>
            ) : null}
          </div>

          {/* Baslik */}
          <button
            type="button"
            onClick={onOpenReader}
            className={cx(
              "text-left font-medium text-body leading-snug line-clamp-2 hover:underline focus:outline-none transition-colors",
              isRead ? "text-muted" : "text-primary hover:text-accent",
            )}
          >
            {bookmark.title || bookmark.url}
          </button>

          {/* Not / Ozet */}
          {bookmark.note && (
            <p className="text-meta text-muted line-clamp-2 italic">
              {bookmark.note}
            </p>
          )}

          {/* Etiketler */}
          {Boolean(bookmark.tags && bookmark.tags.length > 0) && (
            <div className="flex flex-wrap items-center gap-1">
              {bookmark.tags.map((tag) => (
                <Chip key={tag}>#{tag}</Chip>
              ))}
            </div>
          )}
        </div>

        {/* Alt Bilgiler ve Hizli Aksiyonlar */}
        <div className="flex items-center justify-between gap-2 border-t border-subtle pt-2 text-meta">
          <div className="flex items-center gap-1 min-w-0">
            <Chip>{COLLECTION_LABELS[bookmark.collection] || bookmark.collection}</Chip>
            {isRead && <Chip tone="ok">Okundu</Chip>}
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <IconButton
              title={isFavorite ? "Favorilerden cikar" : "Favoriye ekle"}
              disabled={!online}
              onClick={() => toggleFavorite.mutate()}
            >
              <Star
                size={14}
                className={isFavorite ? "fill-accent text-accent" : "text-muted"}
              />
            </IconButton>

            <Button
              size="sm"
              variant="ghost"
              disabled={!online}
              title={isRead ? "Okunmadi isaretle" : "Okundu isaretle"}
              onClick={() => toggleReadStatus.mutate()}
            >
              {isRead ? "Geri al" : "Okundu"}
            </Button>

            <a
              href={bookmark.url}
              target="_blank"
              rel="noreferrer"
              title="Orijinal sayfayi yeni sekmede ac"
              className="inline-flex h-8 w-8 items-center justify-center rounded-control text-muted hover:bg-surface-hover hover:text-primary transition"
            >
              <ExternalLink size={14} />
            </a>

            <IconButton
              title="Odak Okuma Modunda Ac"
              onClick={onOpenReader}
            >
              <BookOpen size={14} />
            </IconButton>

            <IconButton
              title="Sil"
              tone="danger"
              disabled={!online}
              onClick={() => remove.mutate()}
            >
              <Trash2 size={14} />
            </IconButton>
          </div>
        </div>
      </div>
    </article>
  );
}
