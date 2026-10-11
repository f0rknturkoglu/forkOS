import { invalidateAfter } from "@/core/invalidation";
import { useBackupStatus } from "@/core/runtimeQueries";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  BellRing,
  Blocks,
  BrainCircuit,
  Briefcase,
  DatabaseBackup,
  HeartPulse,
  LayoutGrid,
  Plug,
  SlidersHorizontal,
} from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { confirmDialog } from "@/core/dialog";
import { api } from "@/core/api";
import type { AppSettings, BackupStatus } from "@/core/types";
import { SystemStatusPanel } from "@/modules/health/SystemStatus";
import { LinkedInProfilesEditor } from "@/modules/opportunity/LinkedInProfilesEditor";
import type { LucideIcon } from "lucide-react";
import { Button, NumberInput, PageFrame, Section, Select, Skeleton, SkeletonRows, cx, useToast } from "@/core/ui";
import { openGuide, openSourceDiscovery } from "@/core/onboarding/experience";
import { BrainAgentSection } from "./BrainAgentSection";
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
import {
  CareerProfileSection,
  DangerZoneSection,
  StorageReportSection,
  SystemDiagnosticsSection,
  TodayFlowSection,
} from "./SettingsPanels";
import type { CareerProfile } from "./SettingsPanels";
import { useOnline } from "@/lib/hooks";
import {
  BackupSection,
  IntegrationsSection,
  ModulesSection,
  ThemePicker,
  WeatherSection,
  type IntegrationStatus,
} from "./SettingsSections";

/**
 * Sekmeler URL'de yasar (`#/settings?tab=modules`): yenileyince kaybolmaz,
 * baglanti paylasilabilir.
 */
type SettingsGroup = "preferences" | "system";

const GROUP_LABELS: Record<SettingsGroup, string> = {
  preferences: "Tercihler",
  system: "Sistem",
};

/**
 * Ray iki anlamsal gruba ayrılır: kullanıcı TERCİHLERİ ile sistem işleri aynı
 * listede karışmaz. Sekme kimlikleri ve `?tab=` derin bağlantıları sözleşmedir;
 * yalnız etiket ve gruplama değişir.
 *
 * SİSTEM grubundaki ayrım bilinçlidir: "Entegrasyonlar" DIŞ sağlayıcıları
 * (Google Calendar, GitHub) barındırır; "Agent & Bilgi" ise ajan sınırlarını
 * (agent bağlantısı, f0rknbrain, yerel model, proaktivite, bekleyen kararlar,
 * Hermes tarifi) -- Obsidian Vault'u bu yüzden Entegrasyonlar altında değil
 * orada yaşar. "Durum & Kaynaklar" teşhis girişidir; ayrıntılı kartlar kanonik
 * `#/health`, kaynak kataloğu `#/sources` sayfasında kalır.
 */
const TABS: { id: string; label: string; icon: LucideIcon; group: SettingsGroup }[] = [
  { id: "general", label: "Genel & Görünüm", icon: SlidersHorizontal, group: "preferences" },
  { id: "today", label: "Home", icon: LayoutGrid, group: "preferences" },
  { id: "notifications", label: "Bildirimler & Çevre", icon: BellRing, group: "preferences" },
  { id: "modules", label: "Modüller", icon: Blocks, group: "preferences" },
  { id: "career", label: "Kariyer Profili", icon: Briefcase, group: "preferences" },
  { id: "brain", label: "Agent & Bilgi", icon: BrainCircuit, group: "system" },
  { id: "integrations", label: "Entegrasyonlar", icon: Plug, group: "system" },
  { id: "status", label: "Durum & Kaynaklar", icon: HeartPulse, group: "system" },
  { id: "backup", label: "Sistem & Yedekleme", icon: DatabaseBackup, group: "system" },
];

const TAB_IDS = new Set(TABS.map((tab) => tab.id));

/**
 * Ayarlar gövdesi. Tercih formları `form` genişliğinde kalır (uzun satır
 * okunmaz); iki kolonlu tanılama yüzeyi `wide` varyantını kullanır. Tek
 * varyant noktası burasıdır: sekme başına özel sarmalayıcı yazılmaz.
 */
function Pane({ children, width = "form" }: { children: React.ReactNode; width?: "form" | "wide" }) {
  return <div className={cx("mx-auto stack-y-4", width === "wide" ? "max-w-4xl" : "max-w-3xl")}>{children}</div>;
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
  const requestedTab = route.params.get("tab");
  const tab = requestedTab && TAB_IDS.has(requestedTab) ? requestedTab : "general";

  const [weatherLoc, setWeatherLoc] = useState<string | null>(null);
  const [retentionDays, setRetentionDays] = useState<number | null>(null);
  const [githubLogin, setGithubLogin] = useState("");
  const [githubToken, setGithubToken] = useState("");

  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<AppSettings>("/settings"),
  });
  const settings = settingsQuery.data;
  const {
    data: google,
    isError: googleFailed,
    refetch: refetchGoogle,
  } = useQuery({
    queryKey: ["google-status"],
    queryFn: () => api.get<IntegrationStatus>("/auth/google/status"),
  });
  const {
    data: github,
    isError: githubFailed,
    refetch: refetchGithub,
  } = useQuery({
    queryKey: ["github-status"],
    queryFn: () => api.get<IntegrationStatus>("/auth/github/status"),
  });
  const { data: backupStatus } = useBackupStatus();

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
  /**
   * Bağlantı kesme GERİ ALINAMAZ: kayıtlı OAuth jetonu silinir ve yeniden
   * bağlanmak gerekir. Bu yüzden tek tıkla çalışmaz; açık onay ister (§54).
   */
  async function requestDisconnect(provider: "github" | "google") {
    const label = provider === "github" ? "GitHub" : "Google";
    const ok = await confirmDialog({
      title: `${label} bağlantısı kesilsin mi?`,
      body: `Kayıtlı ${label} erişimi silinir. Bağlı özellikler (Takvim/GitHub) durur; yeniden bağlanman gerekir.`,
      confirmLabel: "Bağlantıyı kes",
    });
    if (!ok) return;
    disconnect.mutate(provider);
  }

  const backup = useMutation({
    mutationFn: () => api.post<{ path: string; size: number }>("/backup"),
    onSuccess: () => invalidateAfter("backup.write"),
  });
  const reset = useMutation({
    mutationFn: () => api.post<{ removed: number }>("/settings/reset"),
    onSuccess: (result) => {
      invalidateAfter("settings.write");
      setWeatherLoc(null);
      setRetentionDays(null);
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

  const go = (id: string) => navigate(`/settings?tab=${id}`);

  const rail = (
    <WorkspaceRailContent className="max-h-72 lg:max-h-workspace-body">
      {(["preferences", "system"] as const).map((group) => (
        <WorkspaceRailGroup key={group} label={GROUP_LABELS[group]}>
          {TABS.filter((item) => item.group === group).map((item) => {
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
      ))}
    </WorkspaceRailContent>
  );

  /**
   * Kabuk: ray ve sayfa başlığı veri beklerken de YERİNDE kalır. Önceki
   * davranış tüm sayfayı tek bir "yükleniyor" satırıyla değiştiriyordu; sekme
   * değiştirmek isteyen kullanıcı için bu her seferinde bir sıçramaydı.
   */
  const shell = (body: React.ReactNode) => (
    <PageFrame>
      <Workspace rail={rail}>
        <WorkspacePaneHeader eyebrow="Sistem" title="Ayarlar" hint={TABS.find((item) => item.id === tab)?.label} />
        <WorkspaceScrollArea className="p-4 sm:p-6">{body}</WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );

  // İki kolonlu tanılama yüzeyleri `wide` ister; form sekmeleri okunabilir
  // genişlikte kalır.
  const paneWidth = tab === "brain" || tab === "status" ? "wide" : "form";

  if (settingsQuery.isError) {
    return shell(
      <Pane>
        <Section title="Ayarlar">
          <p className="text-body text-warn">Ayarlar yüklenemedi.</p>
          <p className="mt-1 text-meta text-muted">{settingsQuery.error.message}</p>
          <Button className="mt-3" onClick={() => void settingsQuery.refetch()}>
            Yeniden dene
          </Button>
        </Section>
      </Pane>,
    );
  }

  if (!settings) {
    return shell(
      <Pane width={paneWidth}>
        <Skeleton className="h-24" />
        <SkeletonRows rows={3} />
      </Pane>,
    );
  }

  const disabled = settings["modules.disabled"] ?? [];
  const subreddits = Array.isArray(settings["news.subreddits"]) ? (settings["news.subreddits"] as string[]) : [];
  const career = (settings["opportunity.career_profile"] ?? {
    current_location: "",
    authorized_countries: [],
    willing_to_relocate: false,
  }) as CareerProfile;
  const write = (key: string, value: unknown) => save.mutate({ key, value });
  const toggleModule = (id: string) =>
    write("modules.disabled", disabled.includes(id) ? disabled.filter((x) => x !== id) : [...disabled, id]);
  const retention = retentionDays ?? Number(settings["rss.retention_days"] ?? 90);
  const intervalMinutes = Number(settings["rss.interval_minutes"] ?? 30);

  return shell(
    <>
      {tab === "general" && (
        <Pane>
          <Section title="Başlangıç ve rehberler">
            <div className="flex flex-wrap gap-2">
              <Button onClick={openGuide}>Rehberleri aç</Button>
              <Button onClick={openSourceDiscovery}>Akış kaynakları</Button>
            </div>
          </Section>
          <Section title="Tema">
            <ThemePicker />
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
          <TodayFlowSection online={online} subreddits={subreddits} onSave={write} />
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

      {tab === "brain" && (
        <Pane width={paneWidth}>
          <BrainAgentSection />
        </Pane>
      )}

      {tab === "career" && (
        <Pane>
          <CareerProfileSection online={online} profile={career} onSave={write} />
          <LinkedInProfilesEditor online={online} />
        </Pane>
      )}

      {tab === "status" && (
        <Pane width={paneWidth}>
          <SystemStatusPanel />
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
            onDisconnectGithub={() => requestDisconnect("github")}
            onDisconnectGoogle={() => requestDisconnect("google")}
            busy={disconnect.isPending}
            statusFailed={googleFailed || githubFailed}
            onRetryStatus={() => {
              void refetchGoogle();
              void refetchGithub();
            }}
          />
        </Pane>
      )}

      {tab === "backup" && (
        <Pane>
          <SystemDiagnosticsSection />
          <StorageReportSection />
          <BackupSection
            online={online}
            backupPending={backup.isPending}
            onBackup={() => backup.mutate()}
            backupData={backup.data}
            backupStatus={backupStatus}
          />
          <Section title="RSS otomasyonu">
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
          <DangerZoneSection onReset={() => reset.mutate()} busy={reset.isPending} />
        </Pane>
      )}
    </>,
  );
}
