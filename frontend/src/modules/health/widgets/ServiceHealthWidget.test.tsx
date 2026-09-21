import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ServiceHealthWidget } from "./ServiceHealthWidget";

type QueryOptions = { queryKey: readonly unknown[]; queryFn: () => unknown };
type QueryState = { data?: unknown; isError?: boolean };

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  queries: [] as QueryOptions[],
  refetch: vi.fn(),
  state: {} as Record<string, QueryState>,
}));

vi.mock("@/core/api", () => ({ api: { get: harness.apiGet } }));
vi.mock("@tanstack/react-query", () => ({
  useQuery: (options: QueryOptions) => {
    harness.queries.push(options);
    const entry = harness.state[String(options.queryKey[0])] ?? {};
    return { data: entry.data, isError: entry.isError ?? false, refetch: harness.refetch };
  },
}));

const NOW = Date.now();
const iso = (hoursAgo: number) => new Date(NOW - hoursAgo * 3_600_000).toISOString();

/** Kırmızı ton, chip sınıfından okunur: durum metni kadar kesin bir kanıt. */
const DANGER = "bg-danger-surface";

function statsWith(status: string, heartbeatAt: string | null) {
  return { cpu_pct: 5, mem_total_kb: 1, uptime_s: 10, worker: { status, heartbeat_at: heartbeatAt } };
}

function backupWith(at: string | null, changesSinceBackup: boolean) {
  return {
    last_backup: at ? { at } : null,
    drive_folder_id: null,
    last_drive_upload: null,
    last_drive_error: null,
    changes_since_backup: changesSinceBackup,
  };
}

describe("ServiceHealthWidget — worker ve yedek dürüstlüğü", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.refetch.mockReset();
    harness.queries.length = 0;
    harness.state = {
      "system-stats": { data: statsWith("healthy", iso(0.02)) },
      "backup-status": { data: backupWith(iso(1), true) },
    };
  });

  it("saglikli worker + guncel yedek ok tonu tasir", () => {
    const markup = renderToStaticMarkup(<ServiceHealthWidget />);
    expect(markup).toContain("çalışıyor");
    expect(markup).toContain("güncel");
    expect(markup).not.toContain("durdu");
  });

  it("stale worker uyarisi gosterir", () => {
    harness.state["system-stats"] = { data: statsWith("stale", iso(0.5)) };
    const markup = renderToStaticMarkup(<ServiceHealthWidget />);
    expect(markup).toContain("durdu — arka plan işleri çalışmıyor");
    expect(markup).toContain(DANGER);
  });

  it("48 saatten eski yedek + bekleyen degisiklik uyarir", () => {
    harness.state["backup-status"] = { data: backupWith(iso(72), true) };
    const markup = renderToStaticMarkup(<ServiceHealthWidget />);
    expect(markup).toContain("eski");
  });

  it("eski ama degisiklik yoksa yedek UYARMAZ", () => {
    // Zamanlanmis yedek anlamli degisiklik yoksa bilerek atlanir; eski tarih
    // tek basina sorun degildir.
    harness.state["backup-status"] = { data: backupWith(iso(72), false) };
    const markup = renderToStaticMarkup(<ServiceHealthWidget />);
    expect(markup).toContain("değişiklik yok");
    expect(markup).not.toContain("eski —");
  });

  it("bilerek kapatilmis worker'i KIRMIZI gostermez, 'kapali' der", () => {
    harness.state["system-stats"] = { data: statsWith("disabled", null) };
    const markup = renderToStaticMarkup(<ServiceHealthWidget />);
    expect(markup).toContain("kapalı");
    expect(markup).toContain("bilerek kapalı");
    expect(markup).not.toContain("durdu");
    expect(markup).not.toContain(DANGER);
  });

  it("worker durumunu API'den ogrenemezse 'bilinmiyor' der, 'kapali' DEMEZ", () => {
    // `unknown`: worker acik ama kayitli kalp atisi yok — bu bir hata degil.
    harness.state["system-stats"] = { data: statsWith("unknown", null) };
    const markup = renderToStaticMarkup(<ServiceHealthWidget />);
    expect(markup).toContain("bilinmiyor");
    expect(markup).toContain("kalp atışı");
    expect(markup).not.toContain("kapalı");
    expect(markup).not.toContain(DANGER);
  });

  it("worker sorgusu dustugunde yalniz o satir 'alinamadi' der", () => {
    harness.state["system-stats"] = { isError: true };
    const markup = renderToStaticMarkup(<ServiceHealthWidget />);
    expect(markup).toContain("Worker durumu alınamadı");
    expect(markup).not.toContain("çalışıyor");
    // Yedek satiri okunmaya devam eder.
    expect(markup).toContain("güncel");
  });

  it("yedek durumu okunamazsa 'henuz yedek yok' DEMEZ", () => {
    harness.state["backup-status"] = { isError: true };
    const markup = renderToStaticMarkup(<ServiceHealthWidget />);
    expect(markup).toContain("Yedek durumu alınamadı");
    expect(markup).toContain("durum bilinmiyor");
    expect(markup).not.toContain("henüz yedek yok");
  });
});
