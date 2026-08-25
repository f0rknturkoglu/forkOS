import { Plus } from "lucide-react";
import { Metric, MetricStrip, cx } from "@/core/ui";
import type { MediaItem, MediaStats } from "@/core/types";
import { MediaActionsMenu } from "./MediaActionsMenu";
import {
  KIND_LABELS,
  KINDS,
  STATUSES,
  STATUS_LABELS,
  kindBg,
  kindChip,
  mediaCoverUrl,
  mediaProvider,
  progressPct,
  providerChip,
  providerLabel,
} from "./shared";

type PosterItem = Pick<
  MediaItem,
  "id" | "title" | "kind" | "status" | "progress" | "total" | "cover_path" | "cover_url"
  | "meta" | "provider" | "provider_id" | "provider_ids"
>;

type PosterStats = Pick<MediaStats, "total" | "in_progress" | "completed" | "planned">;
const QUICK_PROGRESS_STATUSES = new Set(["planned", "in_progress", "paused"]);

export function MediaMetrics({ stats }: { stats?: PosterStats | null }) {
  return (
    <div data-media-metrics className="grid-cols-2 sm:grid-cols-4">
      <MetricStrip className="grid-cols-2 sm:grid-cols-4">
        <Metric label="Toplam" value={stats?.total ?? 0} />
        <Metric label="Devam ediyor" value={stats?.in_progress ?? 0} />
        <Metric label="Tamamlandı" value={stats?.completed ?? 0} />
        <Metric label="Planlandı" value={stats?.planned ?? 0} />
      </MetricStrip>
    </div>
  );
}

export function MediaLibraryControls({
  kind,
  status,
  onKindChange,
  onStatusChange,
}: {
  kind: string;
  status: string;
  onKindChange: (kind: string) => void;
  onStatusChange: (status: string) => void;
}) {
  return (
    <div data-media-library-controls className="flex flex-wrap items-center gap-2">
      <div className="flex max-w-full gap-1.5 overflow-x-auto" role="group" aria-label="Tür filtresi">
        {["", ...KINDS].map((value) => (
          <button
            key={value || "all"}
            type="button"
            aria-pressed={kind === value}
            onClick={() => onKindChange(value)}
            className={cx(
              "h-7 shrink-0 rounded-control border px-2.5 text-meta transition",
              kind === value ? "border-accent bg-accent-surface text-accent" : value
                ? cx(kindChip(value), "hover:opacity-80")
                : "border-subtle text-secondary hover:border-strong hover:text-primary",
            )}
          >
            {value ? KIND_LABELS[value] ?? value : "Tümü"}
          </button>
        ))}
      </div>
      <label className="sr-only" htmlFor="media-library-status">Durum filtresi</label>
      <select
        id="media-library-status"
        value={status}
        onChange={(event) => onStatusChange(event.target.value)}
        className="h-8 rounded-control border border-subtle bg-surface px-2 text-meta text-primary outline-none focus:border-accent"
      >
        <option value="">Tüm durumlar</option>
        {STATUSES.map((value) => <option key={value} value={value}>{STATUS_LABELS[value]}</option>)}
      </select>
    </div>
  );
}

function PosterCover({ item, href }: { item: PosterItem; href: string }) {
  const url = mediaCoverUrl(item);
  const alt = `${item.title} kapağı`;
  const coverClass = "aspect-[2/3] w-full rounded-card border border-subtle object-cover";
  return (
    <a href={href} aria-label={`${item.title} detayını aç`} className="block rounded-card focus:outline-none focus:ring-2 focus:ring-accent">
      {url ? (
        <img src={url} alt={alt} loading="lazy" className={coverClass} />
      ) : (
        <div role="img" aria-label={alt} className={cx("flex items-center justify-center bg-surface-sunken font-serif text-title text-secondary", coverClass)}>
          {(item.title.trim().charAt(0) || "?").toUpperCase()}
        </div>
      )}
    </a>
  );
}

function MediaPoster({ item, online, onQuick, onTrash }: {
  item: PosterItem;
  online: boolean;
  onQuick: (item: PosterItem) => void;
  onTrash: (item: PosterItem) => void;
}) {
  const href = `#/media/${encodeURIComponent(item.id)}`;
  const provider = mediaProvider(item);
  const percent = progressPct(item);
  const progress = item.progress ?? 0;
  const hasUsableProgress = Number.isFinite(progress);
  const canQuick = QUICK_PROGRESS_STATUSES.has(item.status) && hasUsableProgress
    && typeof item.total === "number" && Number.isFinite(item.total) && item.total > 0 && progress < item.total;

  return (
    <li data-media-poster className="min-w-0">
      <div className="relative">
        <PosterCover item={item} href={href} />
        <div className="absolute right-2 top-2">
          <MediaActionsMenu item={item} onTrash={() => onTrash(item)} disabled={!online} />
        </div>
      </div>
      <div className="mt-2 min-w-0">
        <a href={href} className="block truncate text-body font-medium text-primary hover:text-accent focus:outline-none focus:underline">
          {item.title}
        </a>
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-meta">
          <span className={cx("rounded border px-1.5 py-0.5", kindChip(item.kind))}>{KIND_LABELS[item.kind] ?? item.kind}</span>
          {provider && <span className={cx("rounded border px-1.5 py-0.5", providerChip(provider))}>{providerLabel(provider)}</span>}
          {percent !== null && <span className="numeral text-muted">{item.progress ?? 0}/{item.total}</span>}
        </div>
        {percent !== null && (
          <div
            role="progressbar"
            aria-label={`${item.title} ilerlemesi`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={percent}
            className="mt-2 h-px overflow-hidden bg-surface-sunken"
          >
            <div className={cx("h-full", kindBg(item.kind))} style={{ width: `${percent}%` }} />
          </div>
        )}
        {canQuick && (
          <button
            type="button"
            disabled={!online}
            aria-label={`${item.title} ilerlemesini bir artır`}
            onClick={() => onQuick(item)}
            className="mt-2 flex h-7 w-7 items-center justify-center rounded-control border border-subtle text-secondary transition hover:border-strong hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Plus size={14} aria-hidden="true" />
          </button>
        )}
      </div>
    </li>
  );
}

export function MediaPosterGrid({
  items,
  online,
  onQuick,
  onTrash,
}: {
  items: PosterItem[];
  online: boolean;
  onQuick: (item: PosterItem) => void;
  onTrash: (item: PosterItem) => void;
}) {
  return (
    <ul
      data-media-grid
      className="grid grid-cols-[repeat(auto-fill,minmax(156px,1fr))] gap-x-4 gap-y-6 sm:grid-cols-[repeat(auto-fill,minmax(176px,1fr))]"
    >
      {items.map((item) => <MediaPoster key={item.id} item={item} online={online} onQuick={onQuick} onTrash={onTrash} />)}
    </ul>
  );
}
