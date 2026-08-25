import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HealthPage } from "./HealthPage";

type MutationOptions = {
  mutationFn?: (...args: unknown[]) => unknown;
  onSuccess?: (...args: unknown[]) => void;
};
type QueryOptions = { queryFn: () => unknown; queryKey: readonly unknown[] };

const harness = vi.hoisted(() => ({
  apiDel: vi.fn(),
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  apiUpload: vi.fn(),
  invalidate: vi.fn(),
  mutations: [] as MutationOptions[],
  queries: [] as QueryOptions[],
  queryData: {} as Record<string, unknown>,
  stateCursor: 0,
  stateValues: [] as unknown[],
}));

vi.mock("react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react")>();
  return {
    ...actual,
    useState: (initial: unknown | (() => unknown)) => {
      const index = harness.stateCursor++;
      if (!(index in harness.stateValues)) {
        harness.stateValues[index] = typeof initial === "function" ? initial() : initial;
      }
      return [
        harness.stateValues[index],
        (value: unknown) => {
          harness.stateValues[index] = value;
        },
      ];
    },
  };
});
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
vi.mock("@/lib/hooks", () => ({
  useOnline: () => true,
}));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn((options: MutationOptions) => {
    harness.mutations.push(options);
    return { isPending: false, mutate: vi.fn() };
  }),
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    const key = String(options.queryKey[0]);
    return { data: key in harness.queryData ? harness.queryData[key] : undefined, isLoading: false };
  }),
}));

describe("health dashboard flow", () => {
  beforeEach(() => {
    harness.apiDel.mockReset();
    harness.apiGet.mockReset();
    harness.apiPatch.mockReset();
    harness.apiPost.mockReset();
    harness.apiUpload.mockReset();
    harness.invalidate.mockReset();
    harness.mutations.length = 0;
    harness.queries.length = 0;
    harness.queryData = {};
    harness.stateCursor = 0;
    harness.stateValues = [];
  });

  it("renders source, rss and backup widgets from their queries with the right GET endpoints", async () => {
    harness.queryData = {
      feeds: [
        {
          id: "f1",
          title: "Teknoloji Blogu",
          url: "https://example.com/rss",
          active: true,
          error_count: 2,
          last_status: "ok",
          last_fetched_at: "2026-01-01T00:00:00.000Z",
        },
      ],
      "rss-stats": { feeds: 3, active_feeds: 2, failing_feeds: 1, unread: 4 },
      "backup-status": {
        drive_folder_id: null,
        last_backup: {
          file: "yedek-2026-08-26.gz",
          size: 2048,
          at: "2026-08-26T03:00:00.000Z",
          counts: { entities: 120, events: 340, modules: {} },
        },
        next_backup_scheduled: "03:00",
        retention_days: 14,
        last_drive_upload: null,
        last_drive_error: null,
      },
    };
    const markup = renderToStaticMarkup(<HealthPage />);

    expect(markup).toContain("Kaynak Sağlığı");
    expect(markup).toContain("RSS Sağlığı");
    expect(markup).toContain("Teknoloji Blogu");
    expect(markup).toContain("2 hata");
    expect(markup).toContain("Yedekleme");
    expect(markup).toContain("yedek-2026-08-26.gz");

    const sources = harness.queries.find((query) => query.queryKey[0] === "sources");
    const feeds = harness.queries.find((query) => query.queryKey[0] === "feeds");
    const backup = harness.queries.find((query) => query.queryKey[0] === "backup-status");
    await sources?.queryFn();
    await feeds?.queryFn();
    await backup?.queryFn();
    expect(harness.apiGet).toHaveBeenCalledWith("/sources/health?limit=2000");
    expect(harness.apiGet).toHaveBeenCalledWith("/rss/feeds");
    expect(harness.apiGet).toHaveBeenCalledWith("/backup/status");
  });

  it("refreshes all rss feeds with the right API call and rss.write invalidation", () => {
    harness.apiPost.mockResolvedValue({ started: 3 });
    renderToStaticMarkup(<HealthPage />);

    const refreshAll = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.();
      return harness.apiPost.mock.calls.some(([url]) => url === "/rss/refresh-all");
    });
    expect(refreshAll).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/rss/refresh-all");
    refreshAll?.onSuccess?.({ started: 3 });
    expect(harness.invalidate).toHaveBeenCalledWith("rss.write");
  });

  it("refreshes a single feed and runs an immediate backup with backup.write invalidation", () => {
    harness.queryData = {
      feeds: [
        {
          id: "f1",
          title: "Teknoloji Blogu",
          url: "https://example.com/rss",
          active: true,
          error_count: 2,
          last_status: "ok",
          last_fetched_at: "2026-01-01T00:00:00.000Z",
        },
      ],
    };
    harness.apiPost.mockResolvedValue({ path: "backup-2026-08-26.gz", size: 2048 });
    renderToStaticMarkup(<HealthPage />);

    const refreshOne = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.("f1");
      return harness.apiPost.mock.calls.some(([url]) => url === "/rss/feeds/f1/refresh");
    });
    expect(refreshOne).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/rss/feeds/f1/refresh");
    refreshOne?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("rss.write");

    harness.invalidate.mockClear();
    const runNow = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.();
      return harness.apiPost.mock.calls.some(([url]) => url === "/backup");
    });
    expect(runNow).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/backup");
    runNow?.onSuccess?.({ path: "backup-2026-08-26.gz", size: 2048 });
    expect(harness.invalidate).toHaveBeenCalledWith("backup.write");
  });
});
