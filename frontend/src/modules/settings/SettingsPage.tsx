import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { allModules } from "@/core/registry";
import type { AppSettings, SourceHealth } from "@/core/types";
import { Badge, Button, Panel, useTheme } from "@/core/ui";
import type { Theme } from "@/core/ui";
import { useInvalidate } from "@/lib/hooks";

type IntegrationStatus = { connected: boolean; login?: string | null };
export function SettingsPage() {
  const invalidate = useInvalidate(); const [githubLogin, setGithubLogin] = useState(""); const [githubToken, setGithubToken] = useState(""); const [mediaName, setMediaName] = useState(""); const [mediaUrl, setMediaUrl] = useState("");
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: () => api.get<AppSettings>("/settings") });
  const { data: sources = [] } = useQuery({ queryKey: ["sources", "health"], queryFn: () => api.get<SourceHealth[]>("/sources/health") });
  const { data: google } = useQuery({ queryKey: ["google-status"], queryFn: () => api.get<IntegrationStatus>("/auth/google/status") });
  const { data: github } = useQuery({ queryKey: ["github-status"], queryFn: () => api.get<IntegrationStatus>("/auth/github/status") });
  const save = useMutation({ mutationFn: ({ key, value }: { key: string; value: unknown }) => api.put(`/settings/${key}`, { value }), onSuccess: () => invalidate("settings") });
  const connectGithub = useMutation({ mutationFn: () => api.post("/auth/github", { login: githubLogin, token: githubToken }), onSuccess: () => { setGithubToken(""); invalidate("github-status"); } });
  const backup = useMutation({ mutationFn: () => api.post<{ path: string; size: number }>("/backup") });
  if (!settings) return <div className="p-6 text-body text-muted">Ayarlar yükleniyor…</div>;
  const disabled = settings["modules.disabled"] ?? []; const media = settings["media.links"] ?? [];
  const toggleModule = (id: string) => save.mutate({ key: "modules.disabled", value: disabled.includes(id) ? disabled.filter(x => x !== id) : [...disabled, id] });
  return <div className="space-y-4 p-6"><header><p className="text-meta text-muted">Ayarlar DB’de; localStorage yalnızca hızlı açılış cache’i.</p></header>
    <div className="grid gap-4 xl:grid-cols-2"><Panel title="Modüller"><div className="grid grid-cols-2 gap-2">{allModules().filter(m => m.id !== "settings").map(module => <label key={module.id} className="flex items-center gap-2 rounded border border-subtle px-3 py-2 text-meta"><input type="checkbox" checked={!disabled.includes(module.id)} onChange={() => toggleModule(module.id)}/>{module.title}</label>)}</div></Panel>
      <Panel title="Today sırası"><p className="mb-2 text-meta text-muted">Modül id’lerini virgülle sırala.</p><input defaultValue={(settings["today.widget_order"] ?? []).join(", ")} onBlur={e => save.mutate({ key: "today.widget_order", value: e.target.value.split(",").map(x => x.trim()).filter(Boolean) })} className="w-full rounded border border-subtle bg-canvas px-3 py-2 text-body"/></Panel>
      <Panel title="Pomodoro"><textarea defaultValue={JSON.stringify(settings["pomodoro.defaults"], null, 2)} onBlur={e => { try { save.mutate({ key: "pomodoro.defaults", value: JSON.parse(e.target.value) }); } catch { /* düzenlerken bekle */ } }} className="h-28 w-full rounded border border-subtle bg-canvas p-3 font-mono text-meta"/></Panel>
      <Panel title="Bildirim eşikleri"><textarea defaultValue={JSON.stringify(settings["notifications.thresholds"], null, 2)} onBlur={e => { try { save.mutate({ key: "notifications.thresholds", value: JSON.parse(e.target.value) }); } catch { /* düzenlerken bekle */ } }} className="h-28 w-full rounded border border-subtle bg-canvas p-3 font-mono text-meta"/></Panel>
      <Panel title="Kaynak aralıkları"><textarea defaultValue={JSON.stringify(settings["sources.intervals"], null, 2)} onBlur={e => { try { save.mutate({ key: "sources.intervals", value: JSON.parse(e.target.value) }); } catch { /* düzenlerken bekle */ } }} className="h-28 w-full rounded border border-subtle bg-canvas p-3 font-mono text-meta"/><label className="mt-3 flex items-center justify-between text-meta text-muted">RSS retention (gün)<input type="number" defaultValue={Number(settings["rss.retention_days"] ?? 90)} onBlur={e => save.mutate({ key: "rss.retention_days", value: Number(e.target.value) })} className="w-24 rounded border border-subtle bg-canvas px-2 py-1"/></label></Panel>
      <Panel title="Tema"><ThemePicker /></Panel>
      <Panel title="Entegrasyonlar"><div className="flex items-center justify-between border-b border-subtle pb-3"><span className="text-body">Google</span>{google?.connected ? <Badge tone="ok">bağlı</Badge> : <Button onClick={() => { window.location.href = "/api/auth/google/start"; }}>bağla</Button>}</div><div className="mt-3"><div className="mb-2 flex justify-between"><span className="text-body">GitHub</span><Badge tone={github?.connected ? "ok" : "neutral"}>{github?.connected ? github.login ?? "bağlı" : "bağlı değil"}</Badge></div><div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]"><input value={githubLogin} onChange={e => setGithubLogin(e.target.value)} placeholder="login" className="rounded border border-subtle bg-canvas px-2 py-1 text-meta"/><input type="password" value={githubToken} onChange={e => setGithubToken(e.target.value)} placeholder="fine-grained token" className="rounded border border-subtle bg-canvas px-2 py-1 text-meta"/><Button onClick={() => connectGithub.mutate()} disabled={!githubLogin || !githubToken}>kaydet</Button></div></div></Panel>
      <Panel title="Media bağlantıları"><div className="space-y-2">{media.map((link, index) => <div key={`${link.name}-${index}`} className="flex justify-between text-meta"><a href={link.url} target="_blank" className="text-accent">{link.name} ↗</a><Button variant="danger" onClick={() => save.mutate({ key: "media.links", value: media.filter((_, i) => i !== index) })}>sil</Button></div>)}</div><div className="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr_auto]"><input value={mediaName} onChange={e => setMediaName(e.target.value)} placeholder="Letterboxd" className="rounded border border-subtle bg-canvas px-2 py-1 text-meta"/><input value={mediaUrl} onChange={e => setMediaUrl(e.target.value)} placeholder="https://…" className="rounded border border-subtle bg-canvas px-2 py-1 text-meta"/><Button onClick={() => { if (mediaName && mediaUrl) { save.mutate({ key: "media.links", value: [...media, { name: mediaName, url: mediaUrl }] }); setMediaName(""); setMediaUrl(""); } }}>ekle</Button></div></Panel>
      <Panel title="Yedekleme / Export"><div className="flex flex-wrap gap-2">{[["JSON","json"],["Markdown","markdown"],["Bookmarks","bookmarks"],["OPML","opml"],["ICS","ics"]].map(([label,path]) => <a key={path} href={`/api/export/${path}`} download className="rounded border border-strong px-2 py-1 text-meta text-secondary">{label}</a>)}<a href="/api/export/csv?module=expense" download className="rounded border border-strong px-2 py-1 text-meta">Expense CSV</a><Button variant="primary" onClick={() => backup.mutate()} disabled={backup.isPending}>şimdi yedekle</Button></div>{backup.data && <p className="mt-2 text-meta text-ok">{backup.data.path} · {Math.round(backup.data.size/1024)} KB</p>}</Panel></div>
    <Panel title="Kaynak sağlığı"><div className="max-h-80 overflow-auto"><table className="w-full text-left text-meta"><thead className="text-muted"><tr><th className="p-2">Kaynak</th><th>Durum</th><th>Sonuç</th><th>Zaman</th></tr></thead><tbody>{sources.map(source => <tr key={source.source} className="border-t border-subtle"><td className="p-2">{source.source}</td><td><Badge tone={source.status === "ok" ? "ok" : source.status === "error" ? "warn" : "neutral"}>{source.status}</Badge></td><td>{source.items_found}</td><td>{new Date(source.started_at).toLocaleString("tr-TR")}</td></tr>)}</tbody></table></div></Panel></div>;
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
