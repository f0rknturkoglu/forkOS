import type { FormEvent, RefObject } from "react";
import { allModules } from "@/core/registry";
import type { BackupStatus } from "@/core/types";
import { Button, Checkbox, Chip, FileInput, Input, Section, relativeTime } from "@/core/ui";

export type IntegrationStatus = { connected: boolean; login?: string | null };
export type MediaLink = { name: string; url: string; icon?: string };

export function ModulesSection({
  online,
  disabledModules,
  onToggle,
}: {
  online: boolean;
  disabledModules: string[];
  onToggle: (id: string) => void;
}) {
  return (
    <Section title="Modüller">
      <div className="grid grid-cols-2 gap-2">
        {allModules()
          .filter((m) => m.id !== "settings")
          .map((module) => (
            <Checkbox
              key={module.id}
              disabled={!online}
              checked={!disabledModules.includes(module.id)}
              onChange={() => onToggle(module.id)}
              label={module.title}
              className="rounded border border-subtle px-3 py-2"
            />
          ))}
      </div>
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
        Konum: <strong className="font-medium text-secondary">{location ?? "ayarlanmadı"}</strong> · Open-Meteo,
        anahtarsız.
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
}: {
  online: boolean;
  google?: IntegrationStatus;
  github?: IntegrationStatus;
  githubLogin: string;
  onGithubLogin: (value: string) => void;
  githubToken: string;
  onGithubToken: (value: string) => void;
  onConnectGithub: () => void;
}) {
  return (
    <Section title="Entegrasyonlar">
      <div className="flex items-center justify-between border-b border-subtle pb-3">
        <span className="text-body">Google</span>
        {google?.connected ? (
          <Chip tone="ok">bağlı</Chip>
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
        <div className="mb-2 flex justify-between">
          <span className="text-body">GitHub</span>
          <Chip tone={github?.connected ? "ok" : "neutral"}>
            {github?.connected ? (github.login ?? "bağlı") : "bağlı değil"}
          </Chip>
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

export function MediaLinksSection({
  online,
  tmdbKeyValue,
  onTmdbKey,
  rawgKeyValue,
  onRawgKey,
  media,
  onSave,
  onRemoveLink,
  mediaName,
  onMediaName,
  mediaUrl,
  onMediaUrl,
  onAddLink,
  innerRef,
}: {
  online: boolean;
  tmdbKeyValue: string;
  onTmdbKey: (value: string) => void;
  rawgKeyValue: string;
  onRawgKey: (value: string) => void;
  media: MediaLink[];
  onSave: (key: string, value: unknown) => void;
  onRemoveLink: (index: number) => void;
  mediaName: string;
  onMediaName: (value: string) => void;
  mediaUrl: string;
  onMediaUrl: (value: string) => void;
  onAddLink: () => void;
  innerRef: RefObject<HTMLDivElement>;
}) {
  return (
    <div
      id="media-links"
      ref={innerRef}
      tabIndex={-1}
      className="scroll-mt-4 rounded-card outline-none focus:ring-2 focus:ring-accent"
    >
      <Section title="Medya bağlantıları">
        <div className="mb-3 flex items-center gap-2">
          <Input
            disabled={!online}
            value={tmdbKeyValue}
            onChange={onTmdbKey}
            placeholder="TMDB API anahtarı (film/dizi araması)"
            className="min-w-0 flex-1"
            onBlur={(v) => {
              if (v.trim()) onSave("media.tmdb_key", v.trim());
            }}
          />
          <span className="shrink-0 text-meta text-muted">media.tmdb_key</span>
        </div>
        <div className="mb-3 flex items-center gap-2">
          <Input
            disabled={!online}
            value={rawgKeyValue}
            onChange={onRawgKey}
            placeholder="RAWG API anahtarı (oyun araması)"
            className="min-w-0 flex-1"
            onBlur={(v) => {
              if (v.trim()) onSave("media.rawg_key", v.trim());
            }}
          />
          <span className="shrink-0 text-meta text-muted">media.rawg_key</span>
        </div>
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
          <Button disabled={!online} onClick={onAddLink}>
            Ekle
          </Button>
        </div>
      </Section>
    </div>
  );
}

export function BackupSection({
  online,
  restoreRef,
  restorePending,
  onPickRestore,
  backupPending,
  onBackup,
  backupData,
  backupStatus,
}: {
  online: boolean;
  restoreRef: RefObject<HTMLInputElement>;
  restorePending: boolean;
  onPickRestore: (file: File) => void;
  backupPending: boolean;
  onBackup: () => void;
  backupData: { path: string; size: number } | undefined;
  backupStatus: BackupStatus | undefined;
}) {
  const last = backupStatus?.last_backup;
  const drive = backupStatus?.last_drive_upload;
  return (
    <Section title="Yedekleme / Export">
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
        <a href="/api/export/csv?module=expense" download className="rounded border border-strong px-2 py-1 text-meta">
          Expense CSV
        </a>
        <Button onClick={() => restoreRef.current?.click()} disabled={!online || restorePending}>
          {restorePending ? "yükleniyor…" : "geri yükle"}
        </Button>
        <Button variant="primary" onClick={onBackup} disabled={!online || backupPending}>
          şimdi yedekle
        </Button>
        <FileInput
          ref={restoreRef}
          accept=".gz,.json,application/gzip,application/json"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onPickRestore(file);
            e.target.value = "";
          }}
        />
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
