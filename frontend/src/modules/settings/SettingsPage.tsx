import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useHashRoute } from "@/app/router";
import { api } from "@/core/api";
import type { AppSettings, BackupStatus, SourceHealth } from "@/core/types";
import { Input, NumberInput, PageFrame, PageHeader, Section, Textarea, useTheme, useToast } from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import type { Theme } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import {
  BackupSection,
  IntegrationsSection,
  MediaLinksSection,
  ModulesSection,
  WeatherSection,
  type IntegrationStatus,
} from "./SettingsSections";

export function SettingsSourceHealth({ sources }: { sources: SourceHealth[] }): JSX.Element {
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

export function SettingsPage() {
  const route = useHashRoute();
  const requestedSection = route.params.get("section");
  const toast = useToast();
  const online = useOnline();
  const restoreRef = useRef<HTMLInputElement>(null);
  const mediaLinksRef = useRef<HTMLDivElement>(null);
  const focusedSectionRef = useRef<string | null>(null);
  const restoreBackup = useMutation({
    mutationFn: (file: File) => api.upload<{ restored: number }>("/backup/restore", file),
    onSuccess: (result) => {
      invalidateAfter("backup.write");
      toast.push(`${result.restored} kayıt geri yüklendi — çakışanlara dokunulmadı.`, { tone: "ok" });
    },
    onError: (error: Error) => toast.push(`Geri yükleme başarısız: ${error.message}`, { tone: "danger" }),
  });
  async function pickRestore(file: File) {
    const ok = await confirmDialog({
      title: "Yedek geri yüklensin mi?",
      body:
        "Yedekteki kayıtlar eklenecek; mevcut veriye dokunulmaz (çakışanlar atlanır). " +
        "Tekrar çalıştırmak güvenlidir.",
      confirmLabel: "Geri yükle",
    });
    if (ok) restoreBackup.mutate(file);
  }
  const [weatherLoc, setWeatherLoc] = useState<string | null>(null);
  const [widgetOrder, setWidgetOrder] = useState<string | null>(null);
  const [pomodoroDefaults, setPomodoroDefaults] = useState<string | null>(null);
  const [thresholdsText, setThresholdsText] = useState<string | null>(null);
  const [intervalsText, setIntervalsText] = useState<string | null>(null);
  const [retentionDays, setRetentionDays] = useState<number | null>(null);
  const [tmdbKey, setTmdbKey] = useState<string | null>(null);
  const [rawgKey, setRawgKey] = useState<string | null>(null);
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<AppSettings>("/settings"),
  });
  const { data: sources = [] } = useQuery({
    queryKey: ["sources", "health"],
    queryFn: () => api.get<SourceHealth[]>("/sources/health"),
  });
  const { data: google } = useQuery({
    queryKey: ["google-status"],
    queryFn: () => api.get<IntegrationStatus>("/auth/google/status"),
  });
  const { data: github } = useQuery({
    queryKey: ["github-status"],
    queryFn: () => api.get<IntegrationStatus>("/auth/github/status"),
  });
  const { data: backupStatus } = useQuery({
    queryKey: ["backup-status"],
    queryFn: () => api.get<BackupStatus>("/backup/status"),
  });
  useEffect(() => {
    if (requestedSection !== "media-links") {
      focusedSectionRef.current = null;
      return;
    }
    if (!settings || focusedSectionRef.current === requestedSection) return;
    mediaLinksRef.current?.scrollIntoView({ block: "center" });
    mediaLinksRef.current?.focus();
    focusedSectionRef.current = requestedSection;
  }, [requestedSection, settings]);
  async function saveWeather(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = (weatherLoc ?? (settings?.["weather.location"] as string | undefined) ?? "").trim();
    if (!name) return;
    const geo = await fetch(
      "https://geocoding-api.open-meteo.com/v1/search?name=" + encodeURIComponent(name) + "&count=1&language=tr",
    )
      .then((r) => r.json())
      .catch(() => null);
    const hit = (geo as { results?: { latitude: number; longitude: number }[] } | null)?.results?.[0];
    if (!hit) {
      toast.push("Konum bulunamadı — başka bir ad dene.", { tone: "warn" });
      return;
    }
    await api.put("/settings/weather.location", { value: name });
    await api.put("/settings/weather.lat", { value: hit.latitude });
    await api.put("/settings/weather.lon", { value: hit.longitude });
    invalidateAfter("settings.write");
    toast.push("Hava durumu konumu kaydedildi.", { tone: "ok" });
  }
  const save = useMutation({
    mutationFn: ({ key, value }: { key: string; value: unknown }) => api.put(`/settings/${key}`, { value }),
    onSuccess: () => invalidateAfter("settings.write"),
  });
  const [githubLogin, setGithubLogin] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [mediaName, setMediaName] = useState("");
  const [mediaUrl, setMediaUrl] = useState("");
  const connectGithub = useMutation({
    mutationFn: () => api.post("/auth/github", { login: githubLogin, token: githubToken }),
    onSuccess: () => {
      setGithubToken("");
      invalidateAfter("settings.write");
    },
  });
  const backup = useMutation({
    mutationFn: () => api.post<{ path: string; size: number }>("/backup"),
    onSuccess: () => invalidateAfter("backup.write"),
  });
  if (!settings) return <div className="p-6 text-body text-muted">Ayarlar yükleniyor…</div>;
  const disabled = settings["modules.disabled"] ?? [];
  const media = settings["media.links"] ?? [];
  const toggleModule = (id: string) =>
    save.mutate({
      key: "modules.disabled",
      value: disabled.includes(id) ? disabled.filter((x) => x !== id) : [...disabled, id],
    });
  const addLink = () => {
    if (!mediaName || !mediaUrl) return;
    save.mutate({ key: "media.links", value: [...media, { name: mediaName, url: mediaUrl }] });
    setMediaName("");
    setMediaUrl("");
  };
  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Sistem" title="Ayarlar" />
      <p className="text-meta text-muted">Ayarlar veritabanında; localStorage yalnızca hızlı açılış önbelleğidir.</p>
      <div className="grid gap-4 xl:grid-cols-2">
        <ModulesSection online={online} disabledModules={disabled} onToggle={toggleModule} />
        <WeatherSection
          online={online}
          weatherLoc={weatherLoc}
          onWeatherLoc={(v) => setWeatherLoc(v)}
          location={settings["weather.location"] as string | undefined}
          onSubmit={saveWeather}
        />
        <Section title="Bugün sırası">
          <p className="mb-2 text-meta text-muted">Modül kimliklerini virgülle sırala.</p>
          <Input
            disabled={!online}
            value={widgetOrder ?? (settings["today.widget_order"] ?? []).join(", ")}
            onChange={setWidgetOrder}
            onBlur={(v) =>
              save.mutate({
                key: "today.widget_order",
                value: v
                  .split(",")
                  .map((x) => x.trim())
                  .filter(Boolean),
              })
            }
            className="w-full"
          />
        </Section>
        <Section title="Pomodoro">
          <Textarea
            disabled={!online}
            value={pomodoroDefaults ?? JSON.stringify(settings["pomodoro.defaults"], null, 2)}
            onChange={setPomodoroDefaults}
            onBlur={(v) => {
              try {
                save.mutate({ key: "pomodoro.defaults", value: JSON.parse(v) });
              } catch {
                /* düzenlerken bekle */
              }
            }}
            className="h-28 font-mono"
          />
        </Section>
        <Section title="Bildirim eşikleri">
          <Textarea
            disabled={!online}
            value={thresholdsText ?? JSON.stringify(settings["notifications.thresholds"], null, 2)}
            onChange={setThresholdsText}
            onBlur={(v) => {
              try {
                save.mutate({ key: "notifications.thresholds", value: JSON.parse(v) });
              } catch {
                /* düzenlerken bekle */
              }
            }}
            className="h-28 font-mono"
          />
        </Section>
        <Section title="Kaynak aralıkları">
          <Textarea
            value={intervalsText ?? JSON.stringify(settings["sources.intervals"], null, 2)}
            onChange={setIntervalsText}
            onBlur={(v) => {
              try {
                save.mutate({ key: "sources.intervals", value: JSON.parse(v) });
              } catch {
                /* düzenlerken bekle */
              }
            }}
            className="h-28 font-mono"
          />
          <label
            className="mt-3 flex items-center justify-between text-meta text-muted"
            onBlur={() =>
              save.mutate({
                key: "rss.retention_days",
                value: retentionDays ?? Number(settings["rss.retention_days"] ?? 90),
              })
            }
          >
            RSS retention (gün)
            <NumberInput
              value={retentionDays ?? Number(settings["rss.retention_days"] ?? 90)}
              onChange={setRetentionDays}
              className="w-24"
            />
          </label>
        </Section>
        <Section title="Tema">
          <ThemePicker />
        </Section>
        <IntegrationsSection
          online={online}
          google={google}
          github={github}
          githubLogin={githubLogin}
          onGithubLogin={(v) => setGithubLogin(v)}
          githubToken={githubToken}
          onGithubToken={(v) => setGithubToken(v)}
          onConnectGithub={() => connectGithub.mutate()}
        />
        <MediaLinksSection
          online={online}
          tmdbKeyValue={tmdbKey ?? (settings["media.tmdb_key"] as string | undefined) ?? ""}
          onTmdbKey={(v) => setTmdbKey(v)}
          rawgKeyValue={rawgKey ?? (settings["media.rawg_key"] as string | undefined) ?? ""}
          onRawgKey={(v) => setRawgKey(v)}
          media={media}
          onSave={(key, value) => save.mutate({ key, value })}
          onRemoveLink={(index) => save.mutate({ key: "media.links", value: media.filter((_, i) => i !== index) })}
          mediaName={mediaName}
          onMediaName={(v) => setMediaName(v)}
          mediaUrl={mediaUrl}
          onMediaUrl={(v) => setMediaUrl(v)}
          onAddLink={addLink}
          innerRef={mediaLinksRef}
        />
        <BackupSection
          online={online}
          restoreRef={restoreRef}
          restorePending={restoreBackup.isPending}
          onPickRestore={pickRestore}
          backupPending={backup.isPending}
          onBackup={() => backup.mutate()}
          backupData={backup.data}
          backupStatus={backupStatus}
        />
      </div>
      <SettingsSourceHealth sources={sources} />
    </PageFrame>
  );
}

/**
 * Tema tercihi cihaza ozeldir (localStorage) -- DB'ye yazilmaz, cunku ayni
 * kayit farkli ekranlarda farkli olabilir.
 */
function ThemePicker() {
  const [theme, setTheme] = useTheme();
  const options: { id: Theme; label: string; hint: string }[] = [
    { id: "light", label: "Açık", hint: "sıcak beyaz, varsayılan" },
    { id: "dark", label: "Koyu", hint: "aynı tokenlar, koyu zemin" },
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
