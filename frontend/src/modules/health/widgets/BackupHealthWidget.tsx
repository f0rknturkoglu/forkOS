import type { ReactNode } from "react";
import { invalidateAfter } from "@/core/invalidation";
import { useBackupStatus } from "@/core/runtimeQueries";
import { useMutation } from "@tanstack/react-query";
import { CloudUpload, Database, HardDriveDownload } from "lucide-react";
import { api } from "@/core/api";
import { BackupMergeControl } from "@/core/BackupMergeControl";
import { dataState, SectionFallback } from "@/core/DataState";
import { Button, Chip, Disclosure, Section, relativeTime, useToast } from "@/core/ui";

/** İnsan okur boyut. Tanılama paketi de aynı biçimi kullanır (tek sözlük). */
export function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.round(bytes / 1024)} KB`;
}

function topModules(counts: Record<string, number>, n: number): [string, number][] {
  return Object.entries(counts)
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n);
}

/** Yedek durumu satırı: solda sabit etiket, sağda durum. */
function BackupRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 border-b border-subtle py-2.5 last:border-b-0">
      <span className="w-40 shrink-0 text-meta text-secondary">{label}</span>
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">{children}</div>
    </div>
  );
}

/**
 * Yedekleme durumu: son yedek, yerel durum, bekleyen
 * değişiklik ve sıradaki zamanlanmış tur. Ayrıntılar (kapsam, felaket
 * kurtarma komutu) katlanır — ana kart yalnız durumu söyler.
 *
 * Dürüstlük kuralları:
 *  - "Şimdi yedekle" YEREL bir işlemdir: internet bağlantısına bağlanmaz.
 *  - `/backup/status` okunamazsa "Henüz yedek yok" DENMEZ: durum bilinmiyor der.
 */
export function BackupHealthWidget() {
  const toast = useToast();

  const backup = useBackupStatus();
  const status = backup.data;
  const statusState = dataState(backup);

  const runNow = useMutation({
    mutationFn: () => api.post<{ path: string; size: number }>("/backup"),
    onSuccess: (result) => {
      invalidateAfter("backup.write");
      toast.push(`Yedek alındı (${formatBytes(result.size)}).`, { tone: "ok" });
    },
    onError: (error: Error) => toast.push(`Yedek başarısız: ${error.message}`, { tone: "danger" }),
  });

  const last = status?.last_backup;
  const top = last?.counts ? topModules(last.counts.modules, 4) : [];

  return (
    <Section
      title="Yedekleme"
      action={
        <div className="flex items-center gap-2">
          <BackupMergeControl />
          <Button size="sm" disabled={runNow.isPending} onClick={() => runNow.mutate()}>
            <HardDriveDownload size={13} className={runNow.isPending ? "animate-pulse" : undefined} />
            Şimdi yedekle
          </Button>
        </div>
      }
    >
      {statusState !== "ready" ? (
        <SectionFallback state={statusState} what="Yedek durumu" onRetry={() => void backup.refetch()} />
      ) : (
        <div>
          <BackupRow label="Son yerel yedek">
            {!last ? (
              <span className="text-meta text-muted">Henüz yedek alınmamış — "Şimdi yedekle" ile başla.</span>
            ) : (
              <>
                <span className="min-w-0 flex-1 truncate text-body text-primary">{last.file}</span>
                <Chip>{formatBytes(last.size)}</Chip>
                <span className="text-meta text-muted">{relativeTime(last.at)}</span>
              </>
            )}
          </BackupRow>

          {last?.counts && (
            <BackupRow label="Yedek kapsamı">
              <Chip tone="ok">{last.counts.entities} varlık</Chip>
              <Chip>{last.counts.events} olay</Chip>
              {top.map(([name, count]) => (
                <Chip key={name}>
                  {name} {count}
                </Chip>
              ))}
            </BackupRow>
          )}

          <BackupRow label="Yerel durum">
            <span className="text-meta text-secondary">
              {status?.changes_since_backup === false
                ? "Son yedekten beri anlamlı değişiklik yok — sıradaki tur atlanır"
                : "Son yedekten beri değişiklik var — sıradaki turda yedeklenir"}
            </span>
          </BackupRow>

          <BackupRow label="Sıradaki yedek">
            <span className="text-meta text-secondary">Gece {status?.next_backup_scheduled ?? "bilinmiyor"}</span>
            <span className="text-meta text-muted">
              {status?.retention_days ? `${status.retention_days} gün saklanır` : "Saklama süresi bilinmiyor"}
            </span>
          </BackupRow>
        </div>
      )}

      <Disclosure summary="Felaket kurtarma ayrıntıları" className="mt-3 border-t border-subtle pt-3">
        <div className="stack-y-2 text-meta text-muted">
          <p className="flex items-start gap-2">
            <Database size={13} className="mt-0.5 shrink-0 text-icon" aria-hidden="true" />
            <span>
              Yedekte neler var: entity · link · event (geçmiş akışı) + tüm modül tabloları (bookmark, feed/item, todo,
              pomodoro, habit, review, opportunity, study, course/book, document, project, expense…) + ayarlar
              (setting).
            </span>
          </p>
          <p>
            "Birleştirerek içe aktar" yalnızca eksikleri ekler (tam geri dönüş değil). Gerçek felaket kurtarması
            uygulama dışıdır:{" "}
            <code className="text-secondary">
              make disaster-restore FILE=backups/&lt;dosya&gt;.gz CONFIRM=DISASTER-RESTORE
            </code>{" "}
            (öncesinde API ve worker durur, güvenlik yedeği alınır, sonrasında bütünlük doğrulanır).
          </p>
          <p>Makine taşıma (macOS → Windows): yerel yedek dosyasını yeni makineye taşıyıp geri yüklersin.</p>
        </div>
      </Disclosure>
    </Section>
  );
}
