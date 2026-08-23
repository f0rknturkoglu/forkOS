import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { allModules } from "@/core/registry";
import type { AppSettings, BackupStatus, SourceHealth } from "@/core/types";
import { Badge, Button, PageFrame, PageHeader, Section as Panel, relativeTime, useTheme, useToast } from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import type { Theme } from "@/core/ui";
import { useInvalidate, useOnline } from "@/lib/hooks";

type IntegrationStatus = { connected: boolean; login?: string | null };
export function SettingsPage() {
  const toast = useToast();
  const online = useOnline();
  const restoreRef = useRef<HTMLInputElement>(null);
  const restoreBackup = useMutation({
    mutationFn: (file: File) => api.upload<{ restored: number }>("/backup/restore", file),
    onSuccess: (result) => {
      invalidate("backup-status", "activity");
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
  const invalidate = useInvalidate(); const [githubLogin, setGithubLogin] = useState(""); const [githubToken, setGithubToken] = useState(""); const [mediaName, setMediaName] = useState(""); const [mediaUrl, setMediaUrl] = useState("");
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: () => api.get<AppSettings>("/settings") });
  const { data: sources = [] } = useQuery({ queryKey: ["sources", "health"], queryFn: () => api.get<SourceHealth[]>("/sources/health") });
  const { data: google } = useQuery({ queryKey: ["google-status"], queryFn: () => api.get<IntegrationStatus>("/auth/google/status") });
  const { data: github } = useQuery({ queryKey: ["github-status"], queryFn: () => api.get<IntegrationStatus>("/auth/github/status") });
  const { data: backupStatus } = useQuery({ queryKey: ["backup-status"], queryFn: () => api.get<BackupStatus>("/backup/status") });
  async function saveWeather(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = (new FormData(event.currentTarget).get("loc") as string ?? "").trim();
    if (!name) return;
    const geo = await fetch(
      "https://geocoding-api.open-meteo.com/v1/search?name=" + encodeURIComponent(name) + "&count=1&language=tr",
    ).then((r) => r.json()).catch(() => null);
    const hit = (geo as { results?: { latitude: number; longitude: number }[] } | null)?.results?.[0];
    if (!hit) { toast.push("Konum bulunamadı — başka bir ad dene.", { tone: "warn" }); return; }
    await api.put("/settings/weather.location", { value: name });
    await api.put("/settings/weather.lat", { value: hit.latitude });
    await api.put("/settings/weather.lon", { value: hit.longitude });
    invalidate("settings");
    toast.push("Hava durumu konumu kaydedildi.", { tone: "ok" });
  }
  const save = useMutation({ mutationFn: ({ key, value }: { key: string; value: unknown }) => api.put(`/settings/${key}`, { value }), onSuccess: () => invalidate("settings") });
  const connectGithub = useMutation({ mutationFn: () => api.post("/auth/github", { login: githubLogin, token: githubToken }), onSuccess: () => { setGithubToken(""); invalidate("github-status"); } });
  const backup = useMutation({ mutationFn: () => api.post<{ path: string; size: number }>("/backup"), onSuccess: () => invalidate("backup-status", "activity") });
  if (!settings) return <div className="p-6 text-body text-muted">Ayarlar yükleniyor…</div>;
  const disabled = settings["modules.disabled"] ?? []; const media = settings["media.links"] ?? [];
  const toggleModule = (id: string) => save.mutate({ key: "modules.disabled", value: disabled.includes(id) ? disabled.filter(x => x !== id) : [...disabled, id] });
  return <PageFrame className="space-y-5"><PageHeader eyebrow="Sistem" title="Ayarlar" /><p className="text-meta text-muted">Ayarlar veritabanında; localStorage yalnızca hızlı açılış önbelleğidir.</p>
    <div className="grid gap-4 xl:grid-cols-2"><Panel title="Modüller"><div className="grid grid-cols-2 gap-2">{allModules().filter(m => m.id !== "settings").map(module => <label key={module.id} className="flex items-center gap-2 rounded border border-subtle px-3 py-2 text-meta"><input type="checkbox" disabled={!online} checked={!disabled.includes(module.id)} onChange={() => toggleModule(module.id)}/>{module.title}</label>)}</div></Panel>
      <Panel title="Hava durumu"><p className="mb-2 text-meta text-muted">Konum: <strong className="font-medium text-secondary">{(settings["weather.location"] as string) ?? "ayarlanmadı"}</strong> · Open-Meteo, anahtarsız.</p><form className="flex gap-2" onSubmit={saveWeather}><input name="loc" disabled={!online} defaultValue={(settings["weather.location"] as string) ?? ""} placeholder="Şehir adı — örn. İstanbul" className="min-w-0 flex-1 rounded border border-subtle bg-canvas px-3 py-2 text-body"/><Button type="submit" disabled={!online}>kaydet</Button></form></Panel>
      <Panel title="Bugün sırası"><p className="mb-2 text-meta text-muted">Modül kimliklerini virgülle sırala.</p><input disabled={!online} defaultValue={(settings["today.widget_order"] ?? []).join(", ")} onBlur={e => save.mutate({ key: "today.widget_order", value: e.target.value.split(",").map(x => x.trim()).filter(Boolean) })} className="w-full rounded border border-subtle bg-canvas px-3 py-2 text-body"/></Panel>
      <Panel title="Pomodoro"><textarea disabled={!online} defaultValue={JSON.stringify(settings["pomodoro.defaults"], null, 2)} onBlur={e => { try { save.mutate({ key: "pomodoro.defaults", value: JSON.parse(e.target.value) }); } catch { /* düzenlerken bekle */ } }} className="h-28 w-full rounded border border-subtle bg-canvas p-3 font-mono text-meta"/></Panel>
      <Panel title="Bildirim eşikleri"><textarea disabled={!online} defaultValue={JSON.stringify(settings["notifications.thresholds"], null, 2)} onBlur={e => { try { save.mutate({ key: "notifications.thresholds", value: JSON.parse(e.target.value) }); } catch { /* düzenlerken bekle */ } }} className="h-28 w-full rounded border border-subtle bg-canvas p-3 font-mono text-meta"/></Panel>
      <Panel title="Kaynak aralıkları"><textarea defaultValue={JSON.stringify(settings["sources.intervals"], null, 2)} onBlur={e => { try { save.mutate({ key: "sources.intervals", value: JSON.parse(e.target.value) }); } catch { /* düzenlerken bekle */ } }} className="h-28 w-full rounded border border-subtle bg-canvas p-3 font-mono text-meta"/><label className="mt-3 flex items-center justify-between text-meta text-muted">RSS retention (gün)<input type="number" defaultValue={Number(settings["rss.retention_days"] ?? 90)} onBlur={e => save.mutate({ key: "rss.retention_days", value: Number(e.target.value) })} className="w-24 rounded border border-subtle bg-canvas px-2 py-1"/></label></Panel>
      <Panel title="Tema"><ThemePicker /></Panel>
      <Panel title="Entegrasyonlar"><div className="flex items-center justify-between border-b border-subtle pb-3"><span className="text-body">Google</span>{google?.connected ? <Badge tone="ok">bağlı</Badge> : <Button disabled={!online} onClick={() => { window.location.href = "/api/auth/google/start"; }}>bağla</Button>}</div><div className="mt-3"><div className="mb-2 flex justify-between"><span className="text-body">GitHub</span><Badge tone={github?.connected ? "ok" : "neutral"}>{github?.connected ? github.login ?? "bağlı" : "bağlı değil"}</Badge></div><div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]"><input value={githubLogin} disabled={!online} onChange={e => setGithubLogin(e.target.value)} placeholder="login" className="rounded border border-subtle bg-canvas px-2 py-1 text-meta"/><input type="password" value={githubToken} disabled={!online} onChange={e => setGithubToken(e.target.value)} placeholder="fine-grained token" className="rounded border border-subtle bg-canvas px-2 py-1 text-meta"/><Button onClick={() => connectGithub.mutate()} disabled={!online || !githubLogin || !githubToken}>kaydet</Button></div></div></Panel>
      <Panel title="Medya bağlantıları"><div className="mb-3 flex items-center gap-2"><input disabled={!online} defaultValue={(settings["media.tmdb_key"] as string) ?? ""} placeholder="TMDB API anahtarı (film/dizi araması)" className="min-w-0 flex-1 rounded border border-subtle bg-canvas px-2 py-1 text-meta" onBlur={(e) => { if (e.target.value.trim()) save.mutate({ key: "media.tmdb_key", value: e.target.value.trim() }); }} /><span className="shrink-0 text-meta text-muted">media.tmdb_key</span></div><div className="space-y-2">{media.map((link, index) => <div key={`${link.name}-${index}`} className="flex justify-between text-meta"><a href={link.url} target="_blank" rel="noreferrer" className="text-accent">{link.name} ↗</a><Button variant="danger" disabled={!online} onClick={() => save.mutate({ key: "media.links", value: media.filter((_, i) => i !== index) })}>Sil</Button></div>)}</div><div className="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr_auto]"><input value={mediaName} disabled={!online} onChange={e => setMediaName(e.target.value)} placeholder="Letterboxd" className="rounded border border-subtle bg-canvas px-2 py-1 text-meta"/><input value={mediaUrl} disabled={!online} onChange={e => setMediaUrl(e.target.value)} placeholder="https://…" className="rounded border border-subtle bg-canvas px-2 py-1 text-meta"/><Button disabled={!online} onClick={() => { if (mediaName && mediaUrl) { save.mutate({ key: "media.links", value: [...media, { name: mediaName, url: mediaUrl }] }); setMediaName(""); setMediaUrl(""); } }}>Ekle</Button></div></Panel>
      <Panel title="Yedekleme / Export"><div className="flex flex-wrap gap-2">{[["JSON","json"],["Markdown","markdown"],["Bookmarks","bookmarks"],["OPML","opml"],["ICS","ics"]].map(([label,path]) => <a key={path} href={`/api/export/${path}`} download className="rounded border border-strong px-2 py-1 text-meta text-secondary">{label}</a>)}<a href="/api/export/csv?module=expense" download className="rounded border border-strong px-2 py-1 text-meta">Expense CSV</a><Button onClick={() => restoreRef.current?.click()} disabled={!online || restoreBackup.isPending}>{restoreBackup.isPending ? "yükleniyor…" : "geri yükle"}</Button><Button variant="primary" onClick={() => backup.mutate()} disabled={!online || backup.isPending}>şimdi yedekle</Button><input ref={restoreRef} type="file" accept=".gz,.json,application/gzip,application/json" className="hidden" onChange={(e) => { const file = e.target.files?.[0]; if (file) pickRestore(file); e.target.value = ""; }} /></div>{backup.data && <p className="mt-2 text-meta text-ok">{backup.data.path} · {Math.round(backup.data.size/1024)} KB</p>}
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
        )}</Panel></div>
    <Panel title="Kaynak sağlığı"><div className="max-h-80 overflow-auto border-y border-subtle"><table className="w-full text-left text-meta"><thead className="text-muted"><tr><th className="p-2">Kaynak</th><th>Durum</th><th>Sonuç</th><th>Zaman</th></tr></thead><tbody>{sources.map(source => <tr key={source.source} className="border-t border-subtle"><td className="p-2">{source.source}</td><td><Badge tone={source.status === "ok" ? "ok" : source.status === "error" ? "warn" : "neutral"}>{source.status}</Badge></td><td>{source.items_found}</td><td>{new Date(source.started_at).toLocaleString("tr-TR")}</td></tr>)}</tbody></table></div></Panel></PageFrame>;
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
