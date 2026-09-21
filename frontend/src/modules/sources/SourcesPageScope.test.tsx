// @vitest-environment node
/**
 * `/sources` kapsam ayrımı: medya kapsamı YALNIZ çekim ilerlemesini ve parti
 * geçmişini gösterir. İş sınıfı, katalog ve kapsam matrisi kariyer/sistem
 * yüzeyine aittir; medya kapsamına sızmaz.
 *
 * (Bu test `modules/health/SourceHealthPageScope.test.tsx` idi; yüzey tek
 * uygulamaya taşınınca buraya geldi.)
 */
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SourcesPage } from "./SourcesPage";

type QueryOptions = { queryFn: () => unknown; queryKey: readonly unknown[] };

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  queries: [] as QueryOptions[],
  params: new URLSearchParams("scope=media"),
}));

vi.mock("@/app/router", () => ({
  navigate: vi.fn(),
  useHashRoute: () => ({ path: "/sources", params: harness.params }),
}));
vi.mock("@/core/api", () => ({
  api: { get: harness.apiGet, post: vi.fn() },
}));
vi.mock("@/lib/hooks", () => ({
  useInvalidate: () => vi.fn(),
  useOnline: () => true,
}));
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn(() => ({ isPending: false, mutate: vi.fn() })),
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    if (options.queryKey[0] === "source-sync-history") {
      return {
        data: [
          {
            id: "batch-1",
            created_at: "2026-08-23T10:00:00Z",
            started_at: "2026-08-23T10:00:00Z",
            finished_at: "2026-08-23T10:00:04Z",
            total_sources: 2,
            completed_sources: 2,
            ok_sources: 2,
            empty_sources: 0,
            error_sources: 0,
            items_found: 3,
          },
        ],
      };
    }
    if (options.queryKey[0] === "source-sync") {
      return { data: { active: null, last_completed: null, running: [], sources: [] } };
    }
    return { data: [] };
  }),
}));

describe("SourcesPage media scope", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.queries.length = 0;
    harness.params = new URLSearchParams("scope=media");
  });

  it("renders media history and calls scoped status/history endpoints", async () => {
    const markup = renderToStaticMarkup(<SourcesPage />);
    const status = harness.queries.find(
      (query) => query.queryKey[0] === "source-sync" && query.queryKey[1] === "media",
    );
    const history = harness.queries.find(
      (query) => query.queryKey[0] === "source-sync-history" && query.queryKey[1] === "media",
    );

    await status?.queryFn();
    await history?.queryFn();
    expect(harness.apiGet).toHaveBeenCalledWith("/sources/sync?scope=media");
    expect(harness.apiGet).toHaveBeenCalledWith("/sources/sync/history?scope=media");
    expect(markup).toContain("Medya Kaynak Durumu");
    expect(markup).toContain("+3 kayıt");
    expect(markup).not.toContain("Tümünü çek");
  });

  it("medya kapsamı iş kataloğunu, sınıf süzgecini ve kapsam matrisini göstermez", () => {
    const markup = renderToStaticMarkup(<SourcesPage />);
    expect(markup).not.toContain("Kritik + normal yenile");
    expect(markup).not.toContain("Kaynak kataloğu");
    expect(markup).not.toContain("Kaynak kapsamı");
    expect(markup).not.toContain("Duyuru");
    expect(markup).not.toContain("İş ilanı");
    // Kapsam sorgusu hiç çağrılmaz: medya yüzeyi kapsam/katalog çekmez.
    for (const query of harness.queries) {
      expect(["source-sync", "source-sync-history"]).toContain(query.queryKey[0]);
    }
  });
});
