import { useEffect, useMemo, useRef, useState } from "react";
import { Bell, X } from "lucide-react";
import { Checkbox, Chip, FilterChip, IconButton, Input, Metric, MetricStrip, Select, Section, cx } from "@/core/ui";
import type { MediaItem, MediaStats } from "@/core/types";
import { CollectionPicker } from "./CollectionPicker";
import { MediaActionsMenu } from "./MediaActionsMenu";
import { measureLabel } from "./MediaSessionTransfer";
import {
  KIND_LABELS,
  KINDS,
  KindIcon,
  ProviderLogo,
  STATUSES,
  STATUS_LABELS,
  kindBg,
  mediaCoverUrl,
  mediaProvider,
  progressPct,
  providerChip,
  providerIdentity,
  providerLabel,
  statusLabel,
} from "./shared";

/** Poster kartının ihtiyaç duyduğu alanlar; sayfa da bu tipi kullanır. */
export type MediaPosterItem = Pick<
  MediaItem,
  | "id"
  | "title"
  | "kind"
  | "status"
  | "progress"
  | "total"
  | "cover_path"
  | "cover_url"
  | "meta"
  | "progress_measure"
  | "provider"
  | "provider_id"
  | "provider_ids"
  | "monitored"
  | "release_date"
>;

type PosterItem = MediaPosterItem;

type PosterStats = Pick<MediaStats, "total" | "in_progress" | "completed" | "planned">;

const QUICK_PROGRESS_STATUSES = new Set(["planned", "in_progress", "paused"]);

/** Durum -> chip tonu; rozetler listede taranirken anlam tasir. */
const STATUS_TONES: Record<string, "neutral" | "accent" | "ok" | "warn" | "danger"> = {
  planned: "neutral",
  in_progress: "accent",
  paused: "warn",
  completed: "ok",
  dropped: "danger",
};

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

/* ══════════════════════════════════════════════════════════════════════
   Kütüphane filtreleri (URL'e MediaPage yazar; panel yalnız sunum yapar)
   ══════════════════════════════════════════════════════════════════════ */

/** Kütüphane filtresinin URL'e yansıyan tüm alanları. */
export type MediaFilterValues = {
  kind: string;
  status: string;
  provider: string;
  owned: boolean;
  favorite: boolean;
  monitored: boolean;
  collectionId: string;
  tag: string;
  sort: string;
};

export const EMPTY_MEDIA_FILTERS: MediaFilterValues = {
  kind: "",
  status: "",
  provider: "",
  owned: false,
  favorite: false,
  monitored: false,
  collectionId: "",
  tag: "",
  sort: "",
};

/** Sıralama seçenekleri; boş değer backend varsayılanıdır. */
const MEDIA_SORTS: [string, string][] = [
  ["", "Varsayılan"],
  ["updated", "Güncellenme"],
  ["created", "Eklenme"],
  ["title", "Başlık"],
  ["score", "Puan"],
  ["progress", "İlerleme"],
  ["relevance", "Alaka"],
];

export function MediaFilterPanel({
  values,
  onChange,
  providers,
  collections,
}: {
  values: MediaFilterValues;
  onChange: (patch: Partial<MediaFilterValues>) => void;
  /** Mevcut kayıtlardan türetilen sağlayıcı kimlikleri. */
  providers: string[];
  collections: { id: string; title: string }[];
}) {
  // Etiket alanı her tuşta istek atmasın: yazarken yerel, odak kaybında URL'e.
  const [tagDraft, setTagDraft] = useState(values.tag);
  useEffect(() => setTagDraft(values.tag), [values.tag]);

  return (
    <div data-media-filters>
      <Section title="Filtreler" bodyClassName="space-y-3">
        <div role="group" aria-label="Tür filtresi" className="flex flex-wrap gap-1.5">
          <FilterChip label="Tümü" active={values.kind === ""} onClick={() => onChange({ kind: "" })} />
          {KINDS.map((kind) => (
            <FilterChip
              key={kind}
              label={KIND_LABELS[kind]}
              active={values.kind === kind}
              onClick={() => onChange({ kind: values.kind === kind ? "" : kind })}
            />
          ))}
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <label className="flex flex-col gap-1">
            <span className="label-caps text-muted">Durum</span>
            <Select value={values.status} ariaLabel="Durum filtresi" onChange={(status) => onChange({ status })}>
              <option value="">Tüm durumlar</option>
              {STATUSES.map((status) => (
                <option key={status} value={status}>
                  {STATUS_LABELS[status]}
                </option>
              ))}
            </Select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="label-caps text-muted">Sağlayıcı</span>
            <Select
              value={values.provider}
              ariaLabel="Sağlayıcı filtresi"
              onChange={(provider) => onChange({ provider })}
            >
              <option value="">Tüm sağlayıcılar</option>
              {providers.map((provider) => (
                <option key={provider} value={provider}>
                  {providerLabel(provider) ?? provider}
                </option>
              ))}
            </Select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="label-caps text-muted">Koleksiyon</span>
            <Select
              value={values.collectionId}
              ariaLabel="Koleksiyon filtresi"
              onChange={(collectionId) => onChange({ collectionId })}
            >
              <option value="">Tüm koleksiyonlar</option>
              {collections.map((collection) => (
                <option key={collection.id} value={collection.id}>
                  {collection.title}
                </option>
              ))}
            </Select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="label-caps text-muted">Etiket</span>
            <Input
              value={tagDraft}
              onChange={setTagDraft}
              onBlur={(value) => onChange({ tag: value.trim() })}
              onKeyDown={(event) => {
                if (event.key === "Enter") onChange({ tag: tagDraft.trim() });
              }}
              placeholder="Etiket"
              ariaLabel="Etiket filtresi"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="label-caps text-muted">Sıralama</span>
            <Select value={values.sort} ariaLabel="Sıralama" onChange={(sort) => onChange({ sort })}>
              {MEDIA_SORTS.map(([value, label]) => (
                <option key={value || "default"} value={value}>
                  {label}
                </option>
              ))}
            </Select>
            <span className="text-micro text-muted">Alaka sıralaması yalnızca arama sorgusu varken anlamlıdır.</span>
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <Checkbox checked={values.owned} onChange={(owned) => onChange({ owned })} label="Sahip olduklarım" />
          <Checkbox checked={values.favorite} onChange={(favorite) => onChange({ favorite })} label="Favoriler" />
          <Checkbox
            checked={values.monitored}
            onChange={(monitored) => onChange({ monitored })}
            label="Takip ettiklerim"
          />
        </div>
      </Section>
    </div>
  );
}

/** Seçili filtreleri tek satırda, tek tek silinebilir özetler. */
export function MediaActiveFilters({
  values,
  query,
  collectionTitle,
  onRemove,
  onClear,
}: {
  values: MediaFilterValues;
  query: string;
  collectionTitle?: string;
  onRemove: (key: keyof MediaFilterValues | "q") => void;
  onClear: () => void;
}) {
  const chips: [keyof MediaFilterValues | "q", string][] = [];
  if (query) chips.push(["q", `Arama: ${query}`]);
  if (values.kind) chips.push(["kind", `Tür: ${KIND_LABELS[values.kind] ?? values.kind}`]);
  if (values.status) chips.push(["status", `Durum: ${STATUS_LABELS[values.status] ?? values.status}`]);
  if (values.provider) chips.push(["provider", `Sağlayıcı: ${providerLabel(values.provider) ?? values.provider}`]);
  if (values.collectionId) chips.push(["collectionId", `Koleksiyon: ${collectionTitle ?? values.collectionId}`]);
  if (values.tag) chips.push(["tag", `Etiket: ${values.tag}`]);
  if (values.owned) chips.push(["owned", "Sahip olduklarım"]);
  if (values.favorite) chips.push(["favorite", "Favoriler"]);
  if (values.monitored) chips.push(["monitored", "Takip ettiklerim"]);
  if (values.sort)
    chips.push(["sort", `Sıralama: ${MEDIA_SORTS.find(([value]) => value === values.sort)?.[1] ?? values.sort}`]);

  if (!chips.length) return null;

  return (
    <div data-media-active-filters className="flex flex-wrap items-center gap-2">
      {chips.map(([key, label]) => (
        <button
          key={key}
          type="button"
          aria-label={`${label} filtresini kaldır`}
          onClick={() => onRemove(key)}
          className="inline-flex h-7 items-center gap-1 rounded-control border border-subtle bg-surface px-2 text-micro text-secondary transition hover:border-strong hover:text-primary focus:outline-none focus:ring-1 focus:ring-accent"
        >
          <span>{label}</span>
          <X size={11} aria-hidden="true" />
        </button>
      ))}
      <button
        type="button"
        onClick={onClear}
        className="text-meta text-accent transition hover:underline focus:outline-none focus:ring-1 focus:ring-accent"
      >
        Filtreleri temizle
      </button>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════
   Poster kartları
   ══════════════════════════════════════════════════════════════════════ */

function PosterCover({ item, href }: { item: PosterItem; href: string }) {
  const url = mediaCoverUrl(item);
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const alt = `${item.title} kapağı`;
  const coverClass = "aspect-[2/3] w-full rounded-card border border-subtle object-cover";
  return (
    <a
      href={href}
      aria-label={`${item.title} detayını aç`}
      className="block rounded-card focus:outline-none focus:ring-2 focus:ring-accent"
    >
      {url && failedUrl !== url ? (
        <img src={url} alt={alt} loading="lazy" onError={() => setFailedUrl(url)} className={coverClass} />
      ) : (
        <div
          role="img"
          aria-label={alt}
          className={cx("flex items-center justify-center bg-surface-sunken  text-title text-secondary", coverClass)}
        >
          {(item.title.trim().charAt(0) || "?").toUpperCase()}
        </div>
      )}
    </a>
  );
}

/** Yayın yılı: kanonik `release_date`, yoksa legacy `meta.year`. */
function itemYear(item: PosterItem): string | null {
  const date = item.release_date ?? "";
  const fromDate = /^(\d{4})/.exec(date)?.[1];
  if (fromDate) return fromDate;
  const legacy = item.meta?.year;
  return typeof legacy === "number" || typeof legacy === "string" ? String(legacy) : null;
}

function MediaPoster({
  item,
  online,
  onQuick,
  onTrash,
}: {
  item: PosterItem;
  online: boolean;
  onQuick: (item: PosterItem) => void;
  onTrash: (item: PosterItem) => void;
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const href = `#/media/${encodeURIComponent(item.id)}`;
  const provider = mediaProvider(item);
  const percent = progressPct(item);
  const year = itemYear(item);
  const progress = item.progress ?? 0;
  const hasUsableProgress = Number.isFinite(progress);
  const canQuick =
    QUICK_PROGRESS_STATUSES.has(item.status) &&
    hasUsableProgress &&
    typeof item.total === "number" &&
    Number.isFinite(item.total) &&
    item.total > 0 &&
    progress < item.total;
  const quickLabel = `${item.title} için +1 ${measureLabel(item.progress_measure ?? null)}`;

  return (
    <li data-media-poster className="min-w-0">
      <div className="relative">
        <PosterCover item={item} href={href} />
        <div className="absolute right-2 top-2">
          <MediaActionsMenu
            item={item}
            onTrash={() => onTrash(item)}
            onAddToCollection={() => setPickerOpen(true)}
            onQuick={canQuick ? () => onQuick(item) : undefined}
            quickLabel={canQuick ? quickLabel : undefined}
            disabled={!online}
          />
          <CollectionPicker
            itemId={item.id}
            currentIds={[]}
            open={pickerOpen}
            onOpenChange={setPickerOpen}
            hideTrigger
            align="right"
          />
        </div>
      </div>
      <div className="mt-2 min-w-0">
        <a
          href={href}
          title={item.title}
          className="line-clamp-2 block break-words text-body font-medium text-primary hover:text-accent focus:outline-none focus:underline"
        >
          {item.title}
        </a>
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-meta">
          <Chip
            identity={"kind-" + item.kind}
            variant="outline"
            size="xs"
            icon={<KindIcon kind={item.kind} size={11} />}
            title={KIND_LABELS[item.kind] ?? item.kind}
            aria-label={KIND_LABELS[item.kind] ?? item.kind}
          >
            <span className="sr-only">{KIND_LABELS[item.kind] ?? item.kind}</span>
          </Chip>
          <Chip tone={STATUS_TONES[item.status] ?? "neutral"} variant="soft" size="xs">
            {statusLabel(item.kind, item.status)}
          </Chip>
          {provider && (
            <Chip
              identity={providerIdentity(provider)}
              variant="outline"
              size="xs"
              icon={<ProviderLogo provider={provider} size={11} />}
              title={providerLabel(provider) ?? provider}
            >
              {providerLabel(provider)}
            </Chip>
          )}
          {year && <span className="numeral text-muted">{year}</span>}
          {item.monitored && (
            <Chip tone="accent" variant="soft" size="xs" icon={<Bell size={10} aria-hidden="true" />}>
              <span className="sr-only">Takip ediliyor</span>
            </Chip>
          )}
        </div>
        {percent !== null && (
          <div className="mt-2 flex items-center gap-2">
            <div
              role="progressbar"
              aria-label={`${item.title} ilerlemesi`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={percent}
              className="h-1 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-sunken"
            >
              <div className={cx("h-full", kindBg(item.kind))} style={{ width: `${percent}%` }} />
            </div>
            <span className="numeral text-micro text-secondary">{percent}%</span>
            <span className="numeral text-micro text-muted">
              {progress}/{item.total}
            </span>
          </div>
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
  busy = false,
}: {
  items: PosterItem[];
  online: boolean;
  onQuick: (item: PosterItem) => void;
  onTrash: (item: PosterItem) => void;
  /** Arka planda tazelenirken eski grid korunur; ekran okuyucuya bildirilir. */
  busy?: boolean;
}) {
  // Cursor sayfalama/provider tekrari ayni id'yi iki kez getirebilir; tekrar
  // eden id'ler React reconciliation'i bozup 'duplicate key' uyarisi uretiyor.
  // Ilk gorunum korunur, sonraki tekrarlar atilir.
  const unique = useMemo(() => {
    const seen = new Set<string>();
    const result: PosterItem[] = [];
    for (const item of items) {
      if (!seen.has(item.id)) {
        seen.add(item.id);
        result.push(item);
      }
    }
    return result;
  }, [items]);
  return (
    <ul
      data-media-grid
      aria-busy={busy || undefined}
      className="grid grid-cols-[repeat(auto-fill,minmax(156px,1fr))] gap-x-4 gap-y-6 sm:grid-cols-[repeat(auto-fill,minmax(176px,1fr))]"
    >
      {unique.map((item) => (
        <MediaPoster key={item.id} item={item} online={online} onQuick={onQuick} onTrash={onTrash} />
      ))}
    </ul>
  );
}

export function MediaPosterGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div role="status" aria-label="Kütüphane yükleniyor">
      <span className="sr-only">Kütüphane yükleniyor…</span>
      <ul
        data-media-grid
        aria-hidden="true"
        className="grid grid-cols-[repeat(auto-fill,minmax(156px,1fr))] gap-x-4 gap-y-6 sm:grid-cols-[repeat(auto-fill,minmax(176px,1fr))]"
      >
        {Array.from({ length: count }, (_, index) => (
          <li key={index} data-media-poster-skeleton className="min-w-0 motion-safe:animate-pulse">
            <div className="aspect-[2/3] w-full rounded-card border border-subtle bg-surface-sunken" />
            <div className="mt-2 h-4 w-3/4 rounded bg-surface-sunken" />
            <div className="mt-2 h-5 w-1/2 rounded bg-surface-sunken" />
          </li>
        ))}
      </ul>
    </div>
  );
}
