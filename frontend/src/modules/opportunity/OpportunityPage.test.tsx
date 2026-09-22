// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const harness = vi.hoisted(() => ({
  get: vi.fn(),
  params: new URLSearchParams(),
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
  useHashRoute: () => ({ params: harness.params }),
}));
vi.mock("@/core/SaveToLibrary", () => ({ useSaveToLibrary: () => ({ save: vi.fn() }) }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/SyncProgress", () => ({ SyncProgress: () => null }));
vi.mock("@/modules/sources/SourcePicker", () => ({ SourcePicker: () => null }));
vi.mock("./OpportunityDetail", () => ({
  OpportunityDetail: ({ mode = "drawer" }: { mode?: string }) => (
    <div data-testid="opportunity-detail" data-mode={mode} />
  ),
}));
vi.mock("./ApplicationsWorkspace", () => ({ ApplicationsWorkspace: () => null }));
vi.mock("./CareerWorkspace", () => ({ CareerWorkspace: () => null }));
vi.mock("@/modules/sources/SourcesWorkspace", () => ({ SourcesWorkspace: () => null }));

import { OpportunityPage } from "./OpportunityPage";

describe("opportunity page workspaces", () => {
  beforeEach(() => {
    harness.get.mockReset();
    harness.params = new URLSearchParams();
    harness.query = null;
    const storage = new Map<string, string>();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => {
          storage.set(key, value);
        },
        removeItem: (key: string) => {
          storage.delete(key);
        },
        clear: () => storage.clear(),
      },
    });
  });
  afterEach(cleanup);

  it("renders the five workspaces and uses the paginated browse endpoint", async () => {
    const html = renderToStaticMarkup(<OpportunityPage />);
    // Sekme KIMLIKLERI sozlesme (?tab=), etiketler urun dili.
    for (const label of ["Keşfet", "Başvurular", "Duyurular", "Profil", "Kaynaklar"]) {
      expect(html).toContain(label);
    }
    expect(html).not.toContain("İş alanı");
    expect(html).not.toContain("İşler");
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

  it("kayıtlı görünüm seçicisi sunmaz ve eski ?saved bağlantısını yok sayar", () => {
    harness.params = new URLSearchParams("saved=bilinmeyen");
    const html = renderToStaticMarkup(<OpportunityPage />);
    // Kariyer yüzeyinde saved-view affordance'ı kalmadı.
    expect(html).not.toContain("Kayıtlı görünümler");
    expect(html).not.toContain("Görünümler");
    // Bilinmeyen `?saved=` çökmeye yol açmaz: çalışma alanı normal çizilir.
    expect(html).toContain("Keşfet");
  });

  it("focus bağlantısını geniş ekranda inline inspector olarak açar", async () => {
    harness.params = new URLSearchParams("focus=opp-1");
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: (query: string) => ({
        matches: query.includes("1280"),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    });
    render(<OpportunityPage />);
    expect((await screen.findByTestId("opportunity-detail")).getAttribute("data-mode")).toBe("inline");
  });

  it("focus bağlantısını dar ekranda drawer olarak açar", async () => {
    harness.params = new URLSearchParams("focus=opp-1");
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: () => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }),
    });
    render(<OpportunityPage />);
    expect((await screen.findByTestId("opportunity-detail")).getAttribute("data-mode")).toBe("drawer");
  });
});
