import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ServiceHealthWidget } from "./ServiceHealthWidget";

type QueryOptions = { queryKey: readonly unknown[]; queryFn: () => unknown };

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  stats: {} as Record<string, unknown>,
  backup: {} as Record<string, unknown>,
  queries: [] as QueryOptions[],
}));

vi.mock("@/core/api", () => ({ api: { get: harness.apiGet } }));
vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    const key = String(options.queryKey[0]);
    return { data: key === "system-stats" ? harness.stats : harness.backup };
  }),
}));

describe("ServiceHealthWidget (Faz 26)", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.queries.length = 0;
    harness.stats = {
      worker: { status: "healthy", heartbeat_at: new Date().toISOString() },
      cpu_pct: 5,
      mem_total_kb: 1,
      uptime_s: 10,
    };
    harness.backup = {
      last_backup: { at: new Date().toISOString() },
      drive_folder_id: null,
      last_drive_upload: null,
      last_drive_error: null,
      changes_since_backup: true,
    };
  });

  it("saglikli worker + guncel yedek ok tonu tasir", () => {
    const markup = renderToStaticMarkup(<ServiceHealthWidget />);
    expect(markup).toContain("çalışıyor");
    expect(markup).toContain("güncel");
    expect(markup).not.toContain("durdu");
  });

  it("stale worker uyarisi gosterir", () => {
    harness.stats = { worker: { status: "stale", heartbeat_at: new Date(Date.now() - 10 * 60_000).toISOString() } };
    const markup = renderToStaticMarkup(<ServiceHealthWidget />);
    expect(markup).toContain("durdu — arka plan işleri çalışmıyor");
  });

  it("48 saatten eski yedek + bekleyen degisiklik uyarir", () => {
    harness.backup = {
      last_backup: { at: new Date(Date.now() - 72 * 3_600_000).toISOString() },
      drive_folder_id: null,
      last_drive_upload: null,
      last_drive_error: null,
      changes_since_backup: true,
    };
    const markup = renderToStaticMarkup(<ServiceHealthWidget />);
    expect(markup).toContain("eski");
  });

  it("eski ama degisiklik yoksa yedek UYARMAZ", () => {
    // Zamanlanmis yedek anlamli degisiklik yoksa bilerek atlanir; eski tarih
    // tek basina sorun degildir.
    harness.backup = {
      last_backup: { at: new Date(Date.now() - 72 * 3_600_000).toISOString() },
      drive_folder_id: null,
      last_drive_upload: null,
      last_drive_error: null,
      changes_since_backup: false,
    };
    const markup = renderToStaticMarkup(<ServiceHealthWidget />);
    expect(markup).toContain("değişiklik yok");
    expect(markup).not.toContain("eski —");
  });
});
