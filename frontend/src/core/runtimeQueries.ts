/**
 * Kabuk boyunca PAYLASILAN runtime sorgulari (tek anahtar, tek aralik).
 *
 * Neden: TanStack Query ayni anahtari dedupe eder, ama AYNI ucu farkli
 * anahtarla sormak onbellegi ve polling'i ikiye boler. Kaynak sagligi tam da
 * boyleydi: SourceAlert `["sources","health"]`, StatusLed
 * `["sources","health","all"]` kullaniyordu ve ikisi de kabukta surekli
 * mount oldugu icin ayni uc oturum boyunca iki kez yoklanıyordu.
 *
 * Kural: bu uclari tuketen herkes bu hook'lari kullanir; anahtar veya aralik
 * cagri yerinde YAZILMAZ. Aciliyet gerektiren tazelik zaten
 * `invalidateAfter(...)` iledir (or. `source.sync` -> "sources"), polling ile
 * degil.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/core/api";
import type { BackupStatus, RssStats, SourceHealth, SystemStats } from "@/core/types";

/** Kaynak sagligi: kabuktaki tek paylasilan anahtar. */
export const SOURCE_HEALTH_QUERY_KEY = ["sources", "health", "all"] as const;
/** Bosta yoklama araligi. Aksiyon sonrasi tazelik invalidation ile gelir. */
export const SOURCE_HEALTH_INTERVAL_MS = 5 * 60_000;
/** Cekim surerken (bir kaynak `running`) daha sik yoklanir. */
const SOURCE_HEALTH_ACTIVE_MS = 5_000;

/** /sources/health?limit=2000 -- tum kaynaklarin son durumu. */
export function useSourceHealth() {
  return useQuery({
    queryKey: SOURCE_HEALTH_QUERY_KEY,
    queryFn: () => api.get<SourceHealth[]>("/sources/health?limit=2000"),
    refetchInterval: (query) =>
      (query.state.data as SourceHealth[] | undefined)?.some((run) => run.status === "running")
        ? SOURCE_HEALTH_ACTIVE_MS
        : SOURCE_HEALTH_INTERVAL_MS,
  });
}

/** Sistem istatistikleri (CPU/RAM/disk/worker). */
const SYSTEM_STATS_QUERY_KEY = ["system-stats"] as const;
const SYSTEM_STATS_INTERVAL_MS = 60_000;

export function useSystemStats() {
  return useQuery({
    queryKey: SYSTEM_STATS_QUERY_KEY,
    queryFn: () => api.get<SystemStats>("/system/stats"),
    refetchInterval: SYSTEM_STATS_INTERVAL_MS,
  });
}

/** Yerel yedek durumu (son yedek ve degisiklik durumu). */
const BACKUP_STATUS_QUERY_KEY = ["backup-status"] as const;
const BACKUP_STATUS_INTERVAL_MS = 60_000;

export function useBackupStatus() {
  return useQuery({
    queryKey: BACKUP_STATUS_QUERY_KEY,
    queryFn: () => api.get<BackupStatus>("/backup/status"),
    refetchInterval: BACKUP_STATUS_INTERVAL_MS,
  });
}

/**
 * RSS ozeti. Kabukta bes ayri yerde ayni uc ayni anahtarla soruluyordu;
 * anahtar burada TEK yerde durur (bugun `["rss-stats"]` ile ayni, yarin
 * degisirse tek noktadan degisir).
 */
const RSS_STATS_QUERY_KEY = ["rss-stats"] as const;

export function useRssStats(enabled = true) {
  return useQuery({
    queryKey: RSS_STATS_QUERY_KEY,
    queryFn: () => api.get<RssStats>("/rss/stats"),
    enabled,
    staleTime: 60_000,
  });
}
