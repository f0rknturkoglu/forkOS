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
let githubStatus: { connected: boolean; login?: string | null } = { connected: false };
let googleStatus: { connected: boolean } = { connected: false };

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
  githubStatus = { connected: false };
  googleStatus = { connected: false };
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

      if (url.pathname === "/api/settings" && method === "GET") return json(settings);
      if (url.pathname.startsWith("/api/settings/") && method === "PUT") {
        const key = decodeURIComponent(url.pathname.slice("/api/settings/".length));
        settings[key] = body?.["value"];
        return json({ key, value: body?.["value"] });
      }
      if (url.pathname === "/api/settings/reset") return json({ removed: 3 });
      if (url.pathname === "/api/sources/health") return json([]);
      if (url.pathname === "/api/backup/status")
        return json({ last_backup: null, drive_folder_id: null, last_drive_upload: null, last_drive_error: null });
      if (url.pathname === "/api/auth/github/status") return json(githubStatus);
      if (url.pathname === "/api/auth/google/status") return json(googleStatus);
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

    // Moduller sekmesi acik: modul adlari ve aciklamalari gorunur.
    expect(
      await screen.findByText(
        "Kapatılan modülün rotası, Bugün widget'ları ve komutları devre dışı kalır; verisi silinmez. Ayarlar her zaman açıktır.",
      ),
    ).toBeTruthy();

    openTab("Kariyer profili");
    await waitFor(() => expect(location.hash).toBe("#/settings?tab=career"));
    expect(await screen.findByRole("heading", { name: "Kariyer profili" })).toBeTruthy();
  });

  it("eski ?section=media-links baglantisi Entegrasyonlar sekmesini acar", async () => {
    location.hash = "#/settings?section=media-links";
    renderPage();
    await ready();

    expect(await screen.findByText("Medya bağlantıları")).toBeTruthy();
    expect(document.activeElement?.id).toBe("media-links");
  });
});

describe("SettingsPage yazmalari", () => {
  it("modul anahtarini modules.disabled ayarina yazar", async () => {
    location.hash = "#/settings?tab=modules";
    renderPage();
    await ready();

    fireEvent.click(await screen.findByRole("checkbox", { name: "Notlar" }));
    await waitFor(() => {
      expect(lastWrite("modules.disabled")).toContain("notes");
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

  it("bugun onerilerini kapatir ve subreddit listesini gunceller", async () => {
    location.hash = "#/settings?tab=today";
    renderPage();
    await ready();

    fireEvent.click(
      await screen.findByRole("checkbox", {
        name: "Bugün akışında akıllı görev ve RSS önerilerini göster",
      }),
    );
    await waitFor(() => expect(lastWrite("today.auto_suggestions")).toBe(false));

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
});

describe("SettingsPage teshis ve tehlikeli bolge", () => {
  it("sistem teshisini gosterir ve elle senkronu tetikler", async () => {
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
});
