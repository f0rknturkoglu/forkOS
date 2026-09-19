import { invalidateAfter } from "@/core/invalidation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CloudUpload, Database, HardDriveDownload } from "lucide-react";
import { api } from "@/core/api";
import { BackupMergeControl } from "@/core/BackupMergeControl";
import { Button, Chip, Section, cx, relativeTime, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { BackupStatus } from "@/core/types";

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.round(bytes / 1024)} KB`;
}

function topModules(counts: Record<string, number>, n: number): [string, number][] {
  return Object.entries(counts)
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n);
}

/** Yedekleme durumu: son yedek, Drive yukleme gecmisi ve kapsam. */
export function BackupHealthWidget() {
  const toast = useToast();
  const online = useOnline();

  const { data } = useQuery({
    queryKey: ["backup-status"],
    queryFn: () => api.get<BackupStatus>("/backup/status"),
    refetchInterval: 60_000,
  });
  const { data: google } = useQuery({
    queryKey: ["google-status"],
    queryFn: () => api.get<{ connected: boolean }>("/auth/google/status"),
  });

  const runNow = useMutation({
    mutationFn: () => api.post<{ path: string; size: number }>("/backup"),
    onSuccess: (result) => {
      invalidateAfter("backup.write");
      toast.push(
        `Yedek alındı (${formatBytes(result.size)})${data?.drive_folder_id ? " — Drive'a da yükleniyor" : ""}`,
        { tone: "ok" },
      );
    },
    onError: (error: Error) => toast.push(`Yedek başarısız: ${error.message}`, { tone: "danger" }),
  });

  const last = data?.last_backup;
  const top = last?.counts ? topModules(last.counts.modules, 4) : [];

  return (
    <Section
      title="Yedekleme"
      action={
        <div className="flex items-center gap-2">
          <BackupMergeControl />
          <Button size="sm" disabled={!online || runNow.isPending} onClick={() => runNow.mutate()}>
            <HardDriveDownload size={13} className={runNow.isPending ? "animate-pulse" : undefined} />
            Şimdi yedekle
          </Button>
        </div>
      }
      bodyClassName="space-y-4"
    >
      {/* Kapsam */}
      <div className="border-y border-subtle px-1 py-2">
        <div className="flex items-center gap-2 text-meta text-secondary">
          <Database size={13} className="shrink-0 text-icon" />
          <span>Yedekte neler var</span>
        </div>
        <p className="mt-1 text-meta text-muted">
          entity · link · event (geçmiş akışı) + tüm modül tabloları (bookmark, feed/item, todo, pomodoro, habit,
          review, opportunity, study, course/book, document, project, expense…) + ayarlar (setting).
        </p>
        <p className="mt-1 text-meta text-muted">
          "Birleştirerek içe aktar" yalnızca eksikleri ekler (tam geri dönüş değil). Gerçek felaket kurtarması uygulama
          dışıdır:{" "}
          <code className="text-secondary">
            make disaster-restore FILE=backups/&lt;dosya&gt;.gz CONFIRM=DISASTER-RESTORE
          </code>{" "}
          (öncesinde API ve worker durur, güvenlik yedeği alınır, sonrasında bütünlük doğrulanır).
        </p>
      </div>

      {/* Son yedek */}
      <div>
        <p className="mb-1.5 text-meta text-secondary">Son yedek</p>
        {!last ? (
          <p className="text-meta text-muted">Henüz yedek alınmamış — "Şimdi yedekle" ile başla.</p>
        ) : (
          <div className="flex flex-wrap items-center gap-2 border-y border-subtle px-1 py-2">
            <span className="min-w-0 flex-1 truncate text-body text-primary">{last.file}</span>
            <Chip>{formatBytes(last.size)}</Chip>
            <span className="text-meta text-muted">{relativeTime(last.at)}</span>
          </div>
        )}
        {last?.counts && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Chip tone="ok">{last.counts.entities} varlık</Chip>
            <Chip>{last.counts.events} olay</Chip>
            {top.map(([name, count]) => (
              <Chip key={name}>
                {name} {count}
              </Chip>
            ))}
          </div>
        )}
      </div>

      {/* Drive yukleme */}
      <div>
        <p className="mb-1.5 flex items-center gap-1.5 text-meta text-secondary">
          <CloudUpload size={13} className="shrink-0 text-icon" /> Drive yedeklemesi
        </p>
        {!data?.drive_folder_id ? (
          <p className="text-meta text-muted">
            Drive hedefi ayarlanmadı — yedekler yalnızca yerelde (backup_dir) tutulur.
          </p>
        ) : (
          <>
            <div className="flex items-center gap-2 border-y border-subtle px-1 py-2">
              <span className="min-w-0 flex-1 truncate text-body text-primary">{data.drive_folder_id}</span>
              <Chip tone={google?.connected ? "ok" : "warn"}>{google?.connected ? "Google bağlı" : "bağlı değil"}</Chip>
            </div>
            {data.last_drive_error && (
              <p className="mt-2 flex items-start gap-1.5 rounded-card border border-danger-border bg-danger-surface px-3 py-2 text-meta text-danger">
                Son yükleme başarısız: {data.last_drive_error.message}
              </p>
            )}
            {!data.last_drive_error && data.last_drive_upload && (
              <p className="mt-2 text-meta text-muted">
                Son yükleme: <span className="text-secondary">{data.last_drive_upload.file}</span> ·{" "}
                {relativeTime(data.last_drive_upload.at)}
              </p>
            )}
            {!data.last_drive_upload && !data.last_drive_error && (
              <p className="mt-2 text-meta text-muted">Henüz Drive'a yedek yüklenmedi.</p>
            )}
          </>
        )}
      </div>

      <p className={cx("border-t border-subtle pt-3 text-meta text-muted")}>
        Gece <strong className="font-medium text-secondary">{data?.next_backup_scheduled ?? "03:00"}</strong>'te
        otomatik yedek · <strong className="font-medium text-secondary">{data?.retention_days ?? 14}</strong> gün
        saklanır ·{" "}
        {data?.changes_since_backup === false ? (
          <>
            son yedekten beri değişiklik yok, bu tur <strong className="font-medium text-secondary">atlanacak</strong>
          </>
        ) : (
          <>
            anlamlı bir değişiklik yoksa o tur <strong className="font-medium text-secondary">atlanır</strong>
          </>
        )}{" "}
        · makine taşıma (macOS → Windows) için tek dosyanı Drive'dan alıp yeni makinede restore edersin.
      </p>
    </Section>
  );
}
