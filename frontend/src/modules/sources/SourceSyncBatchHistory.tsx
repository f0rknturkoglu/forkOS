/**
 * Toplu çekim partileri (`/sources/sync/history`) — medya kapsamının gördüğü
 * tek geçmiş görünümü.
 *
 * Kariyer/sistem yüzeyleri kaynak BAŞINA son koşuları (`/sources/runs`) ve
 * kapsam matrisini gösterir; medya kapsamı ise yalnız çekim ilerlemesini ve
 * parti geçmişini gösterir (iş sınıfı/kapsam oraya ait değildir).
 */
import { dataState, SectionFallback } from "@/core/DataState";
import { Chip, RowList, Section, relativeTime } from "@/core/ui";
import type { SourceSyncScope } from "@/core/SyncProgress";
import { useSourceSyncHistory } from "./sourceOps";

export function SourceSyncBatchHistory({ scope = "opportunity" }: { scope?: SourceSyncScope }) {
  const history = useSourceSyncHistory(scope);
  const state = dataState(history);
  const batches = history.data ?? [];

  return (
    <Section title="Son senkronizasyonlar" hint={state === "ready" ? `${batches.length} koşum` : undefined}>
      {state !== "ready" ? (
        <SectionFallback
          state={state}
          what="Senkronizasyon geçmişi"
          onRetry={() => void history.refetch()}
          emptyLabel="Henüz tamamlanmış manuel çekim yok."
        />
      ) : (
        <RowList>
          {batches.map((batch) => {
            const duration =
              batch.started_at && batch.finished_at
                ? Math.max(
                    0,
                    Math.round((new Date(batch.finished_at).getTime() - new Date(batch.started_at).getTime()) / 1000),
                  )
                : null;
            return (
              <div key={batch.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-1 py-3 text-meta">
                <span className="min-w-0 flex-1 text-body text-primary">{relativeTime(batch.created_at)}</span>
                <Chip tone={batch.error_sources ? "danger" : "ok"}>
                  {batch.error_sources ? "hatalarla tamamlandı" : "tamamlandı"}
                </Chip>
                <span className="text-secondary">{batch.total_sources} kaynak</span>
                <span className="tabular-nums text-secondary">+{batch.items_found} kayıt</span>
                {batch.error_sources > 0 && <span className="text-danger">{batch.error_sources} hata</span>}
                {duration !== null && <span className="tabular-nums text-muted">{duration} sn</span>}
              </div>
            );
          })}
        </RowList>
      )}
    </Section>
  );
}
