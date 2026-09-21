import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type * as UiKit from "@/core/ui";
import type { SourceCoverageRow } from "@/core/types";
import { HealthPage } from "./HealthPage";

type MutationOptions = { mutationFn?: (...args: unknown[]) => unknown; onSuccess?: (...args: unknown[]) => void };
type QueryOptions = { queryKey: readonly unknown[]; queryFn: () => unknown };
type QueryState = { data?: unknown; isError?: boolean; isLoading?: boolean };

const harness = vi.hoisted(() => ({
  apiDel: vi.fn(),
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  apiUpload: vi.fn(),
  invalidate: vi.fn(),
  mutations: [] as MutationOptions[],
  queries: [] as QueryOptions[],
  refetch: vi.fn(),
  state: {} as Record<string, QueryState>,
  online: true,
  toasts: [] as { message: string }[],
}));

vi.mock("@/core/api", () => ({
  api: {
    del: harness.apiDel,
    get: harness.apiGet,
    patch: harness.apiPatch,
    post: harness.apiPost,
    upload: harness.apiUpload,
  },
  qs: (params: Record<string, string | number | boolean | undefined | null>) => {
    const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
    return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
  },
}));
vi.mock("@/lib/hooks", () => ({ useOnline: () => harness.online }));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: (...events: string[]) => harness.invalidate(...events) }));
vi.mock("@tanstack/react-query", () => ({
  useMutation: (options: MutationOptions) => {
    harness.mutations.push(options);
    return { isPending: false, mutate: vi.fn() };
  },
  useQuery: (options: QueryOptions) => {
    harness.queries.push(options);
    const entry = harness.state[String(options.queryKey[0])] ?? {};
    const isError = entry.isError ?? false;
    return {
      data: entry.data,
      isError,
      // Gerçek TanStack gibi: veri yokken ve hata yokken sorgu yükleniyordur.
      isLoading: entry.isLoading ?? (entry.data === undefined && !isError),
      refetch: harness.refetch,
    };
  },
}));
/**
 * Kopyalanan tanılama paketi DOM'a yazılır: "Teşhisi kopyala" düğmesinin
 * gerçekten neyi kopyaladığı böyle doğrulanır (pano API'si çağrılmaz).
 * Bildirim metinleri de yakalanır: bir eylem yapmadığı bir şeyi iddia etmemeli.
 */
vi.mock("@/core/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof UiKit>();
  return {
    ...actual,
    CopyButton: ({ text, label }: { text: string; label?: string }) => (
      <span data-diagnostics="">{`[${label}]${text}`}</span>
    ),
    useToast: () => ({
      push: (message: string) => {
        harness.toasts.push({ message });
      },
    }),
  };
});

const NOW = Date.now();
const iso = (hoursAgo: number) => new Date(NOW - hoursAgo * 3_600_000).toISOString();

function coverageRow(overrides: Partial<SourceCoverageRow> = {}): SourceCoverageRow {
  return {
    source: "jobhunter:greenhouse:adyen",
    kind: "job",
    class: "critical",
    category: "jobs",
    official: true,
    url: "https://example.com/jobs",
    parser_version: "v3",
    last_status: "ok",
    last_run_at: iso(1),
    last_success_at: iso(1),
    last_new_content_at: iso(4),
    avg_publish_interval_days: 2,
    consecutive_empty: 0,
    last_error: null,
    last_error_kind: null,
    circuit_open: false,
    consecutive_failures: 0,
    tracked: true,
    ...overrides,
  };
}

/** Sağlıklı ama gerçekçi varsayılan: her sorgu okunabilir bir yanıt verir. */
function healthyState(): Record<string, QueryState> {
  const rows = Array.from({ length: 42 }, (_, index) => coverageRow({ source: `jobhunter:greenhouse:s${index}` }));
  return {
    "system-stats": {
      data: {
        cpu_pct: 4,
        load: [0.4],
        cpu_count: 8,
        mem_total_kb: 16_000_000,
        mem_available_kb: 9_000_000,
        disk: { total: 500 * 1024 ** 3, free: 120 * 1024 ** 3, path: "/" },
        uptime_s: 3600,
        worker: { status: "healthy", heartbeat_at: iso(0.05) },
      },
    },
    sources: {
      data: [
        { source: "jobhunter:greenhouse:adyen", status: "ok", started_at: iso(1), error: null, finished_at: iso(0.9) },
      ],
    },
    "source-coverage": { data: rows },
    feeds: {
      data: [
        {
          id: "f1",
          title: "Teknoloji Blogu",
          url: "https://example.com/rss",
          active: true,
          error_count: 0,
          last_status: "ok",
          last_fetched_at: iso(1),
        },
      ],
    },
    "rss-stats": { data: { feeds: 1, active_feeds: 1, failing_feeds: 0, unread: 3, today: 0, saved: 0 } },
    "backup-status": {
      data: {
        drive_folder_id: null,
        last_backup: {
          file: "lifeos-2026-09-22.json.gz",
          size: 2048,
          at: iso(3),
          counts: { entities: 120, events: 340, modules: {} },
        },
        last_drive_upload: null,
        last_drive_error: null,
        next_backup_scheduled: "03:00",
        changes_since_backup: false,
        retention_days: 14,
        backup_dir: "/app/backups",
        includes: [],
      },
    },
    "agent-status": {
      data: {
        brain: {
          server_name: "forkos-brain",
          endpoint: "http://127.0.0.1:8765/mcp",
          transport: "streamable_http",
          loopback_only: true,
          tool_count: 28,
          families: [],
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
      },
    },
    "vault-status": {
      data: {
        configured: true,
        available: true,
        writable: true,
        readable: true,
        vault_name: "f0rknbrain",
        managed_files: 12,
        conflicts: 0,
        conflict_details: {},
        diagnostic: null,
        open_uri: null,
        inbox_uri: null,
        daily_uri: null,
      },
    },
    "proactivity-status": { data: { enabled: true } },
    "execution-plans": { data: [] },
    settings: { data: {} },
  };
}

function render(state: Record<string, QueryState>) {
  harness.state = state;
  return renderToStaticMarkup(<HealthPage />);
}

/** Kopyalanan paketin metni (mock'lanan düğme DOM'a yazar). */
function bundleOf(markup: string): string {
  const match = /\[Teşhisi kopyala\]([\s\S]*?)<\/span>/.exec(markup);
  return match?.[1] ?? "";
}

/** "Genel bakış" başlığındaki genel durum çipi (tek doğruluk kaynağı). */
function overallChip(markup: string): string {
  const match = /okunur<\/span><span class="[^"]*">([^<]*)<\/span>/.exec(markup);
  return match?.[1] ?? "";
}

/** Tanılama paketi çıkarılmış yüzey: kullanıcının gördüğü metin. */
function uiOnly(markup: string): string {
  return markup.replace(/<span data-diagnostics="">[\s\S]*?<\/span>/, "");
}

describe("Sistem Durumu — bilgi mimarisi", () => {
  beforeEach(() => {
    harness.apiDel.mockReset();
    harness.apiGet.mockReset();
    harness.apiPatch.mockReset();
    harness.apiPost.mockReset();
    harness.apiUpload.mockReset();
    harness.invalidate.mockReset();
    harness.refetch.mockReset();
    harness.mutations.length = 0;
    harness.queries.length = 0;
  });

  it("üç anlamsal grubu çizer ve sağlıklı envanteri tek satırda özetler", () => {
    const markup = render(healthyState());

    expect(markup).toContain("Genel bakış");
    expect(markup).toContain("İlgi gerekenler");
    expect(markup).toContain("Ayrıntılı sağlık");
    // Sağlıklı envanter SAYILIR, listelenmez: 42 kaynağın adı sayfada geçmez.
    expect(markup).toContain("42 sağlıklı");
    expect(markup).not.toContain("greenhouse:s17");
    // Genel durum betimleyicidir; skor/yüzde yok.
    expect(overallChip(markup)).toBe("Sağlıklı");
    expect(uiOnly(markup)).not.toContain("%");
    // Hiçbir kalem ilgi istemiyor: tek sakin satır.
    expect(markup).toContain("İlgi gereken bir şey yok");
  });

  it("bir alt sistem sorgusu düştüğünde genel durum 'Sağlıklı' DEMEZ", () => {
    const state = healthyState();
    state["backup-status"] = { isError: true };
    const markup = render(state);

    expect(overallChip(markup)).toBe("Durum kısmen bilinmiyor");
    // Yedek satırı "sorun yok" değil "bilinmiyor" der; diğer kalemler okunur.
    expect(markup).toContain("Yedek durumu alınamadı");
    expect(markup).toContain("42 sağlıklı");
    // Paket, düşen bölümü ATLAMAZ: "unknown — request failed" olarak yazar.
    expect(bundleOf(markup)).toContain("backup/status: unknown — request failed");
  });

  it("hiçbir sorgu yüklenmeden yeşil cümle kurmaz (yükleniyor iskeleti)", () => {
    const state: Record<string, QueryState> = {};
    const markup = render(state);

    expect(overallChip(markup)).toBe("Durum kısmen bilinmiyor");
    // Sıfır uydurulmaz: yükleme "…" ile gösterilir.
    expect(markup).toContain("…");
  });

  it("gerçek bir sorun varsa 'İlgi gerekiyor' der ve nedeni yazar", () => {
    const state = healthyState();
    state["source-coverage"] = {
      data: [
        ...Array.from({ length: 41 }, (_, index) => coverageRow({ source: `jobhunter:greenhouse:s${index}` })),
        coverageRow({
          source: "jobhunter:greenhouse:broken",
          last_status: "error",
          last_error_kind: "http_429",
          last_error: "429 too many requests",
          circuit_open: true,
          consecutive_failures: 4,
        }),
      ],
    };
    const markup = render(state);

    expect(overallChip(markup)).toBe("İlgi gerekiyor");
    expect(markup).toContain("41 sağlıklı · 1 ilgi istiyor");
    expect(markup).toContain("devre açık");
  });

  it("H6 kapalıyken nötr söyler ve Hermes iddiası kurmaz", () => {
    const state = healthyState();
    state["proactivity-status"] = { data: { enabled: false } };
    const markup = render(state);

    expect(markup).toContain("H6 · proaktivite");
    expect(markup).toContain("kapalı");
    expect(markup).toContain("Kapalı olması hata değil");
    expect(markup).not.toContain("Hermes bağlı");
    expect(markup).toContain("Hermes istemcisinin bağlı olduğunu doğrulayamaz");
  });

  it("worker kapalıyken kırmızı göstermez; okunamayan worker da kırmızı değildir", () => {
    const disabled = healthyState();
    disabled["system-stats"] = {
      data: {
        cpu_pct: null,
        load: [],
        cpu_count: 4,
        mem_total_kb: null,
        mem_available_kb: null,
        disk: null,
        uptime_s: 60,
        worker: { status: "disabled", heartbeat_at: null },
      },
    };
    const disabledMarkup = render(disabled);
    expect(disabledMarkup).toContain("kapalı");
    expect(disabledMarkup).not.toContain("durdu");

    const broken = healthyState();
    broken["system-stats"] = { isError: true };
    const brokenMarkup = render(broken);
    expect(brokenMarkup).toContain("Worker durumu alınamadı");
    expect(brokenMarkup).not.toContain("çalışıyor");
  });

  it("paylaşılan uçları okur ve tanılama paketini sır/yol sızdırmadan üretir", async () => {
    const state = healthyState();
    const markup = render(state);

    // Her sorgu fonksiyonu GERÇEKTEN çağrılır: eksik bir import/yanlış yol
    // statik render'da görünmez (canlıda ReferenceError olurdu).
    harness.apiGet.mockResolvedValue([]);
    for (const query of harness.queries) {
      await expect(query.queryFn()).resolves.not.toThrow();
    }

    expect(harness.apiGet).toHaveBeenCalledWith("/sources/coverage");
    expect(harness.apiGet).toHaveBeenCalledWith("/agent/status");
    expect(harness.apiGet).toHaveBeenCalledWith("/obsidian/status");
    expect(harness.apiGet).toHaveBeenCalledWith("/backup/status");
    expect(harness.apiGet).toHaveBeenCalledWith("/sources/health?limit=2000");
    expect(harness.apiGet).toHaveBeenCalledWith("/system/stats");
    expect(harness.apiGet).toHaveBeenCalledWith("/rss/feeds");
    expect(harness.apiGet).toHaveBeenCalledWith("/rss/stats");
    expect(harness.apiGet).toHaveBeenCalledWith("/proactivity/status");
    expect(harness.apiGet).toHaveBeenCalledWith("/execution/plans?limit=20");

    const bundle = bundleOf(markup);
    expect(bundle).toContain("# forkOS System Diagnostics");
    expect(bundle).toContain("Route: Sistem Durumu (#/health)");
    expect(bundle).toContain("## Sources");
    expect(bundle).toContain("## Brain Interface");
    expect(bundle).toContain("MCP: forkos-brain");
    expect(bundle).toContain("H6: açık");
    expect(bundle).toContain("- none");
    expect(bundle).not.toContain("/app/backups");
    expect(bundle).not.toContain("/Users/");
  });

  it("'Şimdi yedekle' YEREL bir işlemdir: çevrimdışıyken kapatılmaz", () => {
    harness.online = false;
    const markup = render(healthyState());
    const button = [...markup.matchAll(/<button[^>]*>[\s\S]*?<\/button>/g)]
      .map((match) => match[0])
      .find((html) => html.includes("Şimdi yedekle"));
    expect(button).toBeDefined();
    expect(button).not.toContain("disabled");
    harness.online = true;
  });

  it("yedek bildirimi Drive yüklemesini iddia etmez", () => {
    harness.apiPost.mockResolvedValue({ path: "backup-2026-09-22.json.gz", size: 2048 });
    render(healthyState());

    const runNow = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.();
      return harness.apiPost.mock.calls.some(([url]) => url === "/backup");
    });
    harness.toasts.length = 0;
    runNow?.onSuccess?.({ path: "backup-2026-09-22.json.gz", size: 2048 });
    // Drive yüklemesi AYRI bir satırdır: yerel yedek başarısı onu garanti etmez.
    expect(harness.toasts[0]?.message).toContain("Yedek alındı");
    expect(harness.toasts[0]?.message).not.toContain("Drive");
  });

  it("yedekleme ve RSS mutasyonları doğru uçlara gider", () => {
    harness.apiPost.mockResolvedValue({ path: "backup-2026-09-22.json.gz", size: 2048 });
    render(healthyState());

    const refreshAll = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.();
      return harness.apiPost.mock.calls.some(([url]) => url === "/rss/refresh-all");
    });
    expect(refreshAll).toBeDefined();
    refreshAll?.onSuccess?.({ started: 3 });
    expect(harness.invalidate).toHaveBeenCalledWith("rss.write");

    const runNow = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.();
      return harness.apiPost.mock.calls.some(([url]) => url === "/backup");
    });
    expect(runNow).toBeDefined();
    runNow?.onSuccess?.({ path: "backup-2026-09-22.json.gz", size: 2048 });
    expect(harness.invalidate).toHaveBeenCalledWith("backup.write");
  });
});
