import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { sourceLabel } from "@/core/labels";
import type { SourceSyncStatus } from "@/core/types";
import { Button, Chip, cx } from "@/core/ui";

export type SourceSyncScope = "opportunity" | "media";

export function sourceSyncApiPath(scope: SourceSyncScope): string {
  return scope === "media" ? "/sources/sync?scope=media" : "/sources/sync";
}

export function sourceSyncHistoryApiPath(scope: SourceSyncScope): string {
  return scope === "media" ? "/sources/sync/history?scope=media" : "/sources/sync/history";
}

export function sourceSyncRoute(scope: SourceSyncScope): string {
  return scope === "media" ? "/sources?scope=media" : "/sources";
}

export function sourceSyncQueryKey(scope: SourceSyncScope): readonly string[] {
  return scope === "media" ? ["source-sync", "media"] : ["source-sync"];
}

export function sourceSyncHistoryQueryKey(scope: SourceSyncScope): readonly string[] {
  return scope === "media" ? ["source-sync-history", "media"] : ["source-sync-history"];
}

/** Cekim surerken yoklama araligi (ilerleme gorunur kalsin). */
export const SOURCE_SYNC_ACTIVE_MS = 2_000;
/** Bosta yoklama araligi. Ayni anahtari kullanan herkes BUNU kullanir. */
export const SOURCE_SYNC_IDLE_MS = 15_000;

export function useSourceSync(scope: SourceSyncScope = "opportunity") {
  return useQuery({
    queryKey: sourceSyncQueryKey(scope),
    queryFn: () => api.get<SourceSyncStatus>(sourceSyncApiPath(scope)),
    refetchInterval: (query) => (query.state.data?.active ? SOURCE_SYNC_ACTIVE_MS : SOURCE_SYNC_IDLE_MS),
  });
}

type SyncItemStatus = SourceSyncStatus["sources"][number]["status"];

const STATUS_LABELS: Record<SyncItemStatus, string> = {
  queued: "kuyrukta",
  running: "çekiliyor",
  ok: "tamamlandı",
  partial: "kısmi",
  empty: "yeni kayıt yok",
  error: "hata",
};

export function sourceSyncStatusLabel(status: SyncItemStatus): string {
  return STATUS_LABELS[status];
}

export function sourceSyncStatusTone(status: SyncItemStatus): "accent" | "danger" | "neutral" | "ok" | "warn" {
  if (status === "running") return "accent";
  if (status === "ok") return "ok";
  if (status === "partial" || status === "empty") return "warn";
  if (status === "error") return "danger";
  return "neutral";
}

export function SyncProgress({
  compact = false,
  scope = "opportunity",
}: {
  compact?: boolean;
  scope?: SourceSyncScope;
}) {
  const { data, error, isError, isFetching, refetch } = useSourceSync(scope);
  const [expanded, setExpanded] = useState(false);
  if (isError) {
    return (
      <section
        role="alert"
        className={cx(
          "flex flex-wrap items-center gap-3 border-y border-danger-border bg-danger-surface text-meta text-danger",
          compact ? "px-3 py-2.5" : "px-4 py-4",
        )}
      >
        <span>Kaynak senkronizasyonu yüklenemedi: {error?.message}</span>
        <Button
          size="sm"
          disabled={isFetching}
          onClick={() => {
            void refetch();
          }}
        >
          Yeniden dene
        </Button>
      </section>
    );
  }
  const batch = data?.active;
  const recent = data?.last_completed;
  const showRecent = recent?.finished_at && Date.now() - new Date(recent.finished_at).getTime() < 120_000;
  if (!batch && !showRecent) return null;

  if (!batch && recent) {
    return (
      <section className="flex flex-wrap items-center gap-3 border-y border-subtle px-1 py-2.5">
        {recent.error_sources > 0 ? (
          <AlertTriangle size={15} className="text-danger" />
        ) : (
          <CheckCircle2 size={15} className="text-ok" />
        )}
        <span className="text-body font-medium text-primary">Son çekim tamamlandı</span>
        <span className="text-meta text-secondary">{recent.total_sources} kaynak</span>
        <span className="text-meta text-secondary">+{recent.items_found} yeni kayıt</span>
        {recent.error_sources > 0 && (
          <button
            type="button"
            onClick={() => navigate(sourceSyncRoute(scope))}
            className="text-meta text-danger hover:underline"
          >
            {recent.error_sources} hata
          </button>
        )}
      </section>
    );
  }
  if (!batch) return null;

  const running = data?.running.length ?? 0;
  return (
    <section
      className={cx(
        "overflow-hidden border-y border-accent-border bg-accent-surface/30",
        compact ? "px-3 py-2.5" : "px-4 py-4",
      )}
      aria-label="Kaynak senkronizasyonu"
      aria-live="polite"
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="flex items-center gap-2 text-body font-medium text-primary">
          <Loader2 size={15} className="animate-spin text-accent" />
          Kaynaklar çekiliyor
        </span>
        <strong className="numeral text-title text-accent">%{batch.progress_pct}</strong>
        <span className="text-meta text-secondary">
          {batch.completed_sources} / {batch.total_sources} kaynak
        </span>
        {running > 0 && <Chip tone="accent">{running} aktif</Chip>}
        <Chip tone="ok" aria-label={`${batch.items_found} yeni kayıt`} className="ml-auto tabular-nums">
          +{batch.items_found} yeni kayıt
        </Chip>
        {batch.error_sources > 0 && (
          <Button size="sm" variant="ghost" onClick={() => navigate(sourceSyncRoute(scope))} className="text-danger">
            <AlertTriangle size={13} /> {batch.error_sources} hata
          </Button>
        )}
        {!compact && batch.error_sources === 0 && batch.completed_sources > 0 && (
          <span className="flex items-center gap-1 text-meta text-ok">
            <CheckCircle2 size={13} /> {batch.ok_sources} başarılı
          </span>
        )}
        <Button size="sm" variant="ghost" onClick={() => setExpanded((value) => !value)} ariaExpanded={expanded}>
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          {expanded ? "Ayrıntıları gizle" : "Tüm kaynakları göster"}
        </Button>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-sunken">
        <span
          className="block h-full rounded-full bg-accent transition-[width] duration-500"
          style={{ width: `${batch.progress_pct}%` }}
        />
      </div>
      {expanded && (
        <ul className="mt-3 grid max-h-64 grid-cols-1 gap-1 overflow-y-auto border-t border-accent-border pt-3 sm:grid-cols-2 xl:grid-cols-3">
          {(data?.sources ?? []).map((item) => (
            <li
              key={item.source}
              className="flex min-w-0 items-center gap-2 rounded-control bg-surface px-2 py-1.5 text-meta"
              title={item.error ?? undefined}
            >
              <span className="min-w-0 flex-1 truncate text-secondary">{sourceLabel(item.source)}</span>
              {item.items_found > 0 && (
                <span className="tabular-nums text-ok" aria-label={`${item.items_found} yeni kayıt`}>
                  +{item.items_found}
                </span>
              )}
              <Chip tone={sourceSyncStatusTone(item.status)} size="xs">
                {sourceSyncStatusLabel(item.status)}
              </Chip>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
