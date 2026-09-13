import { Bookmark, CalendarDays, ExternalLink, MapPin, RotateCcw, Trash2, Users } from "lucide-react";
import { Button, Chip, FilterChip, Select, cx, relativeTime } from "@/core/ui";
import type { Opportunity } from "@/core/types";
import {
  REMOTE_LABELS,
  SOURCE_STATUS_LABELS,
  STALE_REASON_HINTS,
  announcementCategoryLabel,
  applicationStatusLabel,
  archetypeLabel,
  daysLeft,
  jobCategoryLabel,
  kindLabel,
  recommendationLabel,
  recommendationTone,
  remoteKind,
  scoreBand,
  statusLabel,
} from "./labels";
import { sourceLabel } from "@/core/labels";
import { displayScore } from "./scoreDomain";
import type { RemoteKind } from "./labels";

/**
 * İkincil skorlar tek satırda: profil uyumu (oran) ve tavsiye skoru (puan).
 * Satırdaki TEK ana skor kalite skorudur; bu metin açıklanabilir detaydır.
 */
function secondaryScoreLabel(item: Opportunity): string | null {
  const parts: string[] = [];
  if (item.profile_match_ratio !== null && item.profile_match_ratio !== undefined) {
    parts.push(`Uyum %${Math.round(item.profile_match_ratio * 100)}`);
  }
  if (item.evaluation?.recommendation) {
    parts.push(`Tavsiye ${item.evaluation.score}p`);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}

export function OpportunityCollection({ layout, children }: { layout: "rows" | "grid"; children: React.ReactNode }) {
  return (
    <div
      data-layout={layout}
      className={cx(
        layout === "grid" ? "grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3" : "divide-y divide-subtle",
      )}
    >
      {children}
    </div>
  );
}

export function OpportunityCard({
  item,
  onOpen,
  onStatus,
  onTrash,
  onRestore,
  onDelete,
  disabled,
  isTrash,
  layout = "rows",
  onSource,
  onRemote,
  onKind,
  sourceActive = false,
  remoteActive = false,
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
  const announcement = item.kind !== "job";
  const publicationDate = item.published_at ?? item.found_at;

  function chip(active: boolean) {
    return cx(
      "flex h-6 items-center rounded-control border px-1.5 text-micro transition",
      active
        ? "border-accent bg-accent-surface font-medium text-accent"
        : "border-subtle text-secondary hover:bg-surface-hover hover:text-primary",
    );
  }

  return (
    <article
      className={cx(
        "group min-w-0 transition hover:bg-surface-hover",
        layout === "rows"
          ? "grid grid-cols-[52px_minmax(0,1fr)] gap-3 px-1 py-3 sm:grid-cols-[58px_minmax(0,1fr)_auto]"
          : "flex h-full flex-col gap-3 rounded-card border border-subtle bg-surface p-4",
        band === "eliminated" && "opacity-60",
      )}
    >
      {announcement ? (
        <div className={cx("text-center text-secondary", layout === "grid" && "flex items-center gap-2 text-left")}>
          <CalendarDays size={18} className="mx-auto text-accent" />
          <time dateTime={publicationDate} className="mt-1 block text-meta font-medium">
            {new Date(publicationDate).toLocaleDateString("tr-TR", {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
          </time>
        </div>
      ) : (
        <div
          className={cx("text-center", layout === "grid" && "flex items-baseline justify-center gap-2")}
          title="Kalite skoru: kaynak ve kural tabanlı ilan kalitesi (−1 = elendi)"
          aria-label={
            item.score === null
              ? "Kalite skoru hesaplanmadı"
              : `Kalite skoru ${displayScore(item.score)} / 100`
          }
        >
          <div
            className={cx(
              "numeral leading-none",
              layout === "rows" ? "text-numeral-lg" : "text-title",
              band === "strong"
                ? "text-ok"
                : band === "fair"
                  ? "text-warn"
                  : band === "eliminated"
                    ? "text-danger"
                    : "text-muted",
            )}
          >
            {displayScore(item.score)}
          </div>
          <span className="text-micro uppercase tracking-wide text-muted">skor</span>
        </div>
      )}
      <div className="min-w-0">
        <button
          type="button"
          onClick={onOpen}
          className="block max-w-full text-left text-heading leading-snug text-primary transition hover:text-accent"
        >
          <span className="line-clamp-2">{item.title}</span>
        </button>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-meta text-muted">
          {item.organization && <span className="truncate text-secondary">{item.organization}</span>}
          {item.location && (
            <span className="inline-flex items-center gap-1">
              <MapPin size={12} />
              {item.location}
            </span>
          )}
          {!announcement && (
            <span title={new Date(publicationDate).toLocaleString("tr-TR")}>
              {relativeTime(publicationDate)} · {item.published_at ? "yayınlandı" : "tarandı"}
            </span>
          )}
          {!announcement && item.category && <span className={chip(false)}>{jobCategoryLabel(item.category)}</span>}
          {announcement && item.category?.startsWith("ylsy-") && (
            <Chip tone="accent">{announcementCategoryLabel(item.category)}</Chip>
          )}
          {/* Ikincil skorlar TEK açıklanabilir chip'te toplanir: satirda tek
              ana skor (kalite) kalir, digerleri ayrinti olarak sunulur. */}
          {!announcement && secondaryScoreLabel(item) && (
            <Chip tone="neutral">
              <span title="Profil uyumu: becerilerin ilan metniyle örtüşmesi · Tavsiye skoru: CV ile iki aşamalı değerlendirme">
                {secondaryScoreLabel(item)}
              </span>
            </Chip>
          )}
          {item.evaluation_stale_reason && (
            <Chip tone="warn">
              <span title={STALE_REASON_HINTS[item.evaluation_stale_reason] ?? "Yeniden hesapla"}>
                Değerlendirme güncel değil
              </span>
            </Chip>
          )}
          {!announcement && item.source_status && item.source_status !== "active" && (
            <Chip tone={item.source_status === "closed" ? "danger" : "warn"}>
              {SOURCE_STATUS_LABELS[item.source_status] ?? "Kaynakta bulunamıyor"}
            </Chip>
          )}
          {item.application_status && (
            <Chip tone={item.application_status === "rejected" ? "danger" : "accent"}>
              Başvuru: {applicationStatusLabel(item.application_status)}
            </Chip>
          )}
          {announcement && item.official !== null && item.official !== undefined && (
            <Chip tone={item.official ? "ok" : "neutral"}>{item.official ? "Resmî kaynak" : "İkincil kaynak"}</Chip>
          )}
          {announcement && item.stage && <Chip tone="neutral">{item.stage}</Chip>}
          {item.evaluation?.recommendation && (
            <Chip tone={recommendationTone(item.evaluation.recommendation)}>
              {recommendationLabel(item.evaluation.recommendation)}
            </Chip>
          )}
          {item.evaluation?.archetype && <Chip tone="neutral">{archetypeLabel(item.evaluation.archetype)}</Chip>}
          {item.intelligence?.connection_count ? (
            <Chip tone="accent">
              <span className="inline-flex items-center gap-1">
                <Users size={11} /> {item.intelligence.connection_count} bağlantı
              </span>
            </Chip>
          ) : null}
          {item.intelligence?.is_repost && <Chip tone="warn">Tekrar ilan · {item.intelligence.repost_count}</Chip>}
          {item.intelligence?.pay_transparency_risk && <Chip tone="warn">Geniş ücret bandı</Chip>}
          {item.intelligence?.geo_mismatch && <Chip tone="danger">Konum uyuşmazlığı</Chip>}
          <button
            type="button"
            onClick={() => onKind?.(item.kind)}
            className={chip(false)}
            title="Türüne göre filtrele"
            aria-label={`${item.title} — türüne göre filtrele (${kindLabel(item.kind)})`}
          >
            {kindLabel(item.kind)}
          </button>
          <button
            type="button"
            onClick={() => onSource?.(item.source)}
            className={chip(sourceActive)}
            title="Kaynağına göre filtrele"
            aria-label={`${item.title} — kaynağına göre filtrele (${sourceLabel(item.source)})`}
          >
            {sourceLabel(item.source)}
          </button>
          {rk && (
            <button
              type="button"
              onClick={() => onRemote?.(rk)}
              title="Uzaktan/ofis durumuna göre filtrele"
              aria-label={`${item.title} — çalışma biçimine göre filtrele`}
              className={cx(chip(remoteActive), rk === "remote" && !remoteActive && "border-accent-border text-accent")}
            >
              {REMOTE_LABELS[rk]}
            </button>
          )}
          {left !== null && (
            <span className={urgent ? "text-warn" : "text-secondary"}>
              {left < 0 ? `${Math.abs(left)} gün geçti` : left === 0 ? "Son gün" : `${left} gün kaldı`}
            </span>
          )}
        </div>
      </div>
      <div
        className={cx(
          "flex flex-wrap items-center gap-2",
          layout === "rows" ? "col-span-2 sm:col-span-1 sm:justify-end" : "justify-start",
        )}
      >
        {" "}
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
          <Select
            value={item.status}
            disabled={disabled}
            ariaLabel={`${item.title} — durum`}
            onChange={onStatus}
            className="min-w-0 flex-1"
          >
            {/* Yalnızca mevcut durumdan İZİNLİ geçişler listelenir (backend state machine). */}
            <option value={item.status}>{statusLabel(item.status)}</option>
            {(item.allowed_transitions ?? []).map((status) => (
              <option key={status} value={status}>
                {statusLabel(status)}
              </option>
            ))}
          </Select>
        )}
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer"
            title="İlanı yeni sekmede aç"
            aria-label={`${item.title} — ilanı yeni sekmede aç`}
            className={cx(
              "flex h-8 w-8 items-center justify-center rounded-control border border-subtle text-muted transition",
              "hover:bg-surface-hover hover:text-primary",
            )}
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
            className={cx(
              "flex h-8 w-8 items-center justify-center rounded-control border border-subtle text-muted transition",
              "hover:bg-surface-hover hover:text-primary disabled:opacity-50",
            )}
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
            className={cx(
              "flex h-8 w-8 items-center justify-center rounded-control border border-subtle text-muted transition",
              "hover:border-danger hover:text-danger disabled:opacity-50",
            )}
          >
            <Trash2 size={14} />
          </button>
        )}
      </div>
    </article>
  );
}
