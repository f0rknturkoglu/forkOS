/**
 * Kaynak operasyonlarının TEK veri katmanı.
 *
 * Neden: katalog/koşu/senkronizasyon/kapsam/önbellek sorguları üç ayrı yüzeyde
 * (kaynak çalışma alanı, Sistem > Kaynaklar, "Kaynakları çek" açılır listesi)
 * kopyalanmıştı ve her kopya kendi `/sources/refresh` mutasyonunu taşıyordu.
 * Sorgu ve mutasyon burada tek yerde durur; yüzeyler yalnız okur.
 *
 * Sınır: sağlık EŞİĞİ burada hesaplanmaz. "Sorun mu?" kararı backend
 * özetinden (`/sources/coverage`) gelir; `@/core/sourceStatus` yalnız o
 * alanları yorumlar.
 *
 * Sorgu anahtarları `@/core/invalidation` içindeki `source.sync` kümesiyle
 * aynıdır ("source-catalog", "source-coverage", "source-cache"): yenileme ve
 * önbellek yazmalarından sonra tazelenme `invalidateAfter("source.sync")` ile
 * olur, elle invalidate edilmez.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { sourceLabel } from "@/core/labels";
import {
  sourceSyncHistoryApiPath,
  sourceSyncHistoryQueryKey,
  useSourceSync,
  type SourceSyncScope,
} from "@/core/SyncProgress";
import { useToast } from "@/core/ui";
import type {
  SourceCachePruneResult,
  SourceCacheStats,
  SourceCoverageRow,
  SourceHealth,
  SourceRefreshResult,
  SourceSyncBatch,
  SourceSyncStatus,
} from "@/core/types";

/** `/sources/catalog` satırı — backend `sources_router.source_catalog` çıktısı. */
export interface SourceCatalogEntry {
  id: string;
  interval_minutes: number;
  /** "job" | "announcement" */
  kind: string;
  category?: string | null;
  /** critical | normal | slow_optin */
  class?: string | null;
  /** Portalın kendi verdiği kaba süre tahmini (saniye). */
  estimated_seconds?: number | null;
  timeout_seconds?: number | null;
  opt_in?: boolean | null;
  circuit_open?: boolean | null;
  consecutive_failures?: number | null;
  /** Devre AÇIKken ağa tekrar çıkılacak an; kapalıyken null (backend alanı). */
  retry_at?: string | null;
}

/**
 * Kapsam satırı + devre yeniden deneme anı. `retry_at` backend'de var; tip
 * tarafında eklenmemiş olsa da okunur, uydurma zaman üretilmez.
 */
export type CoverageRow = SourceCoverageRow & { retry_at?: string | null };

export function useSourceCatalog() {
  return useQuery({
    queryKey: ["source-catalog"],
    queryFn: () => api.get<SourceCatalogEntry[]>("/sources/catalog"),
  });
}

/** Yalnız koşu geçmişi listesi için; sağlık kararı bundan ÜRETİLMEZ. */
export function useSourceRuns() {
  return useQuery({
    queryKey: ["source-runs"],
    queryFn: () => api.get<SourceHealth[]>("/sources/runs"),
  });
}

export function useSourceCoverage() {
  return useQuery({
    queryKey: ["source-coverage"],
    queryFn: () => api.get<SourceCoverageRow[]>("/sources/coverage"),
  });
}

export function useSourceCache() {
  return useQuery({
    queryKey: ["source-cache"],
    queryFn: () => api.get<SourceCacheStats>("/sources/cache"),
  });
}

/** Toplu çekim partileri (`/sources/sync/history`) — kapsam başına ayrı anahtar. */
export function useSourceSyncHistory(scope: SourceSyncScope = "opportunity") {
  const sync = useSourceSync(scope);
  return useQuery({
    queryKey: sourceSyncHistoryQueryKey(scope),
    queryFn: () => api.get<SourceSyncBatch[]>(sourceSyncHistoryApiPath(scope)),
    // Çekim sürerken sık, boşta seyrek yokla; aktiflik aynı anahtarlı durum
    // sorgusundan okunur (ek istek üretmez).
    refetchInterval: sync.data?.active ? 2_000 : 30_000,
  });
}

/** Yenileme gövdesi: `mode` toplu taramayı, `source_ids` kaynak seçimini taşır. */
interface SourceRefreshRequest {
  mode?: "general" | "full";
  source_ids?: string[];
}

/**
 * Toplu yenileme yolu. Boş gövde ASLA gönderilmez: çağıran ya `mode` ya
 * `source_ids` verir (backend `{}` durumunda tüm havuzu kritik sınıftan seçer,
 * bu yüzden arayüz niyetini açıkça yazar).
 */
export function useSourceRefresh() {
  const toast = useToast();
  return useMutation({
    mutationFn: (body: SourceRefreshRequest) => api.post<SourceRefreshResult>("/sources/refresh", body),
    onSuccess: (result) => {
      invalidateAfter("source.sync");
      toast.push(
        result.queued ? `${result.queued} kaynak kuyruğa alındı` : "Seçilen kaynaklar aktif çekimde zaten var",
        { tone: "ok" },
      );
    },
  });
}

/**
 * Tek kaynak yenilemesi: kaynağa AYRILMIŞ uç (`/sources/{id}/refresh`).
 * Kuyruk semantiği toplu çağrıyla aynıdır; satır düğmesi bu ucu kullanır.
 */
export function useSourceRefreshOne() {
  const toast = useToast();
  return useMutation({
    mutationFn: (sourceId: string) =>
      api.post<{ source: string; added: number; batch_id: string | null }>(
        `/sources/${encodeURIComponent(sourceId)}/refresh`,
      ),
    onSuccess: (_result, sourceId) => {
      invalidateAfter("source.sync");
      toast.push(`${sourceLabel(sourceId)} çekimi kuyruğa alındı`, { tone: "ok" });
    },
  });
}

/** Disk önbelleğini bütçeye indirir (TTL + LRU). Yerel iş: internet gerekmez. */
export function useSourceCachePrune() {
  const toast = useToast();
  return useMutation({
    mutationFn: () => api.post<SourceCachePruneResult>("/sources/cache/prune", {}),
    onSuccess: (result) => {
      invalidateAfter("source.sync");
      toast.push(`${result.removed} dosya silindi · ${formatBytes(result.bytes_freed)} boşaltıldı`, { tone: "ok" });
    },
  });
}

/** Önbelleği tamamen boşaltır. Yerel iş: internet gerekmez. */
export function useSourceCacheClear() {
  const toast = useToast();
  return useMutation({
    mutationFn: () => api.post<SourceCachePruneResult>("/sources/cache/clear", { confirm: true }),
    onSuccess: (result) => {
      invalidateAfter("source.sync");
      toast.push(`${result.removed} önbellek dosyası silindi`, { tone: "ok" });
    },
  });
}

/** Kaynak başına son koşu (`runs` yeniden eskiye sıralı gelir). */
export function latestRunBySource(runs: readonly SourceHealth[]): Map<string, SourceHealth> {
  const map = new Map<string, SourceHealth>();
  for (const run of runs) if (!map.has(run.source)) map.set(run.source, run);
  return map;
}

export function coverageBySource(rows: readonly SourceCoverageRow[]): Map<string, CoverageRow> {
  return new Map(rows.map((row) => [row.source, row as CoverageRow]));
}

/** Aktif toplu çekimdeki kaynak durumları. */
export function syncBySource(sync: SourceSyncStatus | undefined): Map<string, SourceSyncStatus["sources"][number]> {
  return new Map((sync?.sources ?? []).map((item) => [item.source, item]));
}

/** Şu an çekilen kaynak kimlikleri. */
export function runningSources(sync: SourceSyncStatus | undefined): Set<string> {
  return new Set((sync?.running ?? []).map((item) => item.source));
}

/**
 * Satır durumu: canlı çekim > backend kapsam özeti > son koşu > hiç çalışmadı.
 * Dönen değer `runStateView()` ile yorumlanır.
 */
export function sourceRunState(input: {
  sync?: { status: string } | undefined;
  coverage?: { last_status?: string | null } | undefined;
  run?: { status?: string | null } | undefined;
}): string {
  return input.sync?.status ?? input.coverage?.last_status ?? input.run?.status ?? "new";
}

export function formatBytes(value: number): string {
  if (value >= 1024 ** 3) return `${(value / 1024 ** 3).toFixed(1)} GB`;
  if (value >= 1024 ** 2) return `${(value / 1024 ** 2).toFixed(1)} MB`;
  if (value >= 1024) return `${(value / 1024).toFixed(0)} KB`;
  return `${value} B`;
}

/** Kaba süre tahmini: katalogdaki `estimated_seconds` toplamı bu biçimde gösterilir. */
export function formatSeconds(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)} sn`;
  const minutes = Math.round(seconds / 60);
  return minutes < 60 ? `${minutes} dk` : `${Math.round(minutes / 60)} sa`;
}
