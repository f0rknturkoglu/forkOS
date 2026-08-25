import { Bookmark, ExternalLink, MapPin, RotateCcw, Trash2 } from "lucide-react";
import {Button, Chip, Select, cx, relativeTime} from "@/core/ui";
import type { Opportunity } from "@/core/types";
import {
  REMOTE_LABELS, SCORE_TONE, STATUSES,
  daysLeft, kindLabel, remoteKind, scoreBand, statusLabel,
} from "./labels";
import { sourceLabel } from "@/core/labels";
import type { RemoteKind } from "./labels";

export function FilterChip({
  label, count, active, onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cx(
        "flex h-8 items-center gap-2 rounded-control border px-3 text-meta transition",
        active
          ? "border-accent bg-accent-surface font-medium text-accent"
          : "border-subtle bg-surface text-secondary hover:bg-surface-hover hover:text-primary",
      )}
    >
      <span>{label}</span>
      <span className={cx("numeral text-meta", active ? "text-accent" : "text-muted")}>{count}</span>
    </button>
  );
}

export function OpportunityCard({
  item, onOpen, onStatus, onTrash, onRestore, onDelete, disabled, isTrash,
  layout = "rows", onSource, onRemote, onKind, sourceActive = false, remoteActive = false,
  onSave,
}: {
  item: Opportunity;
  onOpen: () => void;
  onStatus: (status: string) => void;
  onTrash: () => void;
  onRestore: () => void;
  onDelete: () => void;
  disabled: boolean;
  isTrash: boolean;
  /** "rows" yatay satir, "grid" karesel kart. */
  layout?: "rows" | "grid";
  onSource?: (source: string) => void;
  onRemote?: (kind: RemoteKind) => void;
  onKind?: (kind: string) => void;
  sourceActive?: boolean;
  remoteActive?: boolean;
  /** İlanı kütüphaneye kaydet ("Kaydet" aksiyonu; url yoksa buton çizilmez). */
  onSave?: () => void;
}) {
  const left = daysLeft(item.deadline_at);
  const urgent = left !== null && left <= 7;
  const band = scoreBand(item.score);
  const rk = remoteKind(item.remote);

  function chip(active: boolean) {
    return cx(
      "flex h-6 items-center rounded-control border px-1.5 text-micro transition",
      active
        ? "border-accent bg-accent-surface font-medium text-accent"
        : "border-subtle text-secondary hover:bg-surface-hover hover:text-primary",
    );
  }

  return (
    <article className={cx(
      "group min-w-0 px-1 py-3 transition hover:bg-surface-hover",
      layout === "rows"
        ? "grid grid-cols-[52px_minmax(0,1fr)] gap-3 sm:grid-cols-[58px_minmax(0,1fr)_auto]"
        : "flex flex-col gap-2",
      band === "killed" && "opacity-60",
    )}>
      <div className={cx("text-center", layout === "grid" && "flex items-baseline justify-center gap-2")}>
        <div className={cx(
          "numeral leading-none",
          layout === "rows" ? "text-numeral-lg" : "text-title",
          band === "strong" ? "text-ok" : band === "fair" ? "text-warn" : band === "killed" ? "text-danger" : "text-muted",
        )}>
          {item.score === null ? "—" : Math.round(item.score)}
        </div>
        <span className="text-micro uppercase tracking-wide text-muted">skor</span>
      </div>
      <div className="min-w-0">
        <button type="button" onClick={onOpen} className="block max-w-full text-left text-heading leading-snug text-primary transition hover:text-accent">
          <span className="line-clamp-2">{item.title}</span>
        </button>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-meta text-muted">
          {item.organization && <span className="truncate text-secondary">{item.organization}</span>}
          {item.location && <span className="inline-flex items-center gap-1"><MapPin size={12} />{item.location}</span>}
          <span title={new Date(item.found_at).toLocaleString("tr-TR")}>⏱ {relativeTime(item.found_at)} · tarandı</span>
          <button type="button" onClick={() => onKind?.(item.kind)} className={chip(false)} title="Türüne göre filtrele">
            {kindLabel(item.kind)}
          </button>
          <button type="button" onClick={() => onSource?.(item.source)} className={chip(sourceActive)} title="Kaynağına göre filtrele">
            {sourceLabel(item.source)}
          </button>
          {rk && (
            <button
              type="button"
              onClick={() => onRemote?.(rk)}
              title="Uzaktan/ofis durumuna göre filtrele"
              className={cx(
                chip(remoteActive),
                rk === "remote" && !remoteActive && "border-accent-border text-accent",
              )}
            >
              {REMOTE_LABELS[rk]}
            </button>
          )}
          {left !== null && <span className={urgent ? "text-warn" : "text-secondary"}>{left < 0 ? `${Math.abs(left)} gün geçti` : left === 0 ? "Son gün" : `${left} gün kaldı`}</span>}
        </div>
      </div>
      <div className={cx(
        "flex flex-wrap items-center gap-2",
        layout === "rows" ? "col-span-2 sm:col-span-1 sm:justify-end" : "justify-start",
      )}>        {isTrash ? (
          <>
            <Button size="sm" onClick={onRestore} disabled={disabled}>
              <RotateCcw size={13} /> Geri yükle
            </Button>
            <Button size="sm" variant="danger" onClick={onDelete} disabled={disabled}>
              Kalıcı sil
            </Button>
          </>
        ) : (
          <Select
            value={item.status}
            disabled={disabled}
            ariaLabel="Durum"
            onChange={onStatus}
            className="min-w-0 flex-1"
          >
            {STATUSES.map((status) => (
              <option key={status} value={status}>{statusLabel(status)}</option>
            ))}
          </Select>
        )}
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer"
            title="İlanı yeni sekmede aç"
            aria-label="İlanı yeni sekmede aç"
            className="flex h-8 w-8 items-center justify-center rounded-control border border-subtle text-muted transition hover:bg-surface-hover hover:text-primary"
          >
            <ExternalLink size={14} />
          </a>
        )}
        {!isTrash && onSave && item.url && (
          <button
            type="button"
            onClick={onSave}
            disabled={disabled}
            title="Kütüphaneye kaydet"
            aria-label={`${item.title} fırsatını kütüphaneye kaydet`}
            className="flex h-8 w-8 items-center justify-center rounded-control border border-subtle text-muted transition hover:bg-surface-hover hover:text-primary disabled:opacity-50"
          >
            <Bookmark size={14} />
          </button>
        )}
        {!isTrash && (
          <button
            type="button"
            onClick={onTrash}
            disabled={disabled}
            title="Çöpe at"
            aria-label={`${item.title} fırsatını çöpe at`}
            className="flex h-8 w-8 items-center justify-center rounded-control border border-subtle text-muted transition hover:border-danger hover:text-danger disabled:opacity-50"
          >
            <Trash2 size={14} />
          </button>
        )}
      </div>
    </article>
  );
}