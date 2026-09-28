// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const harness = vi.hoisted(() => ({
  get: vi.fn(),
  query: null as null | { queryFn: (context: { pageParam: number }) => unknown },
  page: {
    items: [] as unknown[],
    total: 0,
    offset: 0,
    limit: 60,
    section_counts: { jobs: 12, announcements: 7, trash: 3 },
    facets: {} as Record<string, Record<string, number>>,
  },
}));

vi.mock("@tanstack/react-query", () => ({
  useInfiniteQuery: vi.fn((options) => {
    harness.query = options;
    return {
      data: { pages: [harness.page] },
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
vi.mock("@/modules/sources/SourcePicker", () => ({ SourcePicker: () => null }));
vi.mock("./OpportunityDetail", () => ({ OpportunityDetail: () => null }));
vi.mock("./ApplicationsWorkspace", () => ({ ApplicationsWorkspace: () => null }));
vi.mock("./CareerWorkspace", () => ({ CareerWorkspace: () => null }));
vi.mock("@/modules/sources/SourcesWorkspace", () => ({ SourcesWorkspace: () => null }));

import { OpportunityPage } from "./OpportunityPage";

// jsdom bu kurulumda localStorage sağlamıyor; görünüm tercihi oradan okunur.
vi.hoisted(() => {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => store.set(key, value),
      removeItem: (key: string) => store.delete(key),
      clear: () => store.clear(),
    },
  });
});

/** Debounce sonrası API'ye gidecek sorgu URL'i (sahte obje gerçek queryFn'i saklar). */
async function browseUrl(): Promise<string> {
  harness.get.mockClear();
  await harness.query?.queryFn({ pageParam: 0 });
  return String(harness.get.mock.calls[0]?.[0] ?? "");
}

function searchBox(): HTMLInputElement {
  return screen.getByLabelText("Fırsatlarda ara") as HTMLInputElement;
}

describe("opportunity search input", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    harness.get.mockReset().mockResolvedValue({ items: [] });
    harness.query = null;
    harness.page.section_counts = { jobs: 12, announcements: 7, trash: 3 };
    harness.page.facets = { remote: { remote: 4, unknown: 3 } };
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("hızlı yazarken karakter kaybetmez ve tek istek üretir", async () => {
    render(<OpportunityPage />);
    const box = searchBox();

    act(() => {
      fireEvent.change(box, { target: { value: "r" } });
      fireEvent.change(box, { target: { value: "re" } });
      fireEvent.change(box, { target: { value: "rea" } });
      fireEvent.change(box, { target: { value: "reac" } });
      fireEvent.change(box, { target: { value: "react" } });
    });

    // Girdi anında görünür; API'ye gitmesi debounce'a bağlı.
    expect(box.value).toBe("react");
    expect(await browseUrl()).not.toContain("search=");

    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(box.value).toBe("react");
    expect(await browseUrl()).toContain("search=react");
  });

  it("filtreleri temizlemek eski aramayı geri getirmez", async () => {
    render(<OpportunityPage />);
    const box = searchBox();

    await act(async () => {
      fireEvent.change(box, { target: { value: "react" } });
      vi.advanceTimersByTime(300);
    });
    expect(await browseUrl()).toContain("search=react");

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Tümünü temizle/ }));
      vi.advanceTimersByTime(500);
    });

    expect(box.value).toBe("");
    expect(await browseUrl()).not.toContain("search=");
  });

  it("'bilinmiyor' çalışma biçimi filtresi tek kez gösterilir", async () => {
    render(<OpportunityPage />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Filtreler/ }));
    });

    expect(screen.getAllByRole("button", { name: /bilinmiyor/i })).toHaveLength(1);
  });

  it("hızlı uygunluk 'yok' filtresi gerçekten API'ye gider", async () => {
    render(<OpportunityPage />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Filtreler/ }));
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Hızlı uygunluk yok" }));
    });
    await act(async () => {
      vi.advanceTimersByTime(400);
    });

    expect(await browseUrl()).toContain("score_state=uncomputed");
    expect(screen.getByRole("button", { name: /Skor: hesaplanmadı/ })).toBeTruthy();
  });

  it("skorsuz filtresi profil uyumu 'Hesaplanmadı' ile karışmaz", async () => {
    render(<OpportunityPage />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Filtreler/ }));
    });

    // İki farklı eksen iki farklı ad taşır: aynı ada sahip iki chip olmamalı.
    expect(screen.getAllByRole("button", { name: "Hızlı uygunluk yok" })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "Hesaplanmadı" })).toHaveLength(1);
  });

  it("çöp ve duyuru sekmelerinde yalnızca geçerli filtreler gösterilir", async () => {
    render(<OpportunityPage />);

    // Duyurular: yalnızca duyuruya uygulanan filtreler görünür.
    await act(async () => {
      fireEvent.click(screen.getByRole("tab", { name: /^Duyurular/ }));
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Filtreler/ }));
    });
    expect(screen.getByText("Duyuru türü")).toBeTruthy();
    expect(screen.getByText("Tarih")).toBeTruthy();
    expect(screen.getByText("Kaynak durumu")).toBeTruthy();
    // Skor/uyum filtreleri iş ilanlarına özel: duyurularda gösterilmez.
    expect(screen.queryByText("Profil / beceri uyumu")).toBeNull();
    expect(screen.queryByText("Kategori")).toBeNull();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Filtreler/ }));
      fireEvent.click(screen.getByRole("tab", { name: /^Keşfet/ }));
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Çöp/ }));
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Filtreler/ }));
    });

    // Çöp: arşiv görünümü kendi filtresini taşır; backend'e gitmeyen kontrol yok.
    expect(screen.queryByText("Duyuru türü")).toBeNull();
    expect(screen.queryByText("Tarih")).toBeNull();
    expect(screen.queryByText("Kaynak durumu")).toBeNull();
  });
});
