import { ExternalLink, MapPin, RotateCcw, Trash2 } from "lucide-react";
import { Badge, Button, cx } from "@/core/ui";
import type { Opportunity } from "@/core/types";
import {
  SCORE_LABEL, SCORE_TONE, STATUSES,
  daysLeft, kindLabel, scoreBand, sourceLabel, statusLabel,
} from "./labels";

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
      <span className={cx("numeral text-[13px]", active ? "text-accent" : "text-muted")}>{count}</span>
    </button>
  );
}

export function OpportunityCard({
  item, onOpen, onStatus, onTrash, onRestore, onDelete, disabled, isTrash,
}: {
  item: Opportunity;
  onOpen: () => void;
  onStatus: (status: string) => void;
  onTrash: () => void;
  onRestore: () => void;
  onDelete: () => void;
  disabled: boolean;
  isTrash: boolean;
}) {
  const left = daysLeft(item.deadline_at);
  const urgent = left !== null && left <= 7;
  const band = scoreBand(item.score);

  return (
    <article className={cx(
      "group grid min-w-0 grid-cols-[52px_minmax(0,1fr)] gap-3 px-1 py-3 transition hover:bg-surface-hover sm:grid-cols-[58px_minmax(0,1fr)_auto]",
      band === "killed" && "opacity-60",
    )}>
      <div className="text-center">
        <div className={cx(
          "numeral text-[24px] leading-none",
          band === "strong" ? "text-ok" : band === "fair" ? "text-accent" : band === "killed" ? "text-danger" : "text-muted",
        )}>
          {item.score === null ? "—" : Math.round(item.score)}
        </div>
        <span className="text-[10px] uppercase tracking-wide text-muted">skor</span>
      </div>
      <div className="min-w-0">
        <button type="button" onClick={onOpen} className="block max-w-full text-left text-heading leading-snug text-primary transition hover:text-accent">
          <span className="line-clamp-2">{item.title}</span>
        </button>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-meta text-muted">
          {item.organization && <span className="truncate text-secondary">{item.organization}</span>}
          {item.location && <span className="inline-flex items-center gap-1"><MapPin size={12} />{item.location}</span>}
          <Badge>{kindLabel(item.kind)}</Badge>
          <span>{sourceLabel(item.source)}</span>
          {item.remote && <span>{item.remote}</span>}
          {band && <Badge tone={SCORE_TONE[band]}>{SCORE_LABEL[band]}</Badge>}
          {left !== null && <span className={urgent ? "text-warn" : "text-secondary"}>{left < 0 ? `${Math.abs(left)} gün geçti` : left === 0 ? "Son gün" : `${left} gün kaldı`}</span>}
        </div>
      </div>
      <div className="col-span-2 flex flex-wrap items-center gap-2 sm:col-span-1 sm:justify-end">
        {isTrash ? (
          <>
            <Button size="sm" onClick={onRestore} disabled={disabled}>
              <RotateCcw size={13} /> Geri yükle
            </Button>
            <Button size="sm" variant="danger" onClick={onDelete} disabled={disabled}>
              Kalıcı sil
            </Button>
          </>
        ) : (
          <select
            value={item.status}
            disabled={disabled}
            aria-label="Durum"
            onChange={(event) => onStatus(event.target.value)}
            className="h-8 min-w-0 flex-1 rounded-control border border-subtle bg-canvas px-2 text-meta text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent disabled:opacity-50"
          >
            {STATUSES.map((status) => (
              <option key={status} value={status}>{statusLabel(status)}</option>
            ))}
          </select>
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
