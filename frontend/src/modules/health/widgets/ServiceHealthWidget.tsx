import { useQuery } from "@tanstack/react-query";
import { Activity, DatabaseBackup } from "lucide-react";
import { api } from "@/core/api";
import { Chip, Empty, Section, relativeTime } from "@/core/ui";
import type { BackupStatus } from "@/core/types";

interface SystemStats {
  worker: { status: "healthy" | "stale" | "unknown" | "disabled"; heartbeat_at: string | null };
  cpu_pct: number;
  mem_total_kb: number;
  uptime_s: number;
}

const STALE_BACKUP_HOURS = 48;

/**
 * Servis guvenilirlik karti (Faz 26): worker heartbeat + yedek bayatligi.
 * Her ikisi de mevcut endpoint'lerden turetilir; yeni uc yok.
 */
export function ServiceHealthWidget() {
  const { data: stats } = useQuery({
    queryKey: ["system-stats"],
    queryFn: () => api.get<SystemStats>("/system/stats"),
    refetchInterval: 60_000,
  });
  const { data: backup } = useQuery({
    queryKey: ["backup-status"],
    queryFn: () => api.get<BackupStatus>("/backup/status"),
    refetchInterval: 60_000,
  });

  const workerHealthy = stats?.worker.status === "healthy";
  const lastBackupAt = backup?.last_backup?.at ? new Date(backup.last_backup.at).getTime() : null;
  const backupStale = lastBackupAt !== null && Date.now() - lastBackupAt > STALE_BACKUP_HOURS * 3_600_000;

  if (!stats && !backup) return <Empty>Servis durumu yükleniyor…</Empty>;

  return (
    <Section title="Servis sağlığı">
      <div className="space-y-2 text-meta">
        <p className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-1.5 text-muted">
            <Activity size={13} className="text-icon" /> Worker
          </span>
          {workerHealthy ? (
            <Chip tone="ok">çalışıyor</Chip>
          ) : stats?.worker.status === "disabled" ? (
            <Chip>kapalı · elle yenileme</Chip>
          ) : stats?.worker.status === "stale" ? (
            <Chip tone="danger">durdu — arka plan işleri çalışmıyor</Chip>
          ) : (
            <Chip tone="warn">bilinmiyor</Chip>
          )}
        </p>
        {stats?.worker.heartbeat_at && (
          <p className="text-muted">Son kalp atışı: {relativeTime(stats.worker.heartbeat_at)}</p>
        )}

        <p className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-1.5 text-muted">
            <DatabaseBackup size={13} className="text-icon" /> Yedek
          </span>
          {backupStale ? (
            <Chip tone="warn">eski — {STALE_BACKUP_HOURS} saatten uzun süredir yok</Chip>
          ) : lastBackupAt !== null ? (
            <Chip tone="ok">güncel</Chip>
          ) : (
            <Chip tone="warn">henüz yok</Chip>
          )}
        </p>
        {backup?.last_backup?.at && <p className="text-muted">Son yedek: {relativeTime(backup.last_backup.at)}</p>}
      </div>
    </Section>
  );
}
