import type { FormEvent, RefObject } from "react";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ExternalLink, Eye, EyeOff, RefreshCw, X } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { allModules } from "@/core/registry";
import type { BackupStatus } from "@/core/types";
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
  Select,
  relativeTime,
  useTheme,
  useToast,
} from "@/core/ui";
import { BackupMergeControl } from "@/core/BackupMergeControl";
import { useWeather } from "@/modules/today/weather";
import type { Theme } from "@/core/ui";

/** Ayar yazma sozlesmesi: `PUT /settings/{key}`. Sayfa tek noktadan baglar. */
export type SaveFn = (key: string, value: unknown) => void;

export type IntegrationStatus = { connected: boolean; login?: string | null };

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

/* Otomasyon etiketleri: kullaniciya scheduler jargonu degil, ne oldugu yazilir. */
const AUTOMATION_LABELS: Record<string, string> = {
  opportunity: "İş fırsatları ve duyurular",
  calendar: "Takvim",
  github: "GitHub etkinliği",
};

const PROFILE_LABELS: Record<string, string> = {
  manual: "Elle — arka planda güncelleme yok",
  balanced: "Dengeli — önerilen",
  active: "Aktif — daha sık güncelleme",
};

export function ModulesSection({
  online,
  disabledModules,
  onToggle,
  automation,
  onToggleAutomation,
  profile,
  profiles,
  onProfile,
}: {
  online: boolean;
  disabledModules: string[];
  onToggle: (id: string) => void;
  automation: Record<string, { enabled: boolean; interval_minutes: number }>;
  onToggleAutomation: (domain: string, enabled: boolean) => void;
  profile: string;
  profiles: string[];
  onProfile: (profile: string) => void;
}) {
  const modules = allModules().filter((module) => module.id !== "settings");
  return (
    <>
      <Section title="Arka plan güncellemesi">
        <p className="mb-3 text-meta text-muted">
          Modülü göstermek ile arka planda güncellemek ayrı şeylerdir: bir modülü gizlesen de verisi tazelenebilir, ya
          da görünürken arka planda hiç dışarı çıkmamasını seçebilirsin. Kapalıyken elle yenileme her zaman çalışır.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-meta text-muted">Çalışma profili</span>
          <Select
            value={profile}
            onChange={onProfile}
            disabled={!online}
            ariaLabel="Otomasyon profili"
            className="w-56"
          >
            {profiles.map((id) => (
              <option key={id} value={id}>
                {PROFILE_LABELS[id] ?? id}
              </option>
            ))}
          </Select>
        </div>
        <ul className="mt-3 stack-divide-y divide-subtle rounded-card border border-subtle">
          {Object.entries(automation).map(([domain, state]) => (
            <li key={domain} className="px-3 py-2">
              <Checkbox
                checked={state.enabled}
                onChange={(checked) => onToggleAutomation(domain, checked)}
                disabled={!online}
                label={AUTOMATION_LABELS[domain] ?? domain}
              />
              <p className="mt-0.5 pl-6 text-meta text-muted">
                {state.interval_minutes < 60
                  ? `${state.interval_minutes} dakikada bir`
                  : `${Math.round(state.interval_minutes / 60)} saatte bir`}
              </p>
            </li>
          ))}
        </ul>
      </Section>
      <Section title="Modüller">
        <p className="mb-3 text-meta text-muted">
          Kapatılan modülün rotası, Home bileşenleri ve komutları devre dışı kalır; verisi silinmez ve arka plan
          güncellemesi bundan etkilenmez. Ayarlar her zaman açıktır.
        </p>
        <ul className="stack-divide-y divide-subtle rounded-card border border-subtle">
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
    </>
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
  const { asking, denied, requestLocation } = useWeather({ displayed: false });
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
      <Button size="sm" variant="ghost" disabled={!online || asking} onClick={requestLocation}>
        {asking ? "Konum izni isteniyor…" : "Konumumu kullan"}
      </Button>
      {denied && (
        <p role="status" className="text-meta text-muted">
          Konum izni verilmedi. Şehir adını elle girebilirsin.
        </p>
      )}
    </Section>
  );
}

/**
 * Kimlik bilgisi kilavuzu: kullaniciyi dogrudan yetkilendirme/token sayfasina
 * goturur. Baglanti yalnizca TIKLANINCA acilir; hicbir istek kendiliginden
 * gitmez (local-only kurali).
 */
function CredentialLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="mt-0.5 inline-flex items-center gap-1 text-micro text-accent hover:underline"
    >
      {label}
      <ExternalLink size={11} aria-hidden />
    </a>
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
  statusFailed,
  onRetryStatus,
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
  /**
   * Durum isteği düştüyse "bağlı değil" demek YANLIŞ olur: bağlantı
   * bilinmiyordur. İki hâl ayrı gösterilir ve yeniden denenebilir.
   */
  statusFailed?: boolean;
  onRetryStatus?: () => void;
}) {
  /** Bağlantı durumu bilinmiyorsa rozet bunu söyler, "bağlı değil" demez. */
  const connectionChip = (status?: IntegrationStatus) =>
    statusFailed ? (
      <Chip tone="warn">durum alınamadı</Chip>
    ) : status?.connected ? (
      <Chip tone="ok">bağlı</Chip>
    ) : (
      <Chip tone="danger">bağlı değil</Chip>
    );

  return (
    <Section
      title="Bulut & Geliştirici"
      action={
        statusFailed && onRetryStatus ? (
          <Button variant="ghost" size="sm" onClick={onRetryStatus}>
            <RefreshCw size={13} /> Yeniden dene
          </Button>
        ) : undefined
      }
    >
      <div className="flex items-center justify-between gap-3 border-b border-subtle pb-3">
        <div className="min-w-0">
          <p className="text-body text-primary">Google Calendar</p>
          <p className="text-meta text-muted">Takvim etkinliklerini senkronlamak için erişim.</p>
          <CredentialLink
            href="https://console.cloud.google.com/apis/credentials"
            label="Calendar API kimlik bilgileri"
          />
        </div>
        {google?.connected ? (
          <div className="flex shrink-0 items-center gap-2">
            {connectionChip(google)}
            <Button variant="danger" disabled={!online || busy} onClick={onDisconnectGoogle}>
              kes
            </Button>
          </div>
        ) : (
          <div className="flex shrink-0 items-center gap-2">
            {connectionChip(google)}
            <Button
              disabled={!online}
              onClick={() => {
                window.location.href = "/api/auth/google/start";
              }}
            >
              bağla
            </Button>
          </div>
        )}
      </div>
      <div className="mt-3">
        <div className="mb-2 flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-body text-primary">GitHub</p>
            <p className="text-meta text-muted">Proje paneli, issue ve commit akışı için token.</p>
            <CredentialLink href="https://github.com/settings/tokens" label="Personal access token oluştur" />
          </div>
          {github?.connected ? (
            <div className="flex shrink-0 items-center gap-2">
              {connectionChip(github)}
              <Button variant="danger" disabled={!online || busy} onClick={onDisconnectGithub}>
                kes
              </Button>
            </div>
          ) : (
            connectionChip(github)
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

export function BackupSection({
  online,
  backupPending,
  onBackup,
  backupData,
  backupStatus,
}: {
  online: boolean;
  backupPending: boolean;
  onBackup: () => void;
  backupData: { path: string; size: number } | undefined;
  backupStatus: BackupStatus | undefined;
}) {
  const last = backupStatus?.last_backup;
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
        {[
          ["Görev (CSV)", "todo"],
          ["Fırsat (CSV)", "opportunity"],
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
        <div className="mt-3 stack-y-0.5 border-t border-subtle pt-3 text-meta text-muted">
          <p>
            Son yedek: {last ? `${last.file} · ${Math.round(last.size / 1024)} KB · ${relativeTime(last.at)}` : "—"}
          </p>
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
