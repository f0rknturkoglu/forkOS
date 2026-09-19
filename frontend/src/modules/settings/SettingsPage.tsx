import { invalidateAfter } from "@/core/invalidation";
import { useBackupStatus, useSourceHealth } from "@/core/runtimeQueries";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BellRing, Blocks, Briefcase, DatabaseBackup, LayoutGrid, Plug, SlidersHorizontal } from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { api } from "@/core/api";
import type { AppSettings, BackupStatus, SourceHealth } from "@/core/types";
import type { LucideIcon } from "lucide-react";
import { NumberInput, PageFrame, Section, Select, useToast } from "@/core/ui";
import {
  Workspace,
  WorkspacePaneHeader,
  WorkspaceRailButton,
  WorkspaceRailContent,
  WorkspaceRailGroup,
  WorkspaceScrollArea,
} from "@/core/workspace/Workspace";
import { TodayWidgetsSection } from "./TodayWidgetsSection";
import { NotificationsSection } from "./NotificationsSection";
import { CareerProfileSection, DangerZoneSection, SystemDiagnosticsSection, TodayFlowSection } from "./SettingsPanels";
import type { CareerProfile } from "./SettingsPanels";
import { useOnline } from "@/lib/hooks";
import {
  BackupSection,
  IntegrationsSection,
  MediaProvidersSection,
  ModulesSection,
  SettingsSourceHealth,
  ThemePicker,
  WeatherSection,
  type IntegrationStatus,
} from "./SettingsSections";

/**
 * Sekmeler URL'de yasar (`#/settings?tab=modules`): yenileyince kaybolmaz,
 * baglanti paylasilabilir. Eski `?section=media-links` derin baglantisi da
 * karsilanir -- Entegrasyonlar sekmesini acip medya panelini odaklar.
 */
const TABS: { id: string; label: string; icon: LucideIcon }[] = [
  { id: "general", label: "Genel & Görünüm", icon: SlidersHorizontal },
  { id: "modules", label: "Modüller", icon: Blocks },
  { id: "today", label: "Bugün & Akış", icon: LayoutGrid },
  { id: "notifications", label: "Bildirimler & Çevre", icon: BellRing },
  { id: "career", label: "Kariyer profili", icon: Briefcase },
  { id: "integrations", label: "Entegrasyonlar", icon: Plug },
  { id: "backup", label: "Yedekleme & Sistem", icon: DatabaseBackup },
];

const TAB_IDS = new Set(TABS.map((tab) => tab.id));

/** Ayarlar her sekmede ayni govde genisligini kullanir; uzun satirlar okunmaz. */
function Pane({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto max-w-3xl space-y-4">{children}</div>;
}

type AutomationState = {
  profile: string;
  profiles: string[];
  domains: Record<string, { enabled: boolean; interval_minutes: number }>;
};

const RSS_INTERVALS = [
  { minutes: 30, label: "30 dakikada bir" },
  { minutes: 60, label: "Saatte bir" },
  { minutes: 120, label: "2 saatte bir" },
  { minutes: 360, label: "6 saatte bir" },
  { minutes: 0, label: "Yalnız manuel" },
] as const;

export function SettingsPage() {
  const route = useHashRoute();
  const toast = useToast();
  const online = useOnline();
  const mediaLinksRef = useRef<HTMLDivElement>(null);
  const requestedSection = route.params.get("section");
  const requestedTab = route.params.get("tab");
  const tab =
    requestedTab && TAB_IDS.has(requestedTab)
      ? requestedTab
      : requestedSection === "media-links"
        ? "integrations"
        : "general";

  const [weatherLoc, setWeatherLoc] = useState<string | null>(null);
  const [retentionDays, setRetentionDays] = useState<number | null>(null);
  const [upcomingDays, setUpcomingDays] = useState<number | null>(null);
  const [syncIntervalHours, setSyncIntervalHours] = useState<number | null>(null);
  const [driveFolder, setDriveFolder] = useState<string | null>(null);
  const [keyDrafts, setKeyDrafts] = useState<Record<string, string>>({});
  const [githubLogin, setGithubLogin] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [mediaName, setMediaName] = useState("");
  const [mediaUrl, setMediaUrl] = useState("");

  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<AppSettings>("/settings"),
  });
  const { data: sources = [] } = useSourceHealth();
  const { data: google } = useQuery({
    queryKey: ["google-status"],
    queryFn: () => api.get<IntegrationStatus>("/auth/google/status"),
  });
  const { data: github } = useQuery({
    queryKey: ["github-status"],
    queryFn: () => api.get<IntegrationStatus>("/auth/github/status"),
  });
  const { data: backupStatus } = useBackupStatus();

  /* Derin baglanti: medya paneli odaklanir ve orta hizaya kaydirilir. */
  const [focusedSection, setFocusedSection] = useState<string | null>(null);
  useEffect(() => {
    if (requestedSection !== "media-links") {
      setFocusedSection(null);
      return;
    }
    if (tab !== "integrations" || !settings || focusedSection === requestedSection) return;
    mediaLinksRef.current?.scrollIntoView({ block: "center" });
    mediaLinksRef.current?.focus();
    setFocusedSection(requestedSection);
  }, [tab, requestedSection, settings, focusedSection]);

  // Otomasyon durumu/profili: hook'lar ERKEN RETURN'DEN ONCE kurulur, aksi
  // halde ilk render'da sayilari tutmaz ("more hooks than previous render").
  const { data: automation } = useQuery({
    queryKey: ["automation"],
    queryFn: () => api.get<AutomationState>("/system/automation"),
  });
  const setProfile = useMutation({
    mutationFn: (profile: string) => api.post<AutomationState>("/system/automation/profile", { profile }),
    onSuccess: (state) => {
      // Profil birden cok ayari birlikte yazar; `settings.write` haritasi
      // hem settings hem automation sorgusunu tazeler (kural 14).
      invalidateAfter("settings.write");
      toast.push(state.profile === "manual" ? "Arka plan güncellemesi kapatıldı." : "Çalışma profili güncellendi.", {
        tone: "ok",
      });
    },
    onError: (error) => toast.push(`Profil uygulanamadı: ${error.message}`, { tone: "danger" }),
  });

  const save = useMutation({
    mutationFn: ({ key, value }: { key: string; value: unknown }) => api.put(`/settings/${key}`, { value }),
    onSuccess: () => {
      invalidateAfter("settings.write");
      toast.push("Kaydedildi.", { tone: "ok" });
    },
    onError: (error) => toast.push(`Kaydedilemedi: ${error.message}`, { tone: "danger" }),
  });
  const connectGithub = useMutation({
    mutationFn: () => api.post("/auth/github", { login: githubLogin, token: githubToken }),
    onSuccess: () => {
      setGithubToken("");
      invalidateAfter("settings.write");
      toast.push("GitHub bağlandı.", { tone: "ok" });
    },
    onError: (error) => toast.push(`GitHub bağlanamadı: ${error.message}`, { tone: "danger" }),
  });
  const disconnect = useMutation({
    mutationFn: (provider: "github" | "google") =>
      provider === "github" ? api.del("/auth/github") : api.del("/auth/google"),
    onSuccess: (_result, provider) => {
      invalidateAfter("settings.write");
      toast.push(provider === "github" ? "GitHub bağlantısı kesildi." : "Google bağlantısı kesildi.", {
        tone: "neutral",
      });
    },
    onError: (error) => toast.push(`Bağlantı kesilemedi: ${error.message}`, { tone: "danger" }),
  });
  const backup = useMutation({
    mutationFn: () => api.post<{ path: string; size: number }>("/backup"),
    onSuccess: () => invalidateAfter("backup.write"),
  });
  const reset = useMutation({
    mutationFn: () => api.post<{ removed: number }>("/settings/reset"),
    onSuccess: (result) => {
      invalidateAfter("settings.write");
      setKeyDrafts({});
      setWeatherLoc(null);
      setRetentionDays(null);
      setUpcomingDays(null);
      setSyncIntervalHours(null);
      setDriveFolder(null);
      toast.push(`Ayarlar sıfırlandı (${result.removed} kayıt silindi).`, { tone: "ok" });
    },
    onError: (error) => toast.push(`Sıfırlanamadı: ${error.message}`, { tone: "danger" }),
  });

  async function saveWeather(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = (weatherLoc ?? (settings?.["weather.location"] as string | undefined) ?? "").trim();
    if (!name) return;
    try {
      const hit = await api.get<{ name: string; latitude: number; longitude: number }>(
        `/weather/geocode?query=${encodeURIComponent(name)}`,
      );
      await api.put("/settings/weather.location", { value: name });
      await api.put("/settings/weather.lat", { value: hit.latitude });
      await api.put("/settings/weather.lon", { value: hit.longitude });
      invalidateAfter("settings.write");
      toast.push(`Konum kaydedildi: ${hit.name}`, { tone: "ok" });
    } catch {
      toast.push("Konum bulunamadı — başka bir ad dene.", { tone: "warn" });
    }
  }

  if (!settings) return <div className="p-6 text-body text-muted">Ayarlar yükleniyor…</div>;

  const disabled = settings["modules.disabled"] ?? [];
  const media = settings["media.links"] ?? [];
  const subreddits = Array.isArray(settings["news.subreddits"]) ? (settings["news.subreddits"] as string[]) : [];
  const career = (settings["opportunity.career_profile"] ?? {
    current_location: "",
    authorized_countries: [],
    willing_to_relocate: false,
  }) as CareerProfile;
  const write = (key: string, value: unknown) => save.mutate({ key, value });
  const toggleModule = (id: string) =>
    write("modules.disabled", disabled.includes(id) ? disabled.filter((x) => x !== id) : [...disabled, id]);
  const addLink = () => {
    if (!mediaName || !mediaUrl) return;
    write("media.links", [...media, { name: mediaName, url: mediaUrl }]);
    setMediaName("");
    setMediaUrl("");
  };
  const retention = retentionDays ?? Number(settings["rss.retention_days"] ?? 90);
  const intervalMinutes = Number(settings["rss.interval_minutes"] ?? 30);
  const upcoming = upcomingDays ?? Number(settings["media.upcoming_days"] ?? 30);
  const syncInterval = syncIntervalHours ?? Number(settings["media.sync_interval_hours"] ?? 24);
  const go = (id: string) => navigate(`/settings?tab=${id}`);

  const rail = (
    <WorkspaceRailContent className="max-h-72 lg:max-h-workspace-body">
      <WorkspaceRailGroup label="Ayarlar">
        {TABS.map((item) => {
          const Icon = item.icon;
          return (
            <WorkspaceRailButton
              key={item.id}
              label={item.label}
              icon={<Icon size={13} />}
              active={tab === item.id}
              onClick={() => go(item.id)}
            />
          );
        })}
      </WorkspaceRailGroup>
    </WorkspaceRailContent>
  );

  return (
    <PageFrame>
      <Workspace rail={rail}>
        <WorkspacePaneHeader eyebrow="Sistem" title="Ayarlar" hint={TABS.find((item) => item.id === tab)?.label} />
        <WorkspaceScrollArea className="p-3">
          {tab === "general" && (
            <Pane>
              <Section title="Tema">
                <ThemePicker />
              </Section>
              <SystemDiagnosticsSection />
              <Section title="RSS güncelleme">
                <div className="flex items-center justify-between gap-3 text-meta text-secondary">
                  <span>
                    Arka planda ne sıklıkta yeni yazı çekilsin?
                    <span className="ml-1 text-muted">· rss.interval_minutes</span>
                  </span>
                  <Select
                    value={String(intervalMinutes)}
                    onChange={(value) => write("rss.interval_minutes", Number(value))}
                    ariaLabel="RSS güncelleme sıklığı"
                    className="w-40"
                  >
                    {RSS_INTERVALS.map((option) => (
                      <option key={option.minutes} value={option.minutes}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </div>
              </Section>
              <Section title="RSS saklama">
                <div className="flex items-center justify-between gap-3 text-meta text-secondary">
                  <span>
                    Okunmamış ve kaydedilmemiş eski yazılar bu süreden sonra silinir.
                    <span className="ml-1 text-muted">· rss.retention_days</span>
                  </span>
                  <div
                    onBlur={() => {
                      const current = Number(settings["rss.retention_days"] ?? 90);
                      if (retention !== current) write("rss.retention_days", retention);
                    }}
                  >
                    <NumberInput
                      value={retention}
                      min={1}
                      max={3650}
                      ariaLabel="RSS saklama süresi (gün)"
                      onChange={setRetentionDays}
                      className="w-24"
                    />
                  </div>
                </div>
              </Section>
            </Pane>
          )}

          {tab === "modules" && (
            <Pane>
              <ModulesSection
                online={online}
                disabledModules={disabled}
                onToggle={toggleModule}
                automation={automation?.domains ?? {}}
                onToggleAutomation={(domain, enabled) => write(`automation.${domain}.enabled`, enabled)}
                profile={automation?.profile ?? "balanced"}
                profiles={automation?.profiles ?? []}
                onProfile={(profile) => setProfile.mutate(profile)}
              />
            </Pane>
          )}

          {tab === "today" && (
            <Pane>
              <TodayFlowSection
                online={online}
                autoSuggestions={settings["today.auto_suggestions"] !== false}
                subreddits={subreddits}
                onSave={write}
              />
              <TodayWidgetsSection
                online={online}
                onPersist={(orderIds, hiddenIds) => {
                  write("today.widget_order", orderIds);
                  write("today.widget_hidden", hiddenIds);
                }}
              />
            </Pane>
          )}

          {tab === "notifications" && (
            <Pane>
              <NotificationsSection />
              <WeatherSection
                online={online}
                weatherLoc={weatherLoc}
                onWeatherLoc={setWeatherLoc}
                location={settings["weather.location"] as string | undefined}
                onSubmit={saveWeather}
              />
            </Pane>
          )}

          {tab === "career" && (
            <Pane>
              <CareerProfileSection online={online} profile={career} onSave={write} />
            </Pane>
          )}

          {tab === "integrations" && (
            <Pane>
              <IntegrationsSection
                online={online}
                google={google}
                github={github}
                githubLogin={githubLogin}
                onGithubLogin={setGithubLogin}
                githubToken={githubToken}
                onGithubToken={setGithubToken}
                onConnectGithub={() => connectGithub.mutate()}
                onDisconnectGithub={() => disconnect.mutate("github")}
                onDisconnectGoogle={() => disconnect.mutate("google")}
                busy={disconnect.isPending}
              />
              <MediaProvidersSection
                online={online}
                keys={{
                  "media.tmdb_key": String(settings["media.tmdb_key"] ?? ""),
                  "media.igdb_client_id": String(settings["media.igdb_client_id"] ?? ""),
                  "media.igdb_client_secret": String(settings["media.igdb_client_secret"] ?? ""),
                  "media.google_books_key": String(settings["media.google_books_key"] ?? ""),
                  ...keyDrafts,
                }}
                onKey={(key, value) => setKeyDrafts((current) => ({ ...current, [key]: value }))}
                onSave={(key, value) => {
                  setKeyDrafts((current) => {
                    const next = { ...current };
                    delete next[key];
                    return next;
                  });
                  write(key, value);
                }}
                media={media}
                onRemoveLink={(index) =>
                  write(
                    "media.links",
                    media.filter((_, i) => i !== index),
                  )
                }
                mediaName={mediaName}
                onMediaName={setMediaName}
                mediaUrl={mediaUrl}
                onMediaUrl={setMediaUrl}
                onAddLink={addLink}
                upcomingDays={upcoming}
                onUpcomingDays={setUpcomingDays}
                onSaveUpcomingDays={() => {
                  if (upcoming !== Number(settings["media.upcoming_days"] ?? 30))
                    write("media.upcoming_days", upcoming);
                }}
                syncIntervalHours={syncInterval}
                onSyncIntervalHours={setSyncIntervalHours}
                onSaveSyncIntervalHours={() => {
                  if (syncInterval !== Number(settings["media.sync_interval_hours"] ?? 24))
                    write("media.sync_interval_hours", syncInterval);
                }}
                innerRef={mediaLinksRef}
              />
            </Pane>
          )}

          {tab === "backup" && (
            <Pane>
              <BackupSection
                online={online}
                backupPending={backup.isPending}
                onBackup={() => backup.mutate()}
                backupData={backup.data}
                backupStatus={backupStatus}
                driveFolder={driveFolder ?? backupStatus?.drive_folder_id ?? ""}
                onDriveFolder={setDriveFolder}
                onSaveDriveFolder={(value) => write("backup.drive_folder_id", value)}
              />
              <SettingsSourceHealth sources={sources} />
              <DangerZoneSection onReset={() => reset.mutate()} busy={reset.isPending} />
            </Pane>
          )}
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
