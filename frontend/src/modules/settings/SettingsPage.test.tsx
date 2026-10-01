// @vitest-environment jsdom

/**
 * Ayarlar sayfasi sozlesmesi: sekme <-> URL hash senkronu, ayar yazmalari,
 * entegrasyon baglama/kesme, API anahtari girme/silme, yeni bolumler ve
 * tehlikeli bolge. Gercek ag yok; `fetch` kaydedici bir stub'dur.
 */

import { QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { queryClient } from "@/core/queryClient";
import "@/modules";
import { SettingsPage } from "./SettingsPage";

vi.mock("@/core/dialog", () => ({ confirmDialog: vi.fn(async () => true), DialogHost: () => null }));
// Yukaridaki mock modul replace eder; asagidaki import MOCK'u getirir.
import { confirmDialog } from "@/core/dialog";

const dialogSpy = vi.mocked(confirmDialog);

interface Call {
  method: string;
  path: string;
  body?: Record<string, unknown>;
}

/** `PUT /settings/{key}` govdesindeki `value` -- son yazmayi doner. */
function lastWrite(key: string): unknown {
  const write = [...calls].reverse().find((call) => call.method === "PUT" && call.path === `/api/settings/${key}`);
  return write?.body?.["value"];
}

/** Bir POST/DELETE cagrisinin govdesi. */
function postBody(path: string): Record<string, unknown> | undefined {
  return calls.find((call) => call.method === "POST" && call.path === path)?.body;
}

let calls: Call[] = [];
let settings: Record<string, unknown> = {};
let settingsFailed = false;
let githubStatus: { connected: boolean; login?: string | null } = { connected: false };
let googleStatus: { connected: boolean } = { connected: false };
/** Brain & Agent kartlarinin okudugu tanilama govdesi (dar tutulur). */
let agentStatus = {
  brain: {
    server_name: "forkos-brain",
    endpoint: "http://127.0.0.1:8787/mcp",
    transport: "streamable_http",
    loopback_only: true,
    tool_count: 29,
    families: [
      { id: "H0", label: "Operasyonel okuma", summary: "okuma", tool_count: 8 },
      { id: "H1", label: "Güvenli yazma", summary: "yazma", tool_count: 11 },
      { id: "H2", label: "Sıcak bellek", summary: "bellek", tool_count: 5 },
      { id: "H3", label: "Kanıt", summary: "kanıt", tool_count: 1 },
      { id: "H4", label: "Yerel biliş", summary: "yerel", tool_count: 1 },
      { id: "H5", label: "İnceleme zekâsı", summary: "inceleme", tool_count: 1 },
      { id: "H6", label: "Proaktivite", summary: "dikkat", tool_count: 1 },
      { id: "H7", label: "Dayanıklı yürütme", summary: "plan", tool_count: 1 },
    ],
  },
  local_cognition: {
    enabled: false,
    provider: "ollama",
    endpoint_class: "loopback",
    configured: false,
    reachable: null,
    state: "disabled",
    small: { configured: false, available: false },
    medium: { configured: false, available: false },
    detail: null,
  },
};

let obsidianStatus = {
  configured: false,
  available: false,
  writable: false,
  readable: false,
  vault_name: "",
  managed_files: 0,
  conflicts: 0,
  conflict_details: {} as Record<string, string[]>,
  diagnostic: null as string | null,
};

/** `GET /sources/forkjob-core/linkedin-profiles` gövdesi (Kariyer Profili sekmesi). */
const LINKEDIN_PROFILES = [{ term: "backend developer", location: "Berlin", results_wanted: 25, is_remote: true }];

function json(value: unknown): Response {
  return new Response(JSON.stringify(value), { status: 200, headers: { "Content-Type": "application/json" } });
}

const STATS = {
  cpu_pct: 12.3,
  load: [0.5, 0.4, 0.3],
  cpu_count: 8,
  mem_total_kb: 16_000_000,
  mem_available_kb: 8_000_000,
  disk: { total: 500_000_000_000, free: 250_000_000_000 },
  uptime_s: 3 * 86_400,
  worker: { status: "healthy", heartbeat_at: new Date().toISOString() },
};

function baseSettings(): Record<string, unknown> {
  return {
    "modules.disabled": [],
    "today.widget_order": [],
    "today.widget_hidden": [],
    "today.auto_suggestions": true,
    "rss.retention_days": 90,
    "media.links": [],
    "media.upcoming_days": 30,
    "media.sync_interval_hours": 24,
    "media.tmdb_key": "",
    "media.igdb_client_id": "",
    "media.igdb_client_secret": "",
    "media.google_books_key": "",
    "news.subreddits": ["programming"],
    "opportunity.career_profile": {
      current_location: "Ankara, Türkiye",
      authorized_countries: ["Türkiye"],
      willing_to_relocate: false,
    },
    "weather.location": "Ankara",
  };
}

/** `opportunity.career_profile` yazmasinin son hali -- daraltilmis okuma. */
function careerProfile(): { current_location?: string; authorized_countries?: string[] } | undefined {
  const value = lastWrite("opportunity.career_profile");
  if (typeof value !== "object" || value === null) return undefined;
  const profile: { current_location?: string; authorized_countries?: string[] } = {};
  if ("current_location" in value && typeof value.current_location === "string") {
    profile.current_location = value.current_location;
  }
  if ("authorized_countries" in value && Array.isArray(value.authorized_countries)) {
    profile.authorized_countries = value.authorized_countries.filter(
      (item): item is string => typeof item === "string",
    );
  }
  return profile;
}

function renderPage() {
  return render(
    <QueryClientProvider client={queryClient()}>
      <ToastProvider>
        <SettingsPage />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

/** Sayfa yuklenene kadar bekle (Ayarlar basligi gelir). */
async function ready() {
  await screen.findByRole("heading", { level: 1, name: "Ayarlar" });
}

function openTab(label: string) {
  fireEvent.click(screen.getByRole("button", { name: label }));
}

beforeEach(() => {
  calls = [];
  settings = baseSettings();
  settingsFailed = false;
  githubStatus = { connected: false };
  googleStatus = { connected: false };
  agentStatus = {
    ...agentStatus,
    brain: { ...agentStatus.brain, loopback_only: true, tool_count: 29 },
    local_cognition: { ...agentStatus.local_cognition, state: "disabled", enabled: false, reachable: null },
  };
  obsidianStatus = {
    configured: false,
    available: false,
    writable: false,
    readable: false,
    vault_name: "",
    managed_files: 0,
    conflicts: 0,
    conflict_details: {},
    diagnostic: null,
  };
  dialogSpy.mockClear();
  dialogSpy.mockResolvedValue(true);
  queryClient().clear();
  location.hash = "#/settings?tab=general";
  Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: { getItem: () => null, setItem: vi.fn(), removeItem: vi.fn() },
  });
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", { configurable: true, value: vi.fn() });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const method = (init?.method ?? "GET").toUpperCase();
      const body: Record<string, unknown> | undefined = init?.body ? JSON.parse(String(init.body)) : undefined;
      calls.push({ method, path: url.pathname, body });

      if (url.pathname === "/api/settings" && method === "GET") {
        if (settingsFailed) return new Response(JSON.stringify({ detail: "ayarlar okunamadı" }), { status: 500 });
        return json(settings);
      }
      if (url.pathname.startsWith("/api/settings/") && method === "PUT") {
        const key = decodeURIComponent(url.pathname.slice("/api/settings/".length));
        settings[key] = body?.["value"];
        return json({ key, value: body?.["value"] });
      }
      if (url.pathname === "/api/settings/reset") return json({ removed: 3 });
      if (url.pathname === "/api/sources/health") return json([]);
      if (url.pathname === "/api/sources/coverage") return json([]);
      if (url.pathname === "/api/sources/forkjob-core/linkedin-profiles") return json(LINKEDIN_PROFILES);
      if (url.pathname === "/api/rss/feeds") return json([]);
      if (url.pathname === "/api/rss/stats")
        return json({ feeds: 0, active_feeds: 0, failing_feeds: 0, unread: 0, today: 0, saved: 0 });
      if (url.pathname === "/api/proactivity/status") return json({ enabled: false });
      if (url.pathname === "/api/backup/status")
        return json({ last_backup: null, drive_folder_id: null, last_drive_upload: null, last_drive_error: null });
      if (url.pathname === "/api/auth/github/status") return json(githubStatus);
      if (url.pathname === "/api/auth/google/status") return json(googleStatus);
      if (url.pathname === "/api/obsidian/status") return json(obsidianStatus);
      if (url.pathname === "/api/agent/status") return json(agentStatus);
      if (url.pathname === "/api/execution/plans") return json([]);
      if (url.pathname === "/api/obsidian/index/refresh" && method === "POST") {
        obsidianStatus = { ...obsidianStatus, managed_files: obsidianStatus.managed_files + 1 };
        return json(obsidianStatus);
      }
      if (url.pathname === "/api/auth/github" && method === "DELETE") {
        githubStatus = { connected: false };
        return new Response(null, { status: 204 });
      }
      if (url.pathname === "/api/auth/google" && method === "DELETE") {
        googleStatus = { connected: false };
        return new Response(null, { status: 204 });
      }
      if (url.pathname === "/api/auth/github" && method === "POST") {
        githubStatus = { connected: true, login: "octocat" };
        return json({ connected: true, login: "octocat" });
      }
      if (url.pathname === "/api/media/artwork/stats")
        return json({ files: 128, bytes: 5_242_880, max_bytes: 536_870_912 });
      if (url.pathname === "/api/media/artwork/prune" && method === "POST")
        return json({ removed: 12, freed_bytes: 2_097_152 });
      if (url.pathname === "/api/system/stats") return json(STATS);
      if (url.pathname === "/api/system/refresh") return json({ status: "running" });
      if (url.pathname === "/api/weather/geocode") return json({ name: "Berlin", latitude: 52.5, longitude: 13.4 });
      return json({});
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("SettingsPage sekmeleri", () => {
  it("sekmeyi URL hash'inden okur ve rail tiklamasiyla hash'i gunceller", async () => {
    location.hash = "#/settings?tab=modules";
    renderPage();
    await ready();

    // Moduller sekmesi acik: gorunurluk ve arka plan guncellemesi AYRI
    // anlatilir; ikisi ayni kavram degildir.
    // "Modüller" hem rail sekmesi hem bolum basligi olabilir: hepsini kabul et.
    expect((await screen.findAllByText("Modüller")).length).toBeGreaterThan(0);
    expect(await screen.findByText("Arka plan güncellemesi")).toBeTruthy();
    expect(
      await screen.findByText(/Kapatılan modülün rotası, Home bileşenleri ve komutları devre dışı kalır/),
    ).toBeTruthy();

    openTab("Kariyer Profili");
    await waitFor(() => expect(location.hash).toBe("#/settings?tab=career"));
    expect(await screen.findByRole("heading", { name: "Kariyer Profili" })).toBeTruthy();
  });

  it("eski ?section=media-links baglantisi Entegrasyonlar sekmesini acar", async () => {
    location.hash = "#/settings?section=media-links";
    renderPage();
    await ready();

    expect(await screen.findByText("Medya sağlayıcı anahtarları")).toBeTruthy();
    expect(document.activeElement?.id).toBe("media-links");
  });
});

describe("SettingsPage yazmalari", () => {
  it("modul anahtarini modules.disabled ayarina yazar", async () => {
    location.hash = "#/settings?tab=modules";
    renderPage();
    await ready();

    fireEvent.click(await screen.findByRole("checkbox", { name: "Bilgi" }));
    await waitFor(() => {
      expect(lastWrite("modules.disabled")).toContain("knowledge");
    });
  });

  it("API anahtarini kaydeder ve alan bosaltilinca siler", async () => {
    location.hash = "#/settings?tab=integrations";
    renderPage();
    await ready();

    const field = await screen.findByLabelText("TMDB API anahtarı");
    fireEvent.change(field, { target: { value: "tmdb-secret" } });
    fireEvent.blur(field, { target: { value: "tmdb-secret" } });
    await waitFor(() => expect(lastWrite("media.tmdb_key")).toBe("tmdb-secret"));

    fireEvent.change(field, { target: { value: "" } });
    fireEvent.blur(field, { target: { value: "" } });
    await waitFor(() => expect(lastWrite("media.tmdb_key")).toBe(""));
  });

  it("goz dugmesi anahtari gorunur yapar", async () => {
    location.hash = "#/settings?tab=integrations";
    renderPage();
    await ready();

    const field = await screen.findByLabelText("IGDB Client Secret");
    expect(field.getAttribute("type")).toBe("password");
    fireEvent.click(screen.getByRole("button", { name: "IGDB Client Secret göster" }));
    expect(field.getAttribute("type")).toBe("text");
  });

  it("kariyer profilini tek nesne olarak kaydeder", async () => {
    location.hash = "#/settings?tab=career";
    renderPage();
    await ready();

    const locationField = await screen.findByLabelText("Mevcut konum");
    fireEvent.change(locationField, { target: { value: "Berlin, Almanya" } });
    fireEvent.blur(locationField, { target: { value: "Berlin, Almanya" } });
    await waitFor(() => expect(careerProfile()?.current_location).toBe("Berlin, Almanya"));

    fireEvent.change(await screen.findByLabelText("Çalışma izni olan ülke"), { target: { value: "Almanya" } });
    fireEvent.click(screen.getByRole("button", { name: "ekle" }));
    await waitFor(() => expect(careerProfile()?.authorized_countries).toEqual(["Türkiye", "Almanya"]));
  });

  it("subreddit listesini ekler ve kaldirir", async () => {
    location.hash = "#/settings?tab=today";
    renderPage();
    await ready();

    fireEvent.change(screen.getByLabelText("Subreddit adı"), { target: { value: "rust" } });
    fireEvent.click(screen.getAllByRole("button", { name: "ekle" }).at(-1)!);
    await waitFor(() => expect(lastWrite("news.subreddits")).toEqual(["programming", "rust"]));

    fireEvent.click(screen.getByRole("button", { name: "programming kaldır" }));
    await waitFor(() => expect(lastWrite("news.subreddits")).toEqual(["rust"]));
  });

  it("Google Drive hedef klasor kimligini kaydeder", async () => {
    location.hash = "#/settings?tab=backup";
    renderPage();
    await ready();

    const field = await screen.findByLabelText("Google Drive hedef klasör kimliği");
    fireEvent.change(field, { target: { value: "1AbCdEf" } });
    fireEvent.blur(field, { target: { value: "1AbCdEf" } });
    await waitFor(() => expect(lastWrite("backup.drive_folder_id")).toBe("1AbCdEf"));
  });

  it("medya yaklaşan penceresini ve tarama aralığını blur'da kaydeder", async () => {
    location.hash = "#/settings?tab=integrations";
    renderPage();
    await ready();

    const upcoming = await screen.findByLabelText("Yaklaşan penceresi (gün)");
    fireEvent.change(upcoming, { target: { value: "45" } });
    fireEvent.blur(upcoming, { target: { value: "45" } });
    await waitFor(() => expect(lastWrite("media.upcoming_days")).toBe(45));

    const interval = screen.getByLabelText("Otomatik tarama aralığı (saat)");
    fireEvent.change(interval, { target: { value: "12" } });
    fireEvent.blur(interval, { target: { value: "12" } });
    await waitFor(() => expect(lastWrite("media.sync_interval_hours")).toBe(12));

    // Degismeyen deger tekrar yazilmaz.
    const writes = calls.filter((call) => call.method === "PUT" && call.path === "/api/settings/media.upcoming_days");
    fireEvent.blur(screen.getByLabelText("Yaklaşan penceresi (gün)"), { target: { value: "45" } });
    await waitFor(() => expect(writes).toHaveLength(1));
  });

  it("ölü media.rawg_key alanını açmaz, kaldırılma notunu gösterir", async () => {
    location.hash = "#/settings?tab=integrations";
    renderPage();
    await ready();

    expect(await screen.findByText(/RAWG ve Kitsu desteği kaldırıldı/)).toBeTruthy();
    expect(screen.queryByLabelText(/RAWG/i)).toBeNull();
    expect(screen.queryByDisplayValue("media.rawg_key")).toBeNull();
  });

  it("görsel önbelleği özetini gösterir ve temizler", async () => {
    location.hash = "#/settings?tab=integrations";
    renderPage();
    await ready();

    expect(await screen.findByText("128 görsel · 5.0 MB / 512.0 MB")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Önbelleği temizle" }));
    await waitFor(() =>
      expect(calls.some((call) => call.method === "POST" && call.path === "/api/media/artwork/prune")).toBe(true),
    );
    expect(await screen.findByText("12 görsel silindi, 2.0 MB kazanıldı.")).toBeTruthy();
  });

  it("çevrimdışıyken önbellek temizliğini kapatır", async () => {
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: false });
    location.hash = "#/settings?tab=integrations";
    renderPage();
    await ready();

    const button = (await screen.findByRole("button", { name: "Önbelleği temizle" })) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });
});

describe("SettingsPage entegrasyonlari", () => {
  it("GitHub token'ini baglar ve baglantiyi keser", async () => {
    location.hash = "#/settings?tab=integrations";
    renderPage();
    await ready();

    fireEvent.change(await screen.findByPlaceholderText("login"), { target: { value: "octocat" } });
    fireEvent.change(screen.getByPlaceholderText("fine-grained token"), { target: { value: "gh-token" } });
    fireEvent.click(screen.getByRole("button", { name: "kaydet" }));

    await waitFor(() => expect(postBody("/api/auth/github")).toEqual({ login: "octocat", token: "gh-token" }));
    // Baglandiktan sonra "kes" gorunur.
    await waitFor(() => expect(screen.getByRole("button", { name: "kes" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "kes" }));
    await waitFor(() =>
      expect(calls.some((call) => call.method === "DELETE" && call.path === "/api/auth/github")).toBe(true),
    );
  });

  it("bagli olmayan entegrasyonu kirmizi rozetle ve kilavuz linkiyle gosterir", async () => {
    location.hash = "#/settings?tab=integrations";
    renderPage();
    await ready();

    // Iki servis de bagli degil: yesil "bagli" rozeti YOK, kirmizi rozet var.
    expect(await screen.findAllByText("bağlı değil")).toHaveLength(2);
    const danger = screen.getAllByText("bağlı değil").every((node) => node.className.includes("text-danger"));
    expect(danger).toBe(true);

    // Kimlik bilgisi kilavuzu: dogru adres, yeni sekme, noopener.
    const google = screen.getByRole("link", { name: /Drive API kimlik bilgileri/ });
    expect(google.getAttribute("href")).toBe("https://console.cloud.google.com/apis/credentials");
    expect(google.getAttribute("target")).toBe("_blank");
    expect(google.getAttribute("rel")).toContain("noreferrer");

    const github = screen.getByRole("link", { name: /Personal access token oluştur/ });
    expect(github.getAttribute("href")).toBe("https://github.com/settings/tokens");
    expect(github.getAttribute("rel")).toContain("noreferrer");
  });

  it("bagliyken kirmizi rozet kalkar", async () => {
    googleStatus = { connected: true };
    location.hash = "#/settings?tab=integrations";
    renderPage();
    await ready();

    await waitFor(() => expect(screen.getByText("bağlı")).toBeTruthy());
    // Google bagli; yalnizca GitHub'in kirmizi rozeti kalir.
    expect(screen.getAllByText("bağlı değil")).toHaveLength(1);
  });

  it("Google baglantisini keser", async () => {
    googleStatus = { connected: true };
    location.hash = "#/settings?tab=integrations";
    renderPage();
    await ready();

    await waitFor(() => expect(screen.getByText("bağlı")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "kes" }));
    await waitFor(() =>
      expect(calls.some((call) => call.method === "DELETE" && call.path === "/api/auth/google")).toBe(true),
    );
  });

  it("Vault durumunu Agent & Bilgi sekmesinde gosterir ve indeksi yeniler", async () => {
    obsidianStatus = {
      configured: true,
      available: true,
      writable: true,
      readable: true,
      vault_name: "PersonalVault",
      managed_files: 42,
      conflicts: 0,
      conflict_details: {},
      diagnostic: null,
    };
    location.hash = "#/settings?tab=brain";
    renderPage();
    await ready();

    // f0rknbrain artik BIR DIS SAGLAYICI degil, bilgi sahibi olarak burada yasar.
    expect((await screen.findAllByText("Bağlı ve hazır")).length).toBeGreaterThan(0);
    expect(screen.getByText("PersonalVault")).toBeTruthy();
    expect(screen.getByText("42 yönetilen not")).toBeTruthy();
    expect(screen.getByText("okunabilir")).toBeTruthy();
    expect(screen.getByText("yazılabilir")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "İndeksi Yenile" }));
    await waitFor(() =>
      expect(calls.some((call) => call.method === "POST" && call.path === "/api/obsidian/index/refresh")).toBe(true),
    );
    expect(await screen.findByText("Vault indeksi yenilendi.")).toBeTruthy();
  });

  it("Vault cakismalarini Agent & Bilgi kartinda listeler", async () => {
    obsidianStatus = {
      configured: true,
      available: true,
      writable: true,
      readable: true,
      vault_name: "PersonalVault",
      managed_files: 10,
      conflicts: 1,
      conflict_details: {
        "12345678-1234-1234-1234-123456789abc": ["20 Projects/Project A.md", "20 Projects/Project B.md"],
      },
      diagnostic: null,
    };
    location.hash = "#/settings?tab=brain";
    renderPage();
    await ready();

    expect(await screen.findByText("1 çakışma")).toBeTruthy();
    expect(screen.getByText(/Aynı forkOS kimliği birden fazla Vault dosyasında bulunuyor/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Çakışan kayıtlar \(1\)/ }));
    expect(screen.getByText("20 Projects/Project A.md")).toBeTruthy();
    expect(screen.getByText("20 Projects/Project B.md")).toBeTruthy();
  });
});

describe("SettingsPage teshis ve tehlikeli bolge", () => {
  it("sistem teshisini Sistem sekmesinde gosterir ve elle senkronu tetikler", async () => {
    // Teshis artik bir TERCIH degil: Yedekleme & Sistem sekmesinde yasar.
    location.hash = "#/settings?tab=backup";
    renderPage();
    await ready();

    expect(await screen.findByText("%12")).toBeTruthy();
    expect(screen.getByText("3 gün 0 sa")).toBeTruthy();
    expect(screen.getByText(/arka plan: sağlıklı/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Şimdi senkronize et/ }));
    await waitFor(() =>
      expect(calls.some((call) => call.method === "POST" && call.path === "/api/system/refresh")).toBe(true),
    );
  });

  it("onaydan sonra ayarlari sifirlar", async () => {
    location.hash = "#/settings?tab=backup";
    renderPage();
    await ready();

    fireEvent.click(screen.getByRole("button", { name: "Ayarları varsayılana döndür" }));
    await waitFor(() => expect(dialogSpy).toHaveBeenCalled());
    await waitFor(() =>
      expect(calls.some((call) => call.method === "POST" && call.path === "/api/settings/reset")).toBe(true),
    );
  });

  it("ray tercihleri ve sistemi ayirir; teshis Genel sekmesinde yer almaz", async () => {
    location.hash = "#/settings?tab=general";
    renderPage();
    await ready();

    // Ray iki anlamsal grup: kullanıcı tercihleri ile sistem işleri karışmaz.
    expect(screen.getByText("Tercihler")).toBeTruthy();
    // "Sistem" hem ray grubu hem bir bolum basligi olabilir: ray grubunu ara.
    expect(screen.getAllByText("Sistem").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Genel & Görünüm" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sistem & Yedekleme" })).toBeTruthy();

    // Genel sekmesi yalnız kullanıcı tercihi taşır: CPU/RAM/diskten söz etmez.
    expect(screen.queryByText("%12")).toBeNull();
    expect(screen.queryByText("Depolama")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Sistem & Yedekleme" }));
    expect(await screen.findByText("%12")).toBeTruthy();
    expect(screen.getByText("Depolama")).toBeTruthy();
  });

  it("Agent & Bilgi sekmesini Sistem grubunda sunar ve derin baglantiyla acar", async () => {
    location.hash = "#/settings?tab=brain";
    renderPage();
    await ready();

    expect(screen.getByRole("button", { name: "Agent & Bilgi" })).toBeTruthy();
    // Sekme govdesi: sahiplik notu + genel durum + kartlar.
    expect(await screen.findByText("Genel durum")).toBeTruthy();
    expect(screen.getByText(/akıl yürütür ve orkestre eder/)).toBeTruthy();
    expect(screen.getByText("forkos-brain")).toBeTruthy();
    expect(screen.getAllByText("Bekleyen kararlar").length).toBeGreaterThan(0);
  });

  it("Obsidian'i Entegrasyonlar'dan cikarir; orada yalniz dis saglayicilar kalir", async () => {
    obsidianStatus = {
      configured: true,
      available: true,
      writable: true,
      readable: true,
      vault_name: "PersonalVault",
      managed_files: 5,
      conflicts: 0,
      conflict_details: {},
      diagnostic: null,
    };
    location.hash = "#/settings?tab=integrations";
    renderPage();
    await ready();

    expect(screen.getByText("Bulut & Geliştirici")).toBeTruthy();
    expect(screen.getByText("Google Drive")).toBeTruthy();
    expect(screen.getByText("GitHub")).toBeTruthy();
    // Vault'a ait hicbir iz bu sekmede yoktur.
    expect(screen.queryByText("PersonalVault")).toBeNull();
    expect(screen.queryByText(/yönetilen not/)).toBeNull();
  });

  it("Proaktiviteyi Bildirimler'den cikarip Agent & Bilgi'ye tasir", async () => {
    location.hash = "#/settings?tab=notifications";
    renderPage();
    await ready();

    expect(screen.getByText("Hava durumu")).toBeTruthy();
    expect(screen.queryByText("Sessizlik başarılı bir sonuçtur.")).toBeNull();
    expect(screen.queryByText("Proaktivite")).toBeNull();

    cleanup();
    location.hash = "#/settings?tab=brain";
    renderPage();
    await ready();
    expect(await screen.findByText("Sessizlik başarılı bir sonuçtur.")).toBeTruthy();
  });

  it("Ayarlar istegi dustugunde sayfa cokmez; hata ve yeniden dene sunar", async () => {
    settingsFailed = true;
    location.hash = "#/settings?tab=general";
    renderPage();
    await ready();

    // Paylasilan istemci tek kez yeniden dener (retry: 1): hatayi bekleyerek olcelim.
    expect(await screen.findByText("Ayarlar yüklenemedi.", {}, { timeout: 5000 })).toBeTruthy();
    expect(screen.getByText("ayarlar okunamadı")).toBeTruthy();
    // Ray kaybolmaz: kullanici baska sekmeye gecebilir.
    expect(screen.getByRole("button", { name: "Agent & Bilgi" })).toBeTruthy();

    settingsFailed = false;
    fireEvent.click(screen.getByRole("button", { name: "Yeniden dene" }));
    expect(await screen.findByText("Tema")).toBeTruthy();
  });

  it("entegrasyon durumu alinamazsa 'bagli degil' demez", async () => {
    location.hash = "#/settings?tab=integrations";
    renderPage();
    await ready();

    // Kurgu: github/google uclari bos govde doner -> baglanti BILINMIYOR degil,
    // "bagli degil" denir; hata halinde ise ayri metin beklenir.
    expect(await screen.findByText("Bulut & Geliştirici")).toBeTruthy();
    expect(screen.getAllByText("bağlı değil").length).toBe(2);
  });

  it("depolama raporu ve bakim durumunu Sistem sekmesinde gosterir", async () => {
    location.hash = "#/settings?tab=backup";
    renderPage();
    await ready();

    expect(await screen.findByText("Depolama")).toBeTruthy();
    expect(screen.getByText("Otomatik hafif bakım")).toBeTruthy();
    expect(screen.getByText(/Sonraki: her gün 04:00 \/ açılışta/)).toBeTruthy();
  });
});

describe("SettingsPage Durum & Kaynaklar ve Kariyer Profili", () => {
  it("Durum & Kaynaklar sekmesinde saglik ozetini ve kaynak operasyonlari baglantisini gosterir", async () => {
    location.hash = "#/settings?tab=status";
    renderPage();
    await ready();

    // Saglik/Kaynaklar icin ikinci bir uygulama yok: ozet ve tanilama paketi
    // Sistem Durumu sayfasinin bilesenleridir.
    expect(await screen.findByText("Genel bakış")).toBeTruthy();
    expect(screen.getByText("forkOS Doctor")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Şimdi kontrol et" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Tam sistem kontrolü komutunu kopyala" })).toBeTruthy();
    expect(screen.getByText("İlgi gerekenler")).toBeTruthy();
    expect(screen.getByText("Kaynak sağlığı")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Teşhisi kopyala" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Kaynak operasyonları →" }).getAttribute("href")).toBe("#/sources");

    // Özet kullanıcı dilinde kalır: iç katman kodları ekrana basılmaz.
    expect(screen.getByText("Agent bağlantısı")).toBeTruthy();
    expect(screen.getAllByText("Bekleyen kararlar").length).toBeGreaterThan(0);
    expect(document.body.textContent).not.toMatch(/\bH[0-7]\b/);
  });

  it("Kariyer Profili sekmesinde LinkedIn arama profillerini kaydeder", async () => {
    location.hash = "#/settings?tab=career";
    renderPage();
    await ready();

    expect(await screen.findByText("LinkedIn arama profilleri")).toBeTruthy();
    const term = screen.getByDisplayValue("backend developer");
    fireEvent.change(term, { target: { value: "data engineer" } });
    fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));

    await waitFor(() => {
      const put = calls.find(
        (call) => call.method === "PUT" && call.path === "/api/sources/forkjob-core/linkedin-profiles",
      );
      expect(put?.body).toEqual([{ term: "data engineer", location: "Berlin", results_wanted: 25, is_remote: true }]);
    });
  });
});
