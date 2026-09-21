import { useState } from "react";
import { useSystemStats } from "@/core/runtimeQueries";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, Briefcase, Clock4, Cpu, HardDrive, MemoryStick, RefreshCw } from "lucide-react";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import type { SystemStats } from "@/core/types";
import { Button, Checkbox, Chip, Input, Section, relativeTime, useToast } from "@/core/ui";
import { ChipListEditor } from "./SettingsSections";
import type { SaveFn } from "./SettingsSections";

/** `opportunity.career_profile`: Career Ops zekasinin kullandigi profil. */
export interface CareerProfile {
  current_location: string;
  authorized_countries: string[];
  willing_to_relocate: boolean;
}

/** `/proc/meminfo` kB verir. */
function gbFromKb(kilobytes: number | null | undefined): string {
  if (!kilobytes) return "—";
  return `${(kilobytes / 1048576).toFixed(1)} GB`;
}

/** `os.statvfs` bayt verir -- ayri cevrilmezse 1000 kat sisiyor. */
function gbFromBytes(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  if (bytes < 1073741824) return `${Math.round(bytes / 1048576)} MB`;
  return `${(bytes / 1073741824).toFixed(1)} GB`;
}

function uptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days} gün ${hours} sa`;
  if (hours > 0) return `${hours} sa ${minutes} dk`;
  return `${minutes} dk`;
}

export function CareerProfileSection({
  online,
  profile,
  onSave,
}: {
  online: boolean;
  profile: CareerProfile;
  onSave: SaveFn;
}) {
  const [location, setLocation] = useState(profile.current_location);

  /** Uc alani birlikte yazar: kismi guncelleme profili bozmasin. */
  const commit = (next: Partial<CareerProfile>) => onSave("opportunity.career_profile", { ...profile, ...next });

  return (
    <Section title="Kariyer profili">
      <p className="mb-3 text-meta text-muted">
        Fırsat değerlendirmesi ve eşleşme skoru bu profili kullanır; ilanları senin konumuna ve çalışma iznine göre
        yorumlar.
      </p>
      <label className="mb-3 block text-meta text-secondary">
        Mevcut konum
        <Input
          value={location}
          disabled={!online}
          onChange={setLocation}
          onBlur={(value) => commit({ current_location: value.trim() })}
          placeholder="Ankara, Türkiye"
          ariaLabel="Mevcut konum"
          className="mt-1"
        />
      </label>
      <div className="mb-3">
        <p className="mb-1 flex items-center gap-1.5 text-meta text-secondary">
          <Briefcase size={13} className="text-icon" /> Çalışma izni olan ülkeler
        </p>
        <ChipListEditor
          values={profile.authorized_countries}
          onChange={(next) => commit({ authorized_countries: next })}
          disabled={!online}
          placeholder="Türkiye"
          emptyLabel="Henüz ülke eklenmedi."
          ariaLabel="Çalışma izni olan ülke"
        />
      </div>
      <Checkbox
        checked={profile.willing_to_relocate}
        disabled={!online}
        onChange={(value) => commit({ willing_to_relocate: value })}
        label="Taşınmaya ve yerinde (on-site) çalışmaya açığım"
      />
    </Section>
  );
}

export function TodayFlowSection({
  online,
  autoSuggestions,
  subreddits,
  onSave,
}: {
  online: boolean;
  autoSuggestions: boolean;
  subreddits: string[];
  onSave: SaveFn;
}) {
  return (
    <Section title="Akış ve öneriler">
      <div className="mb-3">
        <Checkbox
          checked={autoSuggestions}
          disabled={!online}
          onChange={(value) => onSave("today.auto_suggestions", value)}
          label="Home akışında akıllı görev ve RSS önerilerini göster"
        />
        <p className="mt-1 pl-6 text-meta text-muted">
          Kapanınca Home yalnızca kendi planını ve bileşenlerini gösterir; hiçbir veri silinmez.
        </p>
      </div>
      <p className="mb-1 text-meta text-secondary">Takip edilen subreddit'ler</p>
      <ChipListEditor
        values={subreddits}
        onChange={(next) => onSave("news.subreddits", next)}
        disabled={!online}
        placeholder="rust"
        emptyLabel="Liste boş — Home akışı varsayılan subreddit'leri kullanır."
        ariaLabel="Subreddit adı"
      />
    </Section>
  );
}

type StorageReport = {
  database: {
    total_bytes: number;
    tables: { name: string; bytes: number; rows: number }[];
    rows: Record<string, number>;
    wal: { bytes: number } | null;
  };
  files: Record<string, number>;
  warnings: { key: string; label: string; used: number; limit: number }[];
  maintenance?: {
    day: string;
    at: string;
    status: string;
    results: Record<string, Record<string, number>>;
    errors: string[];
  } | null;
};

function formatMaintenancePruned(results?: Record<string, Record<string, number>> | null): string {
  if (!results) return "temizleme kaydı yok";
  const retention = results.retention ?? {};
  const rss = results.rss ?? {};
  const artwork = results.artwork ?? {};
  const parts: string[] = [];
  if (retention.source_run) parts.push(`${retention.source_run} kaynak koşusu`);
  if (retention.source_sync_batch) parts.push(`${retention.source_sync_batch} kuyruk`);
  if (retention.notification) parts.push(`${retention.notification} bildirim`);
  if (rss.feed_item) parts.push(`${rss.feed_item} RSS öğesi`);
  if (artwork.files) parts.push(`${artwork.files} görsel`);
  return parts.length > 0 ? parts.join(", ") : "temizlenecek eski veri bulunamadı";
}

const FILE_LABELS: Record<string, string> = {
  documents: "Yerel belgeler",
  attachments: "Not ekleri",
  media_artwork: "Medya görsel önbelleği",
  scraper_cache: "Scraper önbelleği",
  backups: "Yedekler",
};

const ROW_LABELS: Record<string, string> = {
  source_run: "Kaynak koşuları",
  source_sync_batch: "Yenileme kuyruğu",
  event: "Olay geçmişi",
  notification: "Bildirimler",
};

/**
 * Depolama dokumu: "forkOS ne kadar disk kullaniyor, hangi veri buyuyor?"
 *
 * Yalnizca BURADA, elle tazelenerek okunur; surekli polling yapmaz (teshis
 * ekrani, canli gosterge degil).
 */
export function StorageReportSection() {
  const { data, isFetching, refetch } = useQuery({
    queryKey: ["storage-report"],
    queryFn: () => api.get<StorageReport>("/system/storage"),
    refetchInterval: false,
    staleTime: 30_000,
  });

  // Alanlar SAVUNMALI okunur: teshis ekrani eksik/bozuk bir yanit yuzunden
  // cokmemeli (bu ekran bir sorunu ANLATMAK icin var).
  const database = data?.database;
  const files = Object.entries(data?.files ?? {});
  const rows = Object.entries(database?.rows ?? {});
  const tables = database?.tables ?? [];
  const alerts = data?.warnings ?? [];

  return (
    <Section title="Depolama">
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="text-meta text-muted">
          PostgreSQL {gbFromBytes(database?.total_bytes)}
          {database?.wal ? ` · WAL ${gbFromBytes(database.wal.bytes)}` : ""}
        </span>
        <Button variant="ghost" onClick={() => void refetch()} disabled={isFetching} className="text-meta">
          {isFetching ? "Okunuyor…" : "Yenile"}
        </Button>
      </div>

      {alerts.length > 0 && (
        <ul className="mb-3 space-y-1 rounded-card border border-subtle bg-surface p-2 text-meta text-warn">
          {alerts.map((alert) => (
            <li key={alert.key} className="flex items-center gap-1.5">
              <AlertTriangle size={13} className="shrink-0" />
              {alert.label}: {gbFromBytes(alert.used)} / sınır {gbFromBytes(alert.limit)}
            </li>
          ))}
        </ul>
      )}

      <div className="grid gap-3 text-meta sm:grid-cols-2">
        <div>
          <p className="mb-1 text-muted">Dosyalar</p>
          <ul className="space-y-0.5">
            {files.map(([key, bytes]) => (
              <li key={key} className="flex items-center justify-between gap-2">
                <span className="truncate text-secondary">{FILE_LABELS[key] ?? key}</span>
                <span className="tabular-nums text-primary">{gbFromBytes(bytes)}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-1 text-muted">Kayıtlar</p>
          <ul className="space-y-0.5">
            {rows.map(([key, count]) => (
              <li key={key} className="flex items-center justify-between gap-2">
                <span className="truncate text-secondary">{ROW_LABELS[key] ?? key}</span>
                <span className="tabular-nums text-primary">{count.toLocaleString("tr-TR")}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {tables.length > 0 && (
        <div className="mt-3">
          <p className="mb-1 text-muted">En büyük tablolar</p>
          <ul className="space-y-0.5 text-meta">
            {tables.slice(0, 6).map((table) => (
              <li key={table.name} className="flex items-center justify-between gap-2">
                <span className="truncate text-secondary">{table.name}</span>
                <span className="tabular-nums text-primary">{gbFromBytes(table.bytes)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-1 text-micro text-muted">PostgreSQL istatistiklerinden; satır sayıları tahminîdir.</p>
        </div>
      )}

      <div className="mt-3 rounded-card border border-subtle bg-surface p-2.5 text-meta">
        <div className="flex items-center justify-between text-secondary">
          <span className="font-medium text-primary">Otomatik hafif bakım</span>
          <span className="text-micro text-muted">Sonraki: her gün 04:00 / açılışta</span>
        </div>
        <p className="mt-1 text-micro text-muted">
          {data?.maintenance?.at ? (
            <>
              Son bakım: <span className="text-secondary">{relativeTime(data.maintenance.at)}</span> · Temizlenen:{" "}
              <span className="text-secondary">{formatMaintenancePruned(data.maintenance.results)}</span>
            </>
          ) : (
            "Kaynak koşuları, bildirimler ve yetim medya görselleri günlük bakımla sınırlandırılır."
          )}
        </p>
      </div>
    </Section>
  );
}

export function SystemDiagnosticsSection() {
  const toast = useToast();
  const { data } = useSystemStats();
  const refresh = useMutation({
    mutationFn: () => api.post<{ status: string }>("/system/refresh"),
    onSuccess: () => {
      invalidateAfter("settings.write");
      toast.push("Arka plan senkronu başlatıldı.", { tone: "ok" });
    },
    onError: (error) => toast.push(`Senkron başlatılamadı: ${error.message}`, { tone: "danger" }),
  });

  const memoryUsedShare =
    data?.mem_total_kb && data.mem_available_kb !== null && data.mem_available_kb !== undefined
      ? 1 - data.mem_available_kb / data.mem_total_kb
      : null;
  const diskFreeShare = data?.disk ? data.disk.free / data.disk.total : null;
  const worker = data?.worker;
  const workerTone = worker?.status === "healthy" ? "ok" : worker?.status === "stale" ? "danger" : "neutral";
  const workerLabel =
    worker?.status === "healthy"
      ? "sağlıklı"
      : worker?.status === "stale"
        ? "gecikmiş"
        : worker?.status === "disabled"
          ? "kapalı — elle senkron"
          : "bilinmiyor";

  return (
    <Section title="Sistem teşhisi">
      <div className="grid grid-cols-2 gap-3 text-meta sm:grid-cols-4">
        <div>
          <p className="flex items-center gap-1.5 text-muted">
            <Cpu size={13} className="text-icon" /> CPU
          </p>
          <p className="tabular-nums text-body text-primary">
            {data?.cpu_pct === null || data?.cpu_pct === undefined ? "ölçülüyor…" : `%${Math.round(data.cpu_pct)}`}
          </p>
          <p className="tabular-nums text-micro text-muted">
            yük: {data ? data.load.map((value) => value.toFixed(2)).join(" · ") || "—" : "—"}
          </p>
        </div>
        <div>
          <p className="flex items-center gap-1.5 text-muted">
            <MemoryStick size={13} className="text-icon" /> Bellek
          </p>
          <p className="tabular-nums text-body text-primary">
            {memoryUsedShare === null ? "—" : `%${Math.round(memoryUsedShare * 100)}`}
          </p>
          <p className="tabular-nums text-micro text-muted">
            {gbFromKb(data?.mem_total_kb ? data.mem_total_kb - (data.mem_available_kb ?? 0) : null)} /{" "}
            {gbFromKb(data?.mem_total_kb)}
          </p>
        </div>
        <div>
          <p className="flex items-center gap-1.5 text-muted">
            <HardDrive size={13} className="text-icon" /> Disk
          </p>
          <p className="tabular-nums text-body text-primary">{gbFromBytes(data?.disk?.free)}</p>
          <p className="text-micro text-muted">
            boş {diskFreeShare === null ? "—" : `(%${Math.round(diskFreeShare * 100)})`}
          </p>
        </div>
        <div>
          <p className="flex items-center gap-1.5 text-muted">
            <Clock4 size={13} className="text-icon" /> Çalışma süresi
          </p>
          <p className="tabular-nums text-body text-primary">{data ? uptime(data.uptime_s) : "—"}</p>
          <p className="text-micro text-muted">{data?.cpu_count ?? "—"} çekirdek</p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-subtle pt-3">
        <span className="flex items-center gap-2 text-meta">
          <Chip tone={workerTone}>
            <Activity size={11} /> arka plan: {workerLabel}
          </Chip>
          <span className="text-muted">
            {worker?.heartbeat_at ? `son kalp atışı ${relativeTime(worker.heartbeat_at)}` : "kalp atışı yok"}
          </span>
        </span>
        <Button onClick={() => refresh.mutate()} disabled={refresh.isPending}>
          <RefreshCw size={13} /> Şimdi senkronize et
        </Button>
      </div>
    </Section>
  );
}

/**
 * Tehlikeli bolge: `POST /settings/reset` butun kullanici ayarlarini siler.
 * OAuth token'lari ayri tabloda oldugu icin baglantilar kesilmez; metin bunu
 * acikca soyler ki kullanici ne kaybettigini bilsin.
 */
export function DangerZoneSection({ onReset, busy }: { onReset: () => void; busy: boolean }) {
  async function confirmReset() {
    const ok = await confirmDialog({
      title: "Ayarlar varsayılana dönsün mü?",
      body: "Modül tercihleri, Home düzeni, hava durumu konumu, medya API anahtarları ve yedekleme klasörü silinir. Verileriniz (notlar, görevler, fırsatlar) etkilenmez; bağlı hesaplar bağlı kalır.",
      confirmLabel: "Ayarları sıfırla",
      tone: "danger",
    });
    if (ok) onReset();
  }

  return (
    <Section title="Tehlikeli bölge">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-start gap-2 text-meta text-muted">
          <AlertTriangle size={14} className="mt-0.5 shrink-0 text-warn" />
          Yalnızca tercihleri siler; kayıtlarınıza dokunmaz.
        </p>
        <Button variant="danger" disabled={busy} onClick={confirmReset}>
          Ayarları varsayılana döndür
        </Button>
      </div>
    </Section>
  );
}
