// @vitest-environment jsdom

/**
 * Agent & Bilgi yüzeyi sözleşmesi.
 *
 * Bu dosya ÜRÜN DÜRÜSTLÜĞÜNÜ test eder: yüzeyin söylediği her şey forkOS'un
 * gerçekten bilebileceği bir şey olmalı. Özellikle "Hermes bağlı" gibi bir
 * iddia HİÇBİR durumda görünmemelidir (forkOS istemci durumunu doğrulayamaz).
 *
 * Gerçek ağ yok: `fetch` kaydedici bir stub'dur; karar/onay butonu çağrısı
 * yapılmadığı ayrıca doğrulanır.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";
import { BrainAgentSection } from "./BrainAgentSection";

const navigateSpy = vi.fn();
const openObsidianSpy = vi.fn();
let online = true;

vi.mock("@/app/router", () => ({ navigate: (path: string) => navigateSpy(path) }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => online }));
vi.mock("@/core/obsidian", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/obsidian")>();
  return { ...actual, openObsidianUri: (uri: string) => openObsidianSpy(uri) };
});

interface Call {
  method: string;
  path: string;
}

let calls: Call[] = [];
let agentStatus: Record<string, unknown> = {};
let vaultStatus: Record<string, unknown> = {};
let plans: unknown[] = [];
let agentFailed = false;
let vaultFailed = false;
let plansFailed = false;

const FAMILIES = [
  { id: "H0", label: "Operasyonel okuma", summary: "briefing", tool_count: 8 },
  { id: "H1", label: "Güvenli yazma", summary: "kapalı sözlük", tool_count: 11 },
  { id: "H2", label: "Sıcak bellek", summary: "hatırlatmalar", tool_count: 5 },
  { id: "H3", label: "Kanıt", summary: "evidence", tool_count: 1 },
  { id: "H4", label: "Yerel biliş", summary: "yerel model", tool_count: 1 },
  { id: "H5", label: "İnceleme zekâsı", summary: "review", tool_count: 1 },
  { id: "H6", label: "Proaktivite", summary: "dikkat", tool_count: 1 },
  { id: "H7", label: "Dayanıklı yürütme", summary: "plan", tool_count: 1 },
];

/** `GET /agent/status` gövdesi; test başına alan değiştirilir. */
function makeAgentStatus(overrides: { loopback?: boolean; h4?: Record<string, unknown> } = {}) {
  return {
    brain: {
      server_name: "forkos-brain",
      endpoint: "http://127.0.0.1:8787/mcp",
      transport: "streamable_http",
      loopback_only: overrides.loopback ?? true,
      tool_count: 29,
      families: FAMILIES,
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
      ...overrides.h4,
    },
  };
}

function makeVaultStatus(overrides: Record<string, unknown> = {}) {
  return {
    configured: true,
    available: true,
    writable: true,
    readable: true,
    vault_name: "f0rknbrain",
    managed_files: 13,
    conflicts: 0,
    conflict_details: {},
    invalid_files: [],
    diagnostic: null,
    open_uri: "obsidian://open?vault=f0rknbrain",
    inbox_uri: "obsidian://open?vault=f0rknbrain&file=00%20Inbox",
    daily_uri: "obsidian://open?vault=f0rknbrain&file=2026-09-21",
    ...overrides,
  };
}

function json(value: unknown): Response {
  return new Response(JSON.stringify(value), { status: 200, headers: { "Content-Type": "application/json" } });
}

function plan(overrides: Record<string, unknown> = {}) {
  return {
    plan_row_id: 1,
    plan_id: "plan-1",
    revision: "r1",
    is_current_revision: true,
    state: "awaiting_approval",
    title: "Kitap listesini güncelle",
    summary: null,
    reason: null,
    steps: [],
    step_count: 1,
    mutation_count: 1,
    budget: {},
    source_refs: [],
    evidence_refs: [],
    validation_status: "valid",
    validation_errors: [],
    input_questions: [],
    input_answers: {},
    approved_revision: null,
    approved_at: null,
    expires_at: null,
    decision_required: true,
    final_status: null,
    failure_code: null,
    receipts: [],
    created_at: "2026-09-20T10:00:00Z",
    updated_at: "2026-09-21T09:00:00Z",
    ...overrides,
  };
}

async function ready() {
  // "Genel durum" bloğu her durumda gelir: yüzeyin çizildiğinin kanıtı.
  await screen.findByText("Genel durum");
}

beforeEach(() => {
  calls = [];
  navigateSpy.mockClear();
  openObsidianSpy.mockClear();
  online = true;
  agentFailed = false;
  vaultFailed = false;
  plansFailed = false;
  agentStatus = makeAgentStatus();
  vaultStatus = makeVaultStatus();
  plans = [];
  Object.defineProperty(window.navigator, "onLine", { configurable: true, value: true });
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: {
      onLine: true,
      clipboard: { writeText: vi.fn(async () => undefined) },
    },
  });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const method = (init?.method ?? "GET").toUpperCase();
      calls.push({ method, path: url.pathname });
      if (url.pathname === "/api/agent/status") {
        if (agentFailed) throw new TypeError("Failed to fetch");
        return json(agentStatus);
      }
      if (url.pathname === "/api/agent/lifecycle/status")
        return json({
          available: true,
          last_event_at: null,
          last_harness: null,
          active_sessions: 0,
          last_finalized_at: null,
          incomplete_session_count: 0,
        });
      if (url.pathname === "/api/agent/continuity/status")
        return json({
          available: true,
          last_bootstrap_at: null,
          last_harness: null,
          active_source_count: 0,
          is_truncated: false,
          degraded_reasons: [],
          has_active_continuity: false,
        });
      if (url.pathname === "/api/obsidian/status") {
        if (vaultFailed) throw new TypeError("Failed to fetch");
        return json(vaultStatus);
      }
      if (url.pathname === "/api/obsidian/index/refresh") return json(vaultStatus);
      if (url.pathname === "/api/execution/plans") {
        if (plansFailed) throw new TypeError("Failed to fetch");
        return json(plans);
      }
      if (url.pathname === "/api/proactivity/status")
        return json({
          enabled: false,
          quiet_hours_start: "23:30",
          quiet_hours_end: "08:30",
          focus_deferral_enabled: true,
          digest_time: "18:00",
          immediate_budget: 2,
          immediate_surfaces_today: 0,
          pending_deferred: 0,
          pending_digest: 0,
          worker_heartbeat: null,
          last_run_at: null,
          rules: [],
          recent_failures: [],
        });
      if (url.pathname === "/api/proactivity/rules") return json([]);
      if (url.pathname === "/api/proactivity/history") return json([]);
      if (url.pathname === "/api/system/stats")
        return json({
          cpu_pct: 5,
          load: [0.2, 0.2, 0.2],
          cpu_count: 8,
          mem_total_kb: 16_000_000,
          mem_available_kb: 8_000_000,
          disk: { total: 500_000_000_000, free: 250_000_000_000 },
          uptime_s: 3600,
          worker: { status: "disabled", heartbeat_at: null },
        });
      return json({});
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/**
 * Hata durumlarini deterministik olcmek icin tekrar deneme KAPALI bir istemci:
 * varsayilan backoff, "istek dustu" senaryosunu saniyeler sonraya birakirdi.
 */
function testClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderSection() {
  return render(
    <QueryClientProvider client={testClient()}>
      <ToastProvider>
        <BrainAgentSection />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("Agent bağlantısı kartı", () => {
  it("sunucu, taşıma, araç sayısı ve yerel sınırı gerçek değerlerle gösterir", async () => {
    renderSection();
    await ready();

    expect(await screen.findByText("forkos-brain")).toBeTruthy();
    expect(screen.getByText("Streamable HTTP")).toBeTruthy();
    expect(screen.getAllByText("29 sınırlı araç").length).toBeGreaterThan(0);
    expect(screen.getByText("yalnız 127.0.0.1")).toBeTruthy();
    expect(screen.getAllByText("http://127.0.0.1:8787/mcp").length).toBeGreaterThan(0);
    expect(await screen.findByText("Henüz oturum olayı görülmedi")).toBeTruthy();
  });

  it("yetenek ailelerini istendiğinde sayılarıyla listeler", async () => {
    renderSection();
    await ready();

    fireEvent.click(await screen.findByRole("button", { name: /Yetenek aileleri \(8\)/ }));
    expect(screen.getByText("Operasyonel okuma")).toBeTruthy();
    expect(screen.getByText("Güvenli yazma")).toBeTruthy();
    expect(screen.getByText("Dayanıklı yürütme")).toBeTruthy();
    expect(screen.getByText("11")).toBeTruthy();
  });

  it("iç katman kodlarını (H0…H7) kullanıcıya göstermez", async () => {
    const { container } = renderSection();
    await ready();

    // Aile kimlikleri backend'den gelir ama ekrana basılmaz: yüzey insan dili
    // etiketleri ve araç sayılarını gösterir. Katlanır bölümler açıldığında da
    // kod sızmaz.
    for (const name of [/Yetenek aileleri \(8\)/, /Gelişmiş ayarlar/, /Katmanlar: Hermes Skills/]) {
      fireEvent.click(await screen.findByRole("button", { name }));
    }
    expect(container.textContent).not.toMatch(/\bH[0-7]\b/);
  });

  it("MCP adresini kopyalanabilir sunar", async () => {
    renderSection();
    await ready();

    fireEvent.click((await screen.findAllByRole("button", { name: "MCP adresini kopyala" }))[0]!);
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith("http://127.0.0.1:8787/mcp"));
    expect(await screen.findByText("Kopyalandı.")).toBeTruthy();
  });

  it("istek düştüğünde ulaşılamıyor der ve YALNIZ o kartı bozar", async () => {
    agentFailed = true;
    renderSection();
    await ready();

    expect(await screen.findByText(/Agent bağlantısı durumu alınamadı/)).toBeTruthy();
    // Vault kartı kendi verisiyle çalışmaya devam eder (§40).
    expect(screen.getAllByText("Bağlı ve hazır").length).toBeGreaterThan(0);
  });

  it("uç yerel sınırda değilse bunu gizlemez", async () => {
    agentStatus = makeAgentStatus({ loopback: false });
    renderSection();
    await ready();

    expect((await screen.findAllByText("yerel sınırda değil")).length).toBeGreaterThan(0);
    expect(screen.getByText("yerel sınır dışında")).toBeTruthy();
  });

  it("hiçbir durumda 'Hermes bağlı' iddiasında bulunmaz", async () => {
    renderSection();
    await ready();

    expect(screen.queryByText(/Hermes bağlı/i)).toBeNull();
    expect(await screen.findByText(/forkOS, Hermes istemcisinin bağlı olup olmadığını doğrulayamaz/)).toBeTruthy();
  });

  it("oturum devamlılığı, başlangıç bağlamı ve kaynak devamlılığı tanılamalarını gösterir", async () => {
    renderSection();
    await ready();

    expect(await screen.findByText("Oturum devamlılığı")).toBeTruthy();
    expect(screen.getByText("Başlangıç bağlamı")).toBeTruthy();
    expect(screen.getByText("Kaynak devamlılığı")).toBeTruthy();
    expect(screen.getByText("Etkin kaynak yok")).toBeTruthy();
    expect(screen.getByText("Henüz oluşturulmadı")).toBeTruthy();
  });
});

describe("Hermes kartı", () => {
  it("bağlantı tarifini, güvenli ayarı ve doğrulanamaz olduğunu söyler", async () => {
    renderSection();
    await ready();

    fireEvent.click(await screen.findByRole("button", { name: /Gelişmiş ayarlar/ }));

    expect(screen.getAllByText(/trust: untrusted/).length).toBeGreaterThan(0);
    expect(screen.getByText(/url: "http:\/\/127\.0\.0\.1:8787\/mcp"/)).toBeTruthy();
    expect(screen.getByText(/supports_parallel_tool_calls: false/)).toBeTruthy();
    expect(screen.getByText(/forkOS doğrulayamaz/)).toBeTruthy();
    // forkOS tarafında trust açma/kapama düğmesi YOKTUR.
    expect(screen.queryByRole("button", { name: /trust/i })).toBeNull();
  });

  it("ayar örneğini kopyalanabilir sunar", async () => {
    renderSection();
    await ready();

    fireEvent.click(await screen.findByRole("button", { name: /Gelişmiş ayarlar/ }));
    fireEvent.click(screen.getByRole("button", { name: "Hermes ayar örneğini kopyala" }));

    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalled());
    const copied = String(
      (navigator.clipboard.writeText as unknown as { mock: { calls: string[][] } }).mock.calls[0]![0],
    );
    expect(copied).toContain("mcp_servers:");
    expect(copied).toContain("forkos-brain:");
    expect(copied).toContain("trust: untrusted");
  });

  it("Hermes Skills, agent hafızası ve Vault ayrımını açıklar; eşitleme düğmesi sunmaz", async () => {
    renderSection();
    await ready();

    fireEvent.click(await screen.findByRole("button", { name: /Katmanlar: Hermes Skills · Agent hafızası/ }));
    expect(screen.getByText(/NASIL kullanacağını öğrendiği prosedürler/)).toBeTruthy();
    expect(screen.getByText(/kalıcı insan bilgisi/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /eşitle|sync/i })).toBeNull();
  });
});

describe("f0rknbrain kartı", () => {
  it("sağlıklı durumda bağlı, okunabilir ve yazılabilir olduğunu söyler", async () => {
    renderSection();
    await ready();

    expect((await screen.findAllByText("Bağlı ve hazır")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("f0rknbrain").length).toBeGreaterThan(0);
    expect(screen.getByText("13 yönetilen not")).toBeTruthy();
    expect(screen.getByText("okunabilir")).toBeTruthy();
    expect(screen.getByText("yazılabilir")).toBeTruthy();
    expect(screen.getByText("0 çakışma")).toBeTruthy();
  });

  it("yapılandırılmamış durumu açıklayarak söyler", async () => {
    vaultStatus = makeVaultStatus({
      configured: false,
      available: false,
      readable: false,
      writable: false,
      vault_name: "",
      managed_files: 0,
      open_uri: null,
      inbox_uri: null,
      daily_uri: null,
    });
    renderSection();
    await ready();

    expect(await screen.findByText("Vault runtime'a bağlanmamış")).toBeTruthy();
    expect(screen.getByText(/kalıcı bilgi erişimi kullanılamaz/)).toBeTruthy();
  });

  it("erişilemeyen durumu yapılandırılmıştan ayırır", async () => {
    vaultStatus = makeVaultStatus({ available: false, readable: false, writable: false, diagnostic: "izin yok" });
    renderSection();
    await ready();

    expect(await screen.findByText("Yapılandırılmış ancak erişilemiyor")).toBeTruthy();
    expect(screen.getAllByText("izin yok").length).toBeGreaterThan(0);
  });

  it("salt okunur durumda ne çalışıp neyin çalışmadığını söyler", async () => {
    vaultStatus = makeVaultStatus({ writable: false });
    renderSection();
    await ready();

    expect(await screen.findByText("Erişilebilir ancak salt okunur")).toBeTruthy();
    expect(screen.getByText(/capture ve günlük not yazma çalışmaz/)).toBeTruthy();
  });

  it("kimlik çakışmasını dosya yollarıyla listeler", async () => {
    vaultStatus = makeVaultStatus({
      conflicts: 1,
      conflict_details: { "12345678-1234-1234-1234-123456789abc": ["a/Project A.md", "b/Project B.md"] },
    });
    renderSection();
    await ready();

    expect(await screen.findByText("1 çakışma")).toBeTruthy();
    expect(screen.getByText(/Aynı forkOS kimliği birden fazla Vault dosyasında bulunuyor/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Çakışan kayıtlar \(1\)/ }));
    expect(screen.getByText("a/Project A.md")).toBeTruthy();
    expect(screen.getByText("b/Project B.md")).toBeTruthy();
  });

  it("geçersiz dosyaları çakışmadan AYRI gösterir", async () => {
    vaultStatus = makeVaultStatus({ invalid_files: ["x/Bozuk.md"] });
    renderSection();
    await ready();

    expect(await screen.findByText("1 dosya geçerli forkOS metadata'sı taşımıyor.")).toBeTruthy();
    expect(screen.getByText(/Bu bir kimlik çakışması değildir/)).toBeTruthy();
    expect(screen.getByText("0 çakışma")).toBeTruthy();
  });

  it("Obsidian eylemlerini sunucudan gelen URI ile açar; olmayan eylemi göstermez", async () => {
    vaultStatus = makeVaultStatus({ daily_uri: null });
    renderSection();
    await ready();

    expect(screen.queryByRole("button", { name: /Bugünün Notunu Aç/ })).toBeNull();
    fireEvent.click(await screen.findByRole("button", { name: /Vault'u Aç/ }));
    expect(openObsidianSpy).toHaveBeenCalledWith("obsidian://open?vault=f0rknbrain");

    fireEvent.click(screen.getByRole("button", { name: /Inbox'u Aç/ }));
    expect(openObsidianSpy).toHaveBeenCalledWith("obsidian://open?vault=f0rknbrain&file=00%20Inbox");
  });

  it("indeks yenilemeyi yerel uca gönderir", async () => {
    renderSection();
    await ready();

    fireEvent.click(await screen.findByRole("button", { name: /İndeksi Yenile/ }));
    await waitFor(() =>
      expect(calls.some((call) => call.method === "POST" && call.path === "/api/obsidian/index/refresh")).toBe(true),
    );
    expect(await screen.findByText("Vault indeksi yenilendi.")).toBeTruthy();
  });

  it("Bilgi alanına bağlantı verir", async () => {
    renderSection();
    await ready();

    fireEvent.click(await screen.findByRole("button", { name: /Bilgi alanını aç/ }));
    expect(navigateSpy).toHaveBeenCalledWith("/notes");
  });

  it("Vault isteği düştüğünde yalnız o kartı bozar", async () => {
    vaultFailed = true;
    renderSection();
    await ready();

    expect(await screen.findByText(/Vault durumu alınamadı/)).toBeTruthy();
    expect(screen.getByText("forkos-brain")).toBeTruthy();
  });
});

describe("Yerel model kartı", () => {
  const setH4 = (h4: Record<string, unknown>) => {
    agentStatus = makeAgentStatus({ h4 });
  };

  it("kapalıyken bunu hata gibi değil, isteğe bağlı katman olarak anlatır", async () => {
    renderSection();
    await ready();

    expect((await screen.findAllByText("kapalı")).length).toBeGreaterThan(0);
    expect(screen.getByText(/isteğe bağlı yerel model/)).toBeTruthy();
    expect(screen.getByText(/Hermes'in sohbet modeli bundan bağımsızdır/)).toBeTruthy();
    expect(screen.getByText("yoklanmadı")).toBeTruthy();
  });

  it("yapılandırılmamış / sağlayıcı erişilemiyor / model eksik durumlarını ayırır", async () => {
    setH4({ enabled: true, state: "not_configured" });
    renderSection();
    await ready();
    expect((await screen.findAllByText("yapılandırılmadı")).length).toBeGreaterThan(0);

    cleanup();
    setH4({
      enabled: true,
      state: "provider_unreachable",
      reachable: false,
      small: { configured: true, available: false },
    });
    renderSection();
    await ready();
    expect((await screen.findAllByText("sağlayıcı erişilemiyor")).length).toBeGreaterThan(0);
    expect(screen.getByText("erişilemiyor")).toBeTruthy();

    cleanup();
    setH4({
      enabled: true,
      state: "model_missing",
      reachable: true,
      small: { configured: true, available: true },
      medium: { configured: true, available: false },
    });
    renderSection();
    await ready();
    expect((await screen.findAllByText("model eksik")).length).toBeGreaterThan(0);
    expect(screen.getByText("kurulu değil")).toBeTruthy();
  });

  it("hazır durumda sağlayıcıyı ve modelleri gösterir", async () => {
    setH4({
      enabled: true,
      configured: true,
      state: "ready",
      reachable: true,
      small: { configured: true, available: true },
      medium: { configured: true, available: true },
    });
    renderSection();
    await ready();

    expect(await screen.findByText("hazır")).toBeTruthy();
    expect(screen.getByText("ollama · loopback")).toBeTruthy();
    expect(screen.getByText("erişilebilir")).toBeTruthy();
    expect(screen.getAllByText("kurulu").length).toBe(2);
    // H4 açıkken de yapılandırmanın buradan değiştirilmediği yazılıdır.
    expect(screen.getByText(/buradan değiştirilmez/)).toBeTruthy();
  });
});

describe("Bekleyen kararlar özeti", () => {
  it("bekleyen karar yokken bunu nötr söyler", async () => {
    renderSection();
    await ready();

    expect(await screen.findByText("karar yok")).toBeTruthy();
    expect(screen.getByText("kayıt yok")).toBeTruthy();
  });

  it("aynı planın revizyonlarını TEK karar sayar", async () => {
    plans = [
      plan({ plan_row_id: 2, revision: "r2", is_current_revision: true }),
      plan({ plan_row_id: 1, revision: "r1", is_current_revision: false }),
      plan({ plan_row_id: 3, plan_id: "plan-2", state: "input_required" }),
    ];
    renderSection();
    await ready();

    expect(await screen.findByText("2 karar")).toBeTruthy();
  });

  it("kısmi sonucu başarı gibi göstermez, başarısızı ayırır", async () => {
    plans = [plan({ state: "partial", decision_required: false })];
    renderSection();
    await ready();
    expect(await screen.findByText("kısmi")).toBeTruthy();

    cleanup();
    plans = [plan({ state: "failed", decision_required: false, failure_code: "STEP_FAILED" })];
    renderSection();
    await ready();
    expect(await screen.findByText("başarısız")).toBeTruthy();
    expect(screen.queryByText("sonuçlanmış plan yok")).toBeNull();
  });

  it("onaylama/yürütme/reddetme eylemi SUNMAZ; karar yüzeyine yönlendirir", async () => {
    plans = [plan()];
    renderSection();
    await ready();

    expect(await screen.findByText("1 karar")).toBeTruthy();
    for (const label of ["Onayla", "Yürüt", "Reddet", "Onayla ve yürüt"]) {
      expect(screen.queryByRole("button", { name: label })).toBeNull();
    }

    fireEvent.click(screen.getByRole("button", { name: /Bekleyen kararları gör/ }));
    expect(navigateSpy).toHaveBeenCalledWith("/");
  });

  it("karar isteği düştüğünde yalnız o kartı bozar", async () => {
    plansFailed = true;
    renderSection();
    await ready();

    expect(await screen.findByText(/Karar özeti alınamadı/)).toBeTruthy();
    expect(screen.getAllByText("Bağlı ve hazır").length).toBeGreaterThan(0);
  });
});

describe("çevrimdışı davranış", () => {
  it("internet yokken yerel okuma yüzeyleri ve Obsidian eylemleri çalışır", async () => {
    online = false;
    Object.defineProperty(window.navigator, "onLine", { configurable: true, value: false });
    renderSection();
    await ready();

    // Agent bağlantısı, Vault durumu, yerel model ve karar özeti görünür kalır.
    expect(await screen.findByText("forkos-brain")).toBeTruthy();
    expect(screen.getAllByText("Bağlı ve hazır").length).toBeGreaterThan(0);
    expect(screen.getByText(/Hermes'in sohbet modeli bundan bağımsızdır/)).toBeTruthy();
    expect(screen.getByText("karar yok")).toBeTruthy();

    // Obsidian'ı açmak yerel bir istemci eylemidir: internet gerektirmez.
    fireEvent.click(screen.getByRole("button", { name: /Vault'u Aç/ }));
    expect(openObsidianSpy).toHaveBeenCalled();
  });
});
