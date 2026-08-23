import { useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CloudUpload, Database, HardDriveDownload, UploadCloud } from "lucide-react";
import { api } from "@/core/api";
import { Badge, Button, Section as Panel, cx, relativeTime, useToast } from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { useInvalidate, useOnline } from "@/lib/hooks";
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
  const invalidate = useInvalidate();
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

  const restoreRef = useRef<HTMLInputElement>(null);
  const restoreBackup = useMutation({
    mutationFn: (file: File) =>
      api.upload<{ restored: number }>("/backup/restore", file),
    onSuccess: (result) => {
      invalidate("backup-status", "activity");
      toast.push(
        `${result.restored} kayıt geri yüklendi — çakışan kayıtlara dokunulmadı.`,
        { tone: "ok" },
      );
    },
    onError: (error: Error) =>
      toast.push(`Geri yükleme başarısız: ${error.message}`, { tone: "danger" }),
  });

  async function pickRestore(file: File) {
    const ok = await confirmDialog({
      title: "Yedek geri yüklensin mi?",
      body:
        "Yedekteki kayıtlar EKLENIR; mevcut veriye dokunulmaz (çakışanlar atlanır). " +
        "İstediğin kadar tekrarlayabilirsin — işlem güvenli ve idempotent.",
      confirmLabel: "Geri yükle",
    });
    if (ok) restoreBackup.mutate(file);
  }

  const runNow = useMutation({
    mutationFn: () => api.post<{ path: string; size: number }>("/backup"),
    onSuccess: (result) => {
      invalidate("backup-status", "activity");
      toast.push(
        `Yedek alındı (${formatBytes(result.size)})${
          data?.drive_folder_id ? " — Drive'a da yükleniyor" : ""
        }`,
        { tone: "ok" },
      );
    },
    onError: (error: Error) => toast.push(`Yedek başarısız: ${error.message}`, { tone: "danger" }),
  });

  const last = data?.last_backup;
  const top = last?.counts ? topModules(last.counts.modules, 4) : [];

  return (
    <Panel
      title="Yedekleme"
      action={
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={() => restoreRef.current?.click()} disabled={!online || restoreBackup.isPending}>
            <UploadCloud size={13} />
            {restoreBackup.isPending ? "Yükleniyor…" : "Geri yükle"}
          </Button>
          <Button size="sm" disabled={!online || runNow.isPending} onClick={() => runNow.mutate()}>
            <HardDriveDownload size={13} className={runNow.isPending ? "animate-pulse" : undefined} />
            Şimdi yedekle
          </Button>
          <input
            ref={restoreRef}
            type="file"
            accept=".gz,.json,application/gzip,application/json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) pickRestore(file);
              e.target.value = "";
            }}
          />
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
          entity · link · event (geçmiş akışı) + tüm modül tabloları (bookmark, feed/item, todo,
          pomodoro, habit, review, opportunity, study, course/book, document, project, expense…)
          + ayarlar (setting).
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
            <Badge>{formatBytes(last.size)}</Badge>
            <span className="text-meta text-muted">{relativeTime(last.at)}</span>
          </div>
        )}
        {last?.counts && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Badge tone="ok">{last.counts.entities} varlık</Badge>
            <Badge>{last.counts.events} olay</Badge>
            {top.map(([name, count]) => (
              <Badge key={name}>{name} {count}</Badge>
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
              <span className="min-w-0 flex-1 truncate text-body text-primary">
                {data.drive_folder_id}
              </span>
              <Badge tone={google?.connected ? "ok" : "warn"}>
                {google?.connected ? "Google bağlı" : "bağlı değil"}
              </Badge>
            </div>
            {data.last_drive_error && (
              <p className="mt-2 flex items-start gap-1.5 rounded-card border border-danger-border bg-danger-surface px-3 py-2 text-meta text-danger">
                Son yükleme başarısız: {data.last_drive_error.message}
              </p>
            )}
            {!data.last_drive_error && data.last_drive_upload && (
              <p className="mt-2 text-meta text-muted">
                Son yükleme: <span className="text-secondary">{data.last_drive_upload.file}</span> · {relativeTime(data.last_drive_upload.at)}
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
        saklanır · makine taşıma (macOS → Windows) için tek dosyanı Drive'dan alıp yeni makinede restore edersin.
      </p>
    </Panel>
  );
}
