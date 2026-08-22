import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import type { SourceSyncStatus } from "@/core/types";
import { Badge, cx } from "@/core/ui";

export function useSourceSync() {
  return useQuery({
    queryKey: ["source-sync"],
    queryFn: () => api.get<SourceSyncStatus>("/sources/sync"),
    refetchInterval: (query) => query.state.data?.active ? 2_000 : 15_000,
  });
}

export function SyncProgress({ compact = false }: { compact?: boolean }) {
  const { data } = useSourceSync();
  const batch = data?.active;
  const recent = data?.last_completed;
  const showRecent = recent?.finished_at
    && Date.now() - new Date(recent.finished_at).getTime() < 120_000;
  if (!batch && !showRecent) return null;

  if (!batch && recent) {
    return (
      <section className="flex flex-wrap items-center gap-3 border-y border-subtle px-1 py-2.5">
        {recent.error_sources > 0
          ? <AlertTriangle size={15} className="text-danger" />
          : <CheckCircle2 size={15} className="text-ok" />}
        <span className="text-body font-medium text-primary">Son çekim tamamlandı</span>
        <span className="text-meta text-secondary">{recent.total_sources} kaynak</span>
        <span className="text-meta text-secondary">+{recent.items_found} yeni kayıt</span>
        {recent.error_sources > 0 && (
          <button type="button" onClick={() => navigate("/sources")} className="text-meta text-danger hover:underline">
            {recent.error_sources} hata
          </button>
        )}
      </section>
    );
  }
  if (!batch) return null;

  const running = data?.running.length ?? 0;
  return (
    <section className={cx(
      "overflow-hidden border-y border-accent-border bg-accent-surface/30",
      compact ? "px-3 py-2.5" : "px-4 py-4",
    )} aria-label="Kaynak senkronizasyonu">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="flex items-center gap-2 text-body font-medium text-primary">
          <Loader2 size={15} className="animate-spin text-accent" />
          Kaynaklar çekiliyor
        </span>
        <strong className="numeral text-[18px] text-accent">%{batch.progress_pct}</strong>
        <span className="text-meta text-secondary">
          {batch.completed_sources} / {batch.total_sources} kaynak
        </span>
        {running > 0 && <Badge tone="accent">{running} aktif</Badge>}
        <span className="ml-auto text-meta text-secondary">+{batch.items_found} yeni kayıt</span>
        {batch.error_sources > 0 && (
          <button
            type="button"
            onClick={() => navigate("/sources")}
            className="flex items-center gap-1.5 text-meta text-danger hover:underline"
          >
            <AlertTriangle size={13} /> {batch.error_sources} hata
          </button>
        )}
        {!compact && batch.error_sources === 0 && batch.completed_sources > 0 && (
          <span className="flex items-center gap-1 text-meta text-ok">
            <CheckCircle2 size={13} /> {batch.ok_sources} başarılı
          </span>
        )}
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-sunken">
        <span
          className="block h-full rounded-full bg-accent transition-[width] duration-500"
          style={{ width: `${batch.progress_pct}%` }}
        />
      </div>
    </section>
  );
}
