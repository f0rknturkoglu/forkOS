import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const harness = vi.hoisted(() => ({
  get: vi.fn(),
  query: null as null | { queryFn: (context: { pageParam: number }) => unknown },
}));

vi.mock("@tanstack/react-query", () => ({
  useInfiniteQuery: vi.fn((options) => {
    harness.query = options;
    return {
      data: {
        pages: [
          {
            items: [],
            total: 0,
            offset: 0,
            limit: 60,
            // Sayaç yeni sorgu gelene kadar önceki veriyi korur; sahte 0/0 yok.
            section_counts: { jobs: 12, announcements: 7, trash: 2 },
            facets: { categories: { software: 8 } },
          },
        ],
      },
      isPending: false,
      isLoading: false,
      isError: false,
      isFetching: false,
      hasNextPage: false,
      isFetchingNextPage: false,
      refetch: vi.fn(),
      fetchNextPage: vi.fn(),
    };
  }),
  useMutation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useQuery: vi.fn(() => ({ data: [], isLoading: false })),
}));
vi.mock("@/core/api", () => ({
  api: { get: harness.get, patch: vi.fn(), post: vi.fn(), del: vi.fn() },
  qs: (params: Record<string, unknown>) => {
    const entries = Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== "");
    return entries.length ? `?${new URLSearchParams(entries.map(([key, value]) => [key, String(value)]))}` : "";
  },
}));
vi.mock("@/app/router", () => ({
  navigate: vi.fn(),
  useHashRoute: () => ({ params: new URLSearchParams() }),
}));
vi.mock("@/core/SaveToLibrary", () => ({ useSaveToLibrary: () => ({ save: vi.fn() }) }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/SyncProgress", () => ({ SyncProgress: () => null }));
vi.mock("./SourcePicker", () => ({ SourcePicker: () => null }));
vi.mock("./OpportunityDetail", () => ({ OpportunityDetail: () => null }));
vi.mock("./ApplicationsWorkspace", () => ({ ApplicationsWorkspace: () => null }));
vi.mock("./CareerWorkspace", () => ({ CareerWorkspace: () => null }));
vi.mock("./SourcesWorkspace", () => ({ SourcesWorkspace: () => null }));

import { OpportunityPage } from "./OpportunityPage";

describe("opportunity page workspaces", () => {
  beforeEach(() => {
    harness.get.mockReset();
    harness.query = null;
  });

  it("renders the five workspaces and uses the paginated browse endpoint", async () => {
    const html = renderToStaticMarkup(<OpportunityPage />);
    for (const label of ["İşler", "Başvurular", "Duyurular", "Kariyer", "Kaynaklar"]) {
      expect(html).toContain(label);
    }
    expect(html).not.toContain("İş alanı");
    await harness.query?.queryFn({ pageParam: 60 });
    expect(harness.get).toHaveBeenCalledWith(expect.stringContaining("/opportunities/browse?"));
    expect(harness.get).toHaveBeenCalledWith(expect.stringContaining("offset=60"));
    expect(harness.get).toHaveBeenCalledWith(expect.stringContaining("sort=score"));
  });

  it("keeps the compact score control on the surface without a full-width slider card", () => {
    const html = renderToStaticMarkup(<OpportunityPage />);
    expect(html).toContain("Skor:");
    expect(html).not.toContain("Minimum skor");
  });
});
