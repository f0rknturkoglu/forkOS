import type { FormEvent, RefObject } from "react";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Eye, EyeOff, X } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { allModules } from "@/core/registry";
import type { BackupStatus, SourceHealth } from "@/core/types";
import type { components } from "@/generated/api-schema";
import {
  Button,
  Checkbox,
  Chip,
  Field,
  IconButton,
  Input,
  NumberInput,
  Section,
  relativeTime,
  useTheme,
  useToast,
} from "@/core/ui";
import { BackupMergeControl } from "@/core/BackupMergeControl";
import { EXPORT_MODULE } from "@/modules/finance";
import type { Theme } from "@/core/ui";

/** Ayar yazma sozlesmesi: `PUT /settings/{key}`. Sayfa tek noktadan baglar. */
export type SaveFn = (key: string, value: unknown) => void;

export type IntegrationStatus = { connected: boolean; login?: string | null };
type MediaLink = { name: string; url: string; icon?: string };

/** Ayarlar sayfasinin alt seridi: bozuk kaynak ozeti + saglik sayfasi linki. */
export function SettingsSourceHealth({ sources }: { sources: SourceHealth[] }) {
  const broken = sources.filter((source) => source.status === "error").length;
  return (
    <div className="flex items-center justify-between gap-3 rounded-card border border-subtle bg-surface px-4 py-3">
      <span className="text-body text-primary">
        {broken === 0 ? "Tüm kaynaklar sağlıklı" : `${broken} kaynak hata veriyor`}
      </span>
      <a href="#/health" className="shrink-0 text-meta text-accent hover:underline">
        kaynak sağlığı
      </a>
    </div>
  );
}

/**
 * Sifre alani: API anahtarlari duz metin gorunmesin. Goz dugmesi yalnizca
 * GORUNURLUK icindir; deger kaydetme alandan cikinca (blur) olur ve bos
 * birakmak anahtari SILER -- eski `if (v.trim())` blokaji anahtari
 * temizlemeyi imkansiz kiliyordu.
 */
function SecretField({
  label,
  hint,
  value,
  onChange,
  onSave,
  disabled,
  placeholder,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (value: string) => void;
  onSave: (value: string) => void;
  disabled?: boolean;
  placeholder?: string;
}) {
  const [revealed, setRevealed] = useState(false);
  return (
    <div>
      <p className="mb-1 text-meta text-secondary">{label}</p>
      <div className="flex items-center gap-2">
        <Input
          type={revealed ? "text" : "password"}
          value={value}
          onChange={onChange}
          onBlur={(next) => onSave(next.trim())}
          disabled={disabled}
          placeholder={placeholder}
          ariaLabel={label}
          className="min-w-0 flex-1"
        />
        <IconButton
          title={revealed ? `${label} gizle` : `${label} göster`}
          onClick={() => setRevealed((current) => !current)}
          disabled={disabled}
        >
          {revealed ? <EyeOff size={14} /> : <Eye size={14} />}
        </IconButton>
        <span className="w-40 shrink-0 truncate text-meta text-muted">{hint}</span>
      </div>
    </div>
  );
}

/** Etiket listesi editoru: serbest metin gir, Enter ya da + ile ekle. */
export function ChipListEditor({
  values,
  onChange,
  placeholder,
  disabled,
  emptyLabel,
  ariaLabel,
}: {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder: string;
  disabled?: boolean;
  emptyLabel: string;
  ariaLabel: string;
}) {
  const [draft, setDraft] = useState("");
  /* Sunucu degeri refetch gelene kadar eski kalir; yerel liste aninda
     guncellenir ki ardisik ekleme/cikarma kaybolmasin. */
  const [items, setItems] = useState(values);
  useEffect(() => setItems(values), [values]);

  function commit(next: string[]) {
    setItems(next);
    onChange(next);
  }

  function add() {
    const value = draft.trim();
    setDraft("");
    if (!value || items.includes(value)) return;
    commit([...items, value]);
  }

  return (
    <div>
      {items.length === 0 ? (
        <p className="text-meta text-muted">{emptyLabel}</p>
      ) : (
        <ul className="mb-2 flex flex-wrap gap-1.5">
          {items.map((value) => (
            <li key={value}>
              <span className="inline-flex items-center gap-1 rounded-control border border-subtle bg-surface px-2 py-0.5 text-meta text-secondary">
                {value}
                <button
                  type="button"
                  aria-label={`${value} kaldır`}
                  disabled={disabled}
                  onClick={() => commit(items.filter((item) => item !== value))}
                  className="text-muted transition hover:text-danger disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <X size={11} />
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <Input
          value={draft}
          onChange={setDraft}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              add();
            }
          }}
          disabled={disabled}
          placeholder={placeholder}
          ariaLabel={ariaLabel}
          className="min-w-0 flex-1"
        />
        <Button onClick={add} disabled={disabled || !draft.trim()}>
          ekle
        </Button>
      </div>
    </div>
  );
}

export function ModulesSection({
  online,
  disabledModules,
  onToggle,
}: {
  online: boolean;
  disabledModules: string[];
  onToggle: (id: string) => void;
}) {
  const modules = allModules().filter((module) => module.id !== "settings");
  return (
    <Section title="Modüller">
      <p className="mb-3 text-meta text-muted">
        Kapatılan modülün rotası, Bugün widget'ları ve komutları devre dışı kalır; verisi silinmez. Ayarlar her zaman
        açıktır.
      </p>
      <ul className="divide-y divide-subtle rounded-card border border-subtle">
        {modules.map((module) => (
          <li key={module.id} className="px-3 py-2">
            <Checkbox
              checked={!disabledModules.includes(module.id)}
              onChange={() => onToggle(module.id)}
              disabled={!online}
              label={module.title}
            />
            {module.description && <p className="mt-0.5 pl-6 text-meta text-muted">{module.description}</p>}
          </li>
        ))}
      </ul>
    </Section>
  );
}

export function WeatherSection({
  online,
  weatherLoc,
  onWeatherLoc,
  location,
  onSubmit,
}: {
  online: boolean;
  weatherLoc: string | null;
  onWeatherLoc: (value: string) => void;
  location?: string;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Section title="Hava durumu">
      <p className="mb-2 text-meta text-muted">
        Konum: <strong className="font-medium text-secondary">{location ?? "ayarlanmadı"}</strong> · Open-Meteo
        anahtarsız; istek backend proxy'sinden geçer, tarayıcı dışarı çıkmaz.
      </p>
      <form className="flex gap-2" onSubmit={onSubmit}>
        <Input
          value={weatherLoc ?? location ?? ""}
          onChange={onWeatherLoc}
          disabled={!online}
          placeholder="Şehir adı — örn. İstanbul"
          className="min-w-0 flex-1"
        />
        <Button type="submit" disabled={!online}>
          kaydet
        </Button>
      </form>
    </Section>
  );
}

export function IntegrationsSection({
  online,
  google,
  github,
  githubLogin,
  onGithubLogin,
  githubToken,
  onGithubToken,
  onConnectGithub,
  onDisconnectGithub,
  onDisconnectGoogle,
  busy,
}: {
  online: boolean;
  google?: IntegrationStatus;
  github?: IntegrationStatus;
  githubLogin: string;
  onGithubLogin: (value: string) => void;
  githubToken: string;
  onGithubToken: (value: string) => void;
  onConnectGithub: () => void;
  onDisconnectGithub: () => void;
  onDisconnectGoogle: () => void;
  busy: boolean;
}) {
  return (
    <Section title="Entegrasyonlar">
      <div className="flex items-center justify-between gap-3 border-b border-subtle pb-3">
        <div className="min-w-0">
          <p className="text-body text-primary">Google Drive</p>
          <p className="text-meta text-muted">Belge arama ve senkron için Drive erişimi.</p>
        </div>
        {google?.connected ? (
          <div className="flex shrink-0 items-center gap-2">
            <Chip tone="ok">bağlı</Chip>
            <Button variant="danger" disabled={!online || busy} onClick={onDisconnectGoogle}>
              kes
            </Button>
          </div>
        ) : (
          <Button
            disabled={!online}
            onClick={() => {
              window.location.href = "/api/auth/google/start";
            }}
          >
            bağla
          </Button>
        )}
      </div>
      <div className="mt-3">
        <div className="mb-2 flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-body text-primary">GitHub</p>
            <p className="text-meta text-muted">Proje paneli, issue ve commit akışı için token.</p>
          </div>
          {github?.connected ? (
            <div className="flex shrink-0 items-center gap-2">
              <Chip tone="ok">{github.login ?? "bağlı"}</Chip>
              <Button variant="danger" disabled={!online || busy} onClick={onDisconnectGithub}>
                kes
              </Button>
            </div>
          ) : (
            <Chip>bağlı değil</Chip>
          )}
        </div>
        <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
          <Input value={githubLogin} disabled={!online} onChange={onGithubLogin} placeholder="login" />
          <Input
            type="password"
            value={githubToken}
            disabled={!online}
            onChange={onGithubToken}
            placeholder="fine-grained token"
          />
          <Button onClick={onConnectGithub} disabled={!online || !githubLogin || !githubToken}>
            kaydet
          </Button>
        </div>
      </div>
    </Section>
  );
}

export function MediaProvidersSection({
  online,
  keys,
  onKey,
  onSave,
  media,
  onRemoveLink,
  mediaName,
  onMediaName,
  mediaUrl,
  onMediaUrl,
  onAddLink,
  upcomingDays,
  onUpcomingDays,
  onSaveUpcomingDays,
  syncIntervalHours,
  onSyncIntervalHours,
  onSaveSyncIntervalHours,
  innerRef,
}: {
  online: boolean;
  keys: Record<string, string>;
  onKey: (key: string, value: string) => void;
  onSave: SaveFn;
  media: MediaLink[];
  onRemoveLink: (index: number) => void;
  mediaName: string;
  onMediaName: (value: string) => void;
  mediaUrl: string;
  onMediaUrl: (value: string) => void;
  onAddLink: () => void;
  upcomingDays: number;
  onUpcomingDays: (value: number) => void;
  onSaveUpcomingDays: () => void;
  syncIntervalHours: number;
  onSyncIntervalHours: (value: number) => void;
  onSaveSyncIntervalHours: () => void;
  innerRef: RefObject<HTMLDivElement>;
}) {
  return (
    <div
      id="media-links"
      ref={innerRef}
      tabIndex={-1}
      className="space-y-4 rounded-card scroll-mt-4 outline-none focus:ring-2 focus:ring-accent"
    >
      <Section title="Medya sağlayıcı anahtarları">
        <p className="mb-3 text-meta text-muted">
          API anahtarları yedeklere ve dışa aktarıma girmez. Alanı boş bırakıp dışına çıkmak anahtarı siler.
        </p>
        <p className="mb-3 text-meta text-muted">
          RAWG ve Kitsu desteği kaldırıldı; bu kaynaklardan gelen eski kayıtlar okunmaya devam eder.
        </p>
        <div className="space-y-2">
          <SecretField
            label="TMDB API anahtarı"
            hint="media.tmdb_key"
            placeholder="film ve dizi araması"
            disabled={!online}
            value={keys["media.tmdb_key"] ?? ""}
            onChange={(value) => onKey("media.tmdb_key", value)}
            onSave={(value) => onSave("media.tmdb_key", value)}
          />
          <SecretField
            label="IGDB Client ID"
            hint="media.igdb_client_id"
            placeholder="Twitch/IGDB istemci kimliği — oyun araması"
            disabled={!online}
            value={keys["media.igdb_client_id"] ?? ""}
            onChange={(value) => onKey("media.igdb_client_id", value)}
            onSave={(value) => onSave("media.igdb_client_id", value)}
          />
          <SecretField
            label="IGDB Client Secret"
            hint="media.igdb_client_secret"
            placeholder="Twitch/IGDB istemci sırrı — oyun araması"
            disabled={!online}
            value={keys["media.igdb_client_secret"] ?? ""}
            onChange={(value) => onKey("media.igdb_client_secret", value)}
            onSave={(value) => onSave("media.igdb_client_secret", value)}
          />
          <SecretField
            label="Google Books API anahtarı"
            hint="media.google_books_key"
            placeholder="kitap araması (isteğe bağlı)"
            disabled={!online}
            value={keys["media.google_books_key"] ?? ""}
            onChange={(value) => onKey("media.google_books_key", value)}
            onSave={(value) => onSave("media.google_books_key", value)}
          />
        </div>
      </Section>
      <Section title="Tarama ve yaklaşanlar">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Yaklaşan penceresi (gün)">
            <div onBlur={onSaveUpcomingDays}>
              <NumberInput value={upcomingDays} min={1} max={365} onChange={onUpcomingDays} className="w-full" />
            </div>
          </Field>
          <Field label="Otomatik tarama aralığı (saat)">
            <div onBlur={onSaveSyncIntervalHours}>
              <NumberInput
                value={syncIntervalHours}
                min={1}
                max={168}
                onChange={onSyncIntervalHours}
                className="w-full"
              />
            </div>
          </Field>
        </div>
        <p className="mt-2 text-meta text-muted">
          Yalnızca takip edilen kayıtlar bu aralıkla yeniden taranır; yaklaşanlar penceresi yayın takvimini belirler.
        </p>
      </Section>
      <MediaArtworkCacheSection online={online} />
      <Section title="Hızlı bağlantılar">
        <div className="space-y-2">
          {media.map((link, index) => (
            <div key={`${link.name}-${index}`} className="flex justify-between text-meta">
              <a href={link.url} target="_blank" rel="noreferrer" className="text-accent">
                {link.name} ↗
              </a>
              <Button variant="danger" disabled={!online} onClick={() => onRemoveLink(index)}>
                Sil
              </Button>
            </div>
          ))}
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
          <Input value={mediaName} disabled={!online} onChange={onMediaName} placeholder="Letterboxd" />
          <Input value={mediaUrl} disabled={!online} onChange={onMediaUrl} placeholder="https://…" />
          <Button disabled={!online || !mediaName || !mediaUrl} onClick={onAddLink}>
            Ekle
          </Button>
        </div>
      </Section>
    </div>
  );
}

type MediaArtworkStats = components["schemas"]["MediaArtworkStatsOut"];
type MediaArtworkPrune = components["schemas"]["MediaArtworkPruneOut"];

/** Insan dili boyut: 512 KB / 5.0 MB. */
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${Math.round(kb)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

/**
 * Gorsel onbellegi: saglayici kapaklarinin yerel kopyalari. Temizleme yalnizca
 * hicbir kaydin referans etmedigi ve 7 gunden eski dosyalari siler; kendi
 * yukledigin gorseller korunur.
 */
function MediaArtworkCacheSection({ online }: { online: boolean }) {
  const toast = useToast();
  const stats = useQuery({
    queryKey: ["media-artwork-stats"],
    queryFn: () => api.get<MediaArtworkStats>("/media/artwork/stats"),
  });
  const prune = useMutation({
    mutationFn: () => api.post<MediaArtworkPrune>("/media/artwork/prune"),
    onSuccess: (result) => {
      invalidateAfter("settings.write");
      void stats.refetch();
      toast.push(`${result.removed} görsel silindi, ${formatBytes(result.freed_bytes)} kazanıldı.`, { tone: "ok" });
    },
    onError: (error) => toast.push(`Önbellek temizlenemedi: ${error.message}`, { tone: "danger" }),
  });

  const data = stats.data;
  const summary =
    data && Number.isFinite(data.files) && Number.isFinite(data.bytes) && Number.isFinite(data.max_bytes)
      ? `${data.files} görsel · ${formatBytes(data.bytes)} / ${formatBytes(data.max_bytes)}`
      : stats.isLoading
        ? "Önbellek bilgisi yükleniyor…"
        : "Önbellek bilgisi okunamadı.";

  return (
    <Section title="Görsel önbelleği">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-meta text-secondary" aria-live="polite">
          {summary}
        </p>
        <Button
          size="sm"
          disabled={!online || prune.isPending || !data}
          onClick={() => prune.mutate()}
          ariaLabel="Önbelleği temizle"
        >
          Önbelleği temizle
        </Button>
      </div>
      <p className="mt-1.5 text-meta text-muted">
        Önbellek temizliği kendi görsellerine dokunmaz; yalnızca 7 günden eski ve hiçbir kayda bağlı olmayan kopyaları
        siler.
      </p>
    </Section>
  );
}

export function BackupSection({
  online,
  backupPending,
  onBackup,
  backupData,
  backupStatus,
  driveFolder,
  onDriveFolder,
  onSaveDriveFolder,
}: {
  online: boolean;
  backupPending: boolean;
  onBackup: () => void;
  backupData: { path: string; size: number } | undefined;
  backupStatus: BackupStatus | undefined;
  driveFolder: string;
  onDriveFolder: (value: string) => void;
  onSaveDriveFolder: (value: string) => void;
}) {
  const last = backupStatus?.last_backup;
  const drive = backupStatus?.last_drive_upload;
  return (
    <Section title="Yedekleme / Export">
      <div className="mb-3 flex items-center gap-2">
        <Input
          value={driveFolder}
          disabled={!online}
          onChange={onDriveFolder}
          onBlur={(value) => onSaveDriveFolder(value.trim())}
          placeholder="Google Drive hedef klasör kimliği"
          ariaLabel="Google Drive hedef klasör kimliği"
          className="min-w-0 flex-1"
        />
        <span className="shrink-0 text-meta text-muted">backup.drive_folder_id</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {(
          [
            ["JSON", "json"],
            ["Markdown", "markdown"],
            ["Bookmarks", "bookmarks"],
            ["OPML", "opml"],
            ["ICS", "ics"],
          ] as const
        ).map(([label, path]) => (
          <a
            key={path}
            href={`/api/export/${path}`}
            download
            className="rounded border border-strong px-2 py-1 text-meta text-secondary"
          >
            {label}
          </a>
        ))}
        {[
          ["Harcama (CSV)", EXPORT_MODULE],
          ["Görev (CSV)", "todo"],
          ["Fırsat (CSV)", "opportunity"],
          ["Gelir (CSV)", "income"],
          ["Not (CSV)", "note"],
        ].map(([label, moduleName]) => (
          <a
            key={moduleName}
            href={`/api/export/csv?module=${moduleName}`}
            download
            className="rounded border border-strong px-2 py-1 text-meta text-secondary hover:text-primary"
          >
            {label}
          </a>
        ))}
        <BackupMergeControl />
        <Button variant="primary" onClick={onBackup} disabled={!online || backupPending}>
          şimdi yedekle
        </Button>
      </div>
      {backupData && (
        <p className="mt-2 text-meta text-ok">
          {backupData.path} · {Math.round(backupData.size / 1024)} KB
        </p>
      )}
      {backupStatus && (
        <div className="mt-3 space-y-0.5 border-t border-subtle pt-3 text-meta text-muted">
          <p>
            Son yedek: {last ? `${last.file} · ${Math.round(last.size / 1024)} KB · ${relativeTime(last.at)}` : "—"}
          </p>
          <p>Drive hedefi: {backupStatus.drive_folder_id ? backupStatus.drive_folder_id : "ayarlanmadı"}</p>
          <p>
            Son Drive yüklemesi:{" "}
            {drive ? `${drive.file} · ${relativeTime(drive.at)}` : backupStatus.last_drive_error ? "başarısız" : "—"}
          </p>
          {backupStatus.last_drive_error && (
            <p className="text-danger">Yükleme hatası: {backupStatus.last_drive_error.message}</p>
          )}
          <p>Detaylı durum: Sağlık paneli → "Yedekleme" widget'ı.</p>
        </div>
      )}
    </Section>
  );
}

/**
 * Tema tercihi cihaza ozeldir (localStorage) -- DB'ye yazilmaz, cunku ayni
 * kayit farkli ekranlarda farkli olabilir. "Sistem" isletim sistemi ayarini
 * izler.
 */
export function ThemePicker() {
  const [theme, setTheme] = useTheme();
  const options: { id: Theme; label: string; hint: string }[] = [
    { id: "light", label: "Açık", hint: "sıcak beyaz" },
    { id: "dark", label: "Koyu", hint: "aynı tokenlar, koyu zemin" },
    { id: "system", label: "Sistem", hint: "işletim sistemi tercihini izle" },
  ];
  return (
    <div className="flex flex-col gap-2">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          onClick={() => setTheme(option.id)}
          aria-pressed={theme === option.id}
          className={`flex h-touch items-center gap-3 rounded-control border px-3 text-left transition ${
            theme === option.id ? "border-accent bg-accent-surface" : "border-subtle bg-surface hover:bg-surface-hover"
          }`}
        >
          <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${theme === option.id ? "bg-accent" : "bg-strong"}`} />
          <span className="text-body text-primary">{option.label}</span>
          <span className="text-meta text-muted">{option.hint}</span>
        </button>
      ))}
    </div>
  );
}
