import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useHashRoute } from "@/app/router";
import { api } from "@/core/api";
import { allModules } from "@/core/registry";
import { SourceHealthAccordion } from "@/core/SourceHealthAccordion";
import type { AppSettings, BackupStatus, SourceHealth } from "@/core/types";
import {Button, Checkbox, Chip, FileInput, Input, NumberInput, PageFrame, PageHeader, Section, Textarea, relativeTime, useTheme, useToast} from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import type { Theme } from "@/core/ui";
import {useOnline} from "@/lib/hooks";

type IntegrationStatus = { connected: boolean; login?: string | null };

export function SettingsSourceHealth({ sources }: { sources: SourceHealth[] }): JSX.Element {
  const [open, setOpen] = useState(false);
  return <SourceHealthAccordion title="Kaynak sağlığı" sources={sources} open={open} onOpenChange={setOpen} />;
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
      body: "Yedekteki kayıtlar eklenecek; mevcut veriye dokunulmaz (çakışanlar atlanır). Tekrar çalıştırmak güvenlidir.",
      confirmLabel: "Geri yükle",
    });
    if (ok) restoreBackup.mutate(file);
  }
  const [weatherLoc, setWeatherLoc] = useState<string | null>(null); const [widgetOrder, setWidgetOrder] = useState<string | null>(null); const [pomodoroDefaults, setPomodoroDefaults] = useState<string | null>(null); const [thresholdsText, setThresholdsText] = useState<string | null>(null); const [intervalsText, setIntervalsText] = useState<string | null>(null); const [retentionDays, setRetentionDays] = useState<number | null>(null); const [tmdbKey, setTmdbKey] = useState<string | null>(null); const [rawgKey, setRawgKey] = useState<string | null>(null);
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: () => api.get<AppSettings>("/settings") });
  const { data: sources = [] } = useQuery({ queryKey: ["sources", "health"], queryFn: () => api.get<SourceHealth[]>("/sources/health") });
  const { data: google } = useQuery({ queryKey: ["google-status"], queryFn: () => api.get<IntegrationStatus>("/auth/google/status") });
  const { data: github } = useQuery({ queryKey: ["github-status"], queryFn: () => api.get<IntegrationStatus>("/auth/github/status") });
  const { data: backupStatus } = useQuery({ queryKey: ["backup-status"], queryFn: () => api.get<BackupStatus>("/backup/status") });
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
    const name = (weatherLoc ?? ((settings?.["weather.location"] as string | undefined) ?? "")).trim();
    if (!name) return;
    const geo = await fetch(
      "https://geocoding-api.open-meteo.com/v1/search?name=" + encodeURIComponent(name) + "&count=1&language=tr",
    ).then((r) => r.json()).catch(() => null);
    const hit = (geo as { results?: { latitude: number; longitude: number }[] } | null)?.results?.[0];
    if (!hit) { toast.push("Konum bulunamadı — başka bir ad dene.", { tone: "warn" }); return; }
    await api.put("/settings/weather.location", { value: name });
    await api.put("/settings/weather.lat", { value: hit.latitude });
    await api.put("/settings/weather.lon", { value: hit.longitude });
    invalidateAfter("settings.write");
    toast.push("Hava durumu konumu kaydedildi.", { tone: "ok" });
  }
  const save = useMutation({ mutationFn: ({ key, value }: { key: string; value: unknown }) => api.put(`/settings/${key}`, { value }), onSuccess: () => invalidateAfter("settings.write") });
  const [githubLogin, setGithubLogin] = useState(""); const [githubToken, setGithubToken] = useState(""); const [mediaName, setMediaName] = useState(""); const [mediaUrl, setMediaUrl] = useState("");
  const connectGithub = useMutation({ mutationFn: () => api.post("/auth/github", { login: githubLogin, token: githubToken }), onSuccess: () => { setGithubToken(""); invalidateAfter("settings.write"); } });
  const backup = useMutation({ mutationFn: () => api.post<{ path: string; size: number }>("/backup"), onSuccess: () => invalidateAfter("backup.write") });
  if (!settings) return <div className="p-6 text-body text-muted">Ayarlar yükleniyor…</div>;
  const disabled = settings["modules.disabled"] ?? []; const media = settings["media.links"] ?? [];
  const toggleModule = (id: string) => save.mutate({ key: "modules.disabled", value: disabled.includes(id) ? disabled.filter(x => x !== id) : [...disabled, id] });
  return <PageFrame className="space-y-5"><PageHeader eyebrow="Sistem" title="Ayarlar" /><p className="text-meta text-muted">Ayarlar veritabanında; localStorage yalnızca hızlı açılış önbelleğidir.</p>
    <div className="grid gap-4 xl:grid-cols-2"><Section title="Modüller"><div className="grid grid-cols-2 gap-2">{allModules().filter(m => m.id !== "settings").map(module => <Checkbox key={module.id} disabled={!online} checked={!disabled.includes(module.id)} onChange={() => toggleModule(module.id)} label={module.title} className="rounded border border-subtle px-3 py-2"/>)}</div></Section>
      <Section title="Hava durumu"><p className="mb-2 text-meta text-muted">Konum: <strong className="font-medium text-secondary">{(settings["weather.location"] as string) ?? "ayarlanmadı"}</strong> · Open-Meteo, anahtarsız.</p><form className="flex gap-2" onSubmit={saveWeather}><Input value={weatherLoc ?? (settings["weather.location"] as string) ?? ""} onChange={setWeatherLoc} disabled={!online} placeholder="Şehir adı — örn. İstanbul" className="min-w-0 flex-1"/><Button type="submit" disabled={!online}>kaydet</Button></form></Section>
      <Section title="Bugün sırası"><p className="mb-2 text-meta text-muted">Modül kimliklerini virgülle sırala.</p><Input disabled={!online} value={widgetOrder ?? (settings["today.widget_order"] ?? []).join(", ")} onChange={setWidgetOrder} onBlur={(v) => save.mutate({ key: "today.widget_order", value: v.split(",").map(x => x.trim()).filter(Boolean) })} className="w-full"/></Section>
      <Section title="Pomodoro"><Textarea disabled={!online} value={pomodoroDefaults ?? JSON.stringify(settings["pomodoro.defaults"], null, 2)} onChange={setPomodoroDefaults} onBlur={(v) => { try { save.mutate({ key: "pomodoro.defaults", value: JSON.parse(v) }); } catch { /* düzenlerken bekle */ } }} className="h-28 font-mono"/></Section>
      <Section title="Bildirim eşikleri"><Textarea disabled={!online} value={thresholdsText ?? JSON.stringify(settings["notifications.thresholds"], null, 2)} onChange={setThresholdsText} onBlur={(v) => { try { save.mutate({ key: "notifications.thresholds", value: JSON.parse(v) }); } catch { /* düzenlerken bekle */ } }} className="h-28 font-mono"/></Section>
      <Section title="Kaynak aralıkları"><Textarea value={intervalsText ?? JSON.stringify(settings["sources.intervals"], null, 2)} onChange={setIntervalsText} onBlur={(v) => { try { save.mutate({ key: "sources.intervals", value: JSON.parse(v) }); } catch { /* düzenlerken bekle */ } }} className="h-28 font-mono"/><label className="mt-3 flex items-center justify-between text-meta text-muted" onBlur={() => save.mutate({ key: "rss.retention_days", value: retentionDays ?? Number(settings["rss.retention_days"] ?? 90) })}>RSS retention (gün)<NumberInput value={retentionDays ?? Number(settings["rss.retention_days"] ?? 90)} onChange={setRetentionDays} className="w-24"/></label></Section>
      <Section title="Tema"><ThemePicker /></Section>
      <Section title="Entegrasyonlar"><div className="flex items-center justify-between border-b border-subtle pb-3"><span className="text-body">Google</span>{google?.connected ? <Chip tone="ok">bağlı</Chip> : <Button disabled={!online} onClick={() => { window.location.href = "/api/auth/google/start"; }}>bağla</Button>}</div><div className="mt-3"><div className="mb-2 flex justify-between"><span className="text-body">GitHub</span><Chip tone={github?.connected ? "ok" : "neutral"}>{github?.connected ? github.login ?? "bağlı" : "bağlı değil"}</Chip></div><div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]"><Input value={githubLogin} disabled={!online} onChange={setGithubLogin} placeholder="login"/><Input type="password" value={githubToken} disabled={!online} onChange={setGithubToken} placeholder="fine-grained token"/><Button onClick={() => connectGithub.mutate()} disabled={!online || !githubLogin || !githubToken}>kaydet</Button></div></div></Section>
      <div id="media-links" ref={mediaLinksRef} tabIndex={-1} className="scroll-mt-4 rounded-card outline-none focus:ring-2 focus:ring-accent"><Section title="Medya bağlantıları"><div className="mb-3 flex items-center gap-2"><Input disabled={!online} value={tmdbKey ?? (settings["media.tmdb_key"] as string) ?? ""} onChange={setTmdbKey} placeholder="TMDB API anahtarı (film/dizi araması)" className="min-w-0 flex-1" onBlur={(v) => { if (v.trim()) save.mutate({ key: "media.tmdb_key", value: v.trim() }); }} /><span className="shrink-0 text-meta text-muted">media.tmdb_key</span></div><div className="mb-3 flex items-center gap-2"><Input disabled={!online} value={rawgKey ?? (settings["media.rawg_key"] as string) ?? ""} onChange={setRawgKey} placeholder="RAWG API anahtarı (oyun araması)" className="min-w-0 flex-1" onBlur={(v) => { if (v.trim()) save.mutate({ key: "media.rawg_key", value: v.trim() }); }} /><span className="shrink-0 text-meta text-muted">media.rawg_key</span></div><div className="space-y-2">{media.map((link, index) => <div key={`${link.name}-${index}`} className="flex justify-between text-meta"><a href={link.url} target="_blank" rel="noreferrer" className="text-accent">{link.name} ↗</a><Button variant="danger" disabled={!online} onClick={() => save.mutate({ key: "media.links", value: media.filter((_, i) => i !== index) })}>Sil</Button></div>)}</div><div className="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr_auto]"><Input value={mediaName} disabled={!online} onChange={setMediaName} placeholder="Letterboxd"/><Input value={mediaUrl} disabled={!online} onChange={setMediaUrl} placeholder="https://…"/><Button disabled={!online} onClick={() => { if (mediaName && mediaUrl) { save.mutate({ key: "media.links", value: [...media, { name: mediaName, url: mediaUrl }] }); setMediaName(""); setMediaUrl(""); } }}>Ekle</Button></div></Section></div>
      <Section title="Yedekleme / Export"><div className="flex flex-wrap gap-2">{[["JSON","json"],["Markdown","markdown"],["Bookmarks","bookmarks"],["OPML","opml"],["ICS","ics"]].map(([label,path]) => <a key={path} href={`/api/export/${path}`} download className="rounded border border-strong px-2 py-1 text-meta text-secondary">{label}</a>)}<a href="/api/export/csv?module=expense" download className="rounded border border-strong px-2 py-1 text-meta">Expense CSV</a><Button onClick={() => restoreRef.current?.click()} disabled={!online || restoreBackup.isPending}>{restoreBackup.isPending ? "yükleniyor…" : "geri yükle"}</Button><Button variant="primary" onClick={() => backup.mutate()} disabled={!online || backup.isPending}>şimdi yedekle</Button><FileInput ref={restoreRef} accept=".gz,.json,application/gzip,application/json" onChange={(e) => { const file = e.target.files?.[0]; if (file) pickRestore(file); e.target.value = ""; }} /></div>{backup.data && <p className="mt-2 text-meta text-ok">{backup.data.path} · {Math.round(backup.data.size/1024)} KB</p>}
        {backupStatus && (
          <div className="mt-3 space-y-0.5 border-t border-subtle pt-3 text-meta text-muted">
            <p>Son yedek: {backupStatus.last_backup ? `${backupStatus.last_backup.file} · ${Math.round(backupStatus.last_backup.size / 1024)} KB · ${relativeTime(backupStatus.last_backup.at)}` : "—"}</p>
            <p>Drive hedefi: {backupStatus.drive_folder_id ? backupStatus.drive_folder_id : "ayarlanmadı"}</p>
            <p>Son Drive yüklemesi: {backupStatus.last_drive_upload ? `${backupStatus.last_drive_upload.file} · ${relativeTime(backupStatus.last_drive_upload.at)}` : backupStatus.last_drive_error ? "başarısız" : "—"}</p>
            {backupStatus.last_drive_error && (
              <p className="text-danger">Yükleme hatası: {backupStatus.last_drive_error.message}</p>
            )}
            <p>Detaylı durum: Sağlık paneli → "Yedekleme" widget'ı.</p>
          </div>
        )}</Section></div>
    <SettingsSourceHealth sources={sources} /></PageFrame>;
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
            theme === option.id
              ? "border-accent bg-accent-surface"
              : "border-subtle bg-surface hover:bg-surface-hover"
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
