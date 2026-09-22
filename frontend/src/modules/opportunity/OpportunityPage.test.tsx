// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/core/ui";

const harness = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  del: vi.fn(),
  items: [] as Array<Record<string, unknown>>,
  confirm: vi.fn(async () => true),
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
            items: harness.items,
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
  useMutation: vi.fn((options) => ({
    mutate: (variables: unknown) => {
      Promise.resolve(options.mutationFn(variables)).then((result) => options.onSuccess?.(result, variables));
    },
    isPending: false,
  })),
  useQuery: vi.fn(() => ({ data: [], isLoading: false })),
}));
vi.mock("@/core/api", () => ({
  api: { get: harness.get, patch: vi.fn(), post: harness.post, del: harness.del },
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
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/core/dialog", () => ({ confirmDialog: harness.confirm }));
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
    harness.post.mockReset().mockResolvedValue({});
    harness.del.mockReset().mockResolvedValue({});
    harness.confirm.mockReset().mockResolvedValue(true);
    harness.items = [];
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

  it("kısa liste eylemi domain durumunu değiştirir; çöp onaysız ve toast ile geri alınır", async () => {
    harness.items = [
      {
        id: "1",
        title: "Frontend Developer",
        kind: "job",
        category: "software",
        organization: "forkOS",
        url: "https://example.com/job",
        status: "discovered",
        allowed_transitions: ["shortlisted"],
        priority: 2,
        found_at: "2026-08-23T10:00:00Z",
        published_at: null,
        deadline_at: null,
        applied_at: null,
        location: "İstanbul",
        remote: "remote",
        compensation: null,
        source: "test",
        external_id: null,
        raw: {},
        score: 82,
        score_reasons: null,
        notes: null,
        trashed_at: null,
        trashed_from_status: null,
        country: null,
        region: null,
        follow_up_at: null,
        rejection_reason: null,
      },
    ];
    render(
      <ToastProvider>
        <OpportunityPage />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Kısa Listeye Al" }));
    await waitFor(() =>
      expect(harness.post).toHaveBeenCalledWith("/opportunities/1/transition", { to: "shortlisted" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Çöpe at" }));
    await waitFor(() => expect(harness.post).toHaveBeenCalledWith("/opportunities/1/trash"));
    expect(harness.confirm).not.toHaveBeenCalled();
    fireEvent.click(await screen.findByRole("button", { name: "Geri al" }));
    await waitFor(() => expect(harness.post).toHaveBeenCalledWith("/opportunities/1/restore"));
  });

  it("kalıcı silme için onay ister", async () => {
    harness.params = new URLSearchParams("section=trash");
    harness.items = [
      {
        id: "2",
        title: "Eski ilan",
        kind: "job",
        category: "software",
        organization: "forkOS",
        url: "https://example.com/job",
        status: "discovered",
        allowed_transitions: [],
        priority: 2,
        found_at: "2026-08-23T10:00:00Z",
        published_at: null,
        deadline_at: null,
        applied_at: null,
        location: "İstanbul",
        remote: "remote",
        compensation: null,
        source: "test",
        external_id: null,
        raw: {},
        score: 82,
        score_reasons: null,
        notes: null,
        trashed_at: "2026-08-24T10:00:00Z",
        trashed_from_status: "discovered",
        country: null,
        region: null,
        follow_up_at: null,
        rejection_reason: null,
      },
    ];
    render(<OpportunityPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Kalıcı sil" }));
    await waitFor(() => expect(harness.confirm).toHaveBeenCalledOnce());
    await waitFor(() => expect(harness.del).toHaveBeenCalledWith("/opportunities/2"));
  });
});
