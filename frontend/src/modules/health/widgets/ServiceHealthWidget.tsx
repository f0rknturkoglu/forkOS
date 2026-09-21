import { useBackupStatus, useSystemStats } from "@/core/runtimeQueries";
import { Activity, DatabaseBackup } from "lucide-react";
import { runStateView, type StatusTone } from "@/core/sourceStatus";
import { dataState, SectionFallback } from "@/core/DataState";
import { Chip, Section, relativeTime } from "@/core/ui";

const STALE_BACKUP_HOURS = 48;

/** Bir servis satırının okunabilir durumu: etiket + ton + (varsa) açıklama. */
export interface ServiceStateView {
  label: string;
  tone: StatusTone;
  attention: boolean;
  hint: string | null;
}

/**
 * `kapalı` / `bilinmiyor` etiketleri kaynak durumu sözlüğünden gelir (tek
 * sözlük): ikisi de KIRMIZI DEĞİLDİR.
 */
function neutralState(state: "disabled" | "unknown", hint: string): ServiceStateView {
  const view = runStateView(state);
  return { label: view.label, tone: view.tone, attention: view.attention, hint };
}

/**
 * Worker durumu (§57). Üç ayrı şey AYRI söylenir:
 *   - `disabled` : kullanıcı worker'ı bilerek kapatmıştır → nötr "kapalı".
 *   - `unknown`  : worker açık ama kalp atışı kaydı yok (henüz başlamamış
 *                  olabilir) → nötr "bilinmiyor", hata değil.
 *   - `stale`    : kalp atışı bayatladı → gerçekten durmuş, kırmızı.
 * Bu ayrımı hem bu kart hem sayfanın "Genel bakış" özeti kullanır.
 */
export function workerStatusView(status: string | null | undefined): ServiceStateView {
  if (status === "healthy") return { label: "çalışıyor", tone: "ok", attention: false, hint: null };
  if (status === "stale") {
    return { label: "durdu — arka plan işleri çalışmıyor", tone: "danger", attention: true, hint: null };
  }
  if (status === "disabled") {
    return neutralState("disabled", "Arka plan işleri bilerek kapalı: elle yenileme kullanılıyor.");
  }
  if (status === "unknown") {
    return neutralState("unknown", "Worker açık ama kayıtlı kalp atışı yok — henüz başlamamış olabilir.");
  }
  if (!status) return neutralState("unknown", "Worker durumu bildirilmedi.");
  // Tanımadığımız bir değer: uydurma etiket yok, olduğu gibi ve nötr gösterilir.
  return { label: status, tone: "neutral", attention: false, hint: null };
}

/**
 * Servis güvenilirlik kartı (Faz 26): worker heartbeat + yedek bayatlığı.
 *
 * Her satır KENDİ sorgusunun durumunu taşır: biri düştüğünde yalnız o satır
 * "alınamadı" der, diğeri konuşmaya devam eder. Okunamayan bir yedek durumu
 * "henüz yedek yok" OLARAK gösterilmez (bilinmiyor ≠ yok).
 */
export function ServiceHealthWidget() {
  const stats = useSystemStats();
  const backup = useBackupStatus();

  const workerState = dataState(stats);
  const backupState = dataState(backup);
  const worker = workerStatusView(stats.data?.worker.status);

  const lastBackupAt = backup.data?.last_backup?.at ? new Date(backup.data.last_backup.at).getTime() : null;
  // Anlamlı veri değişmediyse zamanlanmış yedek BİLEREK atlanır: eski tarih
  // tek başına sorun değildir, yalnızca bekleyen değişiklik varsa uyarır.
  const changesPending = backup.data?.changes_since_backup ?? false;
  const backupStale =
    lastBackupAt !== null && changesPending && Date.now() - lastBackupAt > STALE_BACKUP_HOURS * 3_600_000;

  return (
    <Section title="Servis sağlığı" hint="worker kalp atışı · yedek tazeliği" bodyClassName="space-y-3">
      {workerState !== "ready" ? (
        <SectionFallback state={workerState} what="Worker durumu" onRetry={() => void stats.refetch()} />
      ) : (
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-2 text-meta">
            <span className="flex items-center gap-1.5 text-muted">
              <Activity size={13} className="text-icon" aria-hidden="true" /> Worker
            </span>
            <Chip tone={worker.tone}>{worker.label}</Chip>
          </div>
          {worker.hint && <p className="text-meta text-muted">{worker.hint}</p>}
          {stats.data?.worker.heartbeat_at && (
            <p className="text-meta text-muted">Son kalp atışı: {relativeTime(stats.data.worker.heartbeat_at)}</p>
          )}
        </div>
      )}

      {backupState !== "ready" ? (
        <SectionFallback state={backupState} what="Yedek durumu" onRetry={() => void backup.refetch()} />
      ) : (
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-2 text-meta">
            <span className="flex items-center gap-1.5 text-muted">
              <DatabaseBackup size={13} className="text-icon" aria-hidden="true" /> Yedek
            </span>
            {backupStale ? (
              <Chip tone="warn">eski — {STALE_BACKUP_HOURS} saatten uzun süredir yok</Chip>
            ) : lastBackupAt !== null ? (
              <Chip tone="ok">{changesPending ? "güncel" : "güncel · değişiklik yok"}</Chip>
            ) : (
              <Chip>henüz yedek yok</Chip>
            )}
          </div>
          {backup.data?.last_backup?.at && (
            <p className="text-meta text-muted">Son yedek: {relativeTime(backup.data.last_backup.at)}</p>
          )}
        </div>
      )}
    </Section>
  );
}
