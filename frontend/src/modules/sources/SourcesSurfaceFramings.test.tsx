// @vitest-environment jsdom
/**
 * Tek uygulama, iki çerçeve.
 *
 * Kaynak yüzeyi TEK bileşendir (`@/modules/sources/SourcesWorkspace`): kariyer
 * sekmesi ve `/sources` rotası aynı bileşeni farklı `framing` ile kullanır.
 * Bu test, iki yüzeyin de AYNI modül bileşenini çağırdığını ve kariyer
 * modülünde ikinci bir kopya kalmadığını kanıtlar.
 */
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import type { ReactElement } from "react";
import type * as ReactQueryModule from "@tanstack/react-query";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const harness = vi.hoisted(() => ({
  params: new URLSearchParams("tab=sources"),
  surface: vi.fn((_props: { framing?: string }) => null),
}));

// jsdom bu kurulumda kalıcı depolama sağlamaz; sayfa kabuğu onu okur.
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

vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof ReactQueryModule>();
  return {
    ...actual,
    useInfiniteQuery: vi.fn(() => ({
      data: {
        pages: [
          {
            items: [],
            total: 0,
            offset: 0,
            limit: 60,
            section_counts: { jobs: 0, announcements: 0, trash: 0 },
            facets: {},
          },
        ],
      },
      isPending: false,
      isError: false,
      isFetching: false,
      hasNextPage: false,
      isFetchingNextPage: false,
      refetch: vi.fn(),
      fetchNextPage: vi.fn(),
    })),
    useMutation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
    useQuery: vi.fn(() => ({ data: [], isLoading: false, isError: false, refetch: vi.fn() })),
  };
});
vi.mock("@/core/api", () => ({
  api: { get: vi.fn(async () => []), post: vi.fn(), patch: vi.fn(), del: vi.fn() },
  qs: () => "",
}));
vi.mock("@/app/router", () => ({
  navigate: vi.fn(),
  useHashRoute: () => ({ path: "/", params: harness.params }),
}));
vi.mock("@/core/SaveToLibrary", () => ({ useSaveToLibrary: () => ({ save: vi.fn() }) }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true, useInvalidate: () => vi.fn() }));
vi.mock("@/core/SyncProgress", () => ({ SyncProgress: () => null }));
vi.mock("@/modules/sources/SourcePicker", () => ({ SourcePicker: () => null }));
vi.mock("@/modules/sources/SourcesWorkspace", () => ({ SourcesWorkspace: harness.surface }));
vi.mock("@/modules/opportunity/OpportunityDetail", () => ({ OpportunityDetail: () => null }));
vi.mock("@/modules/opportunity/ApplicationsWorkspace", () => ({ ApplicationsWorkspace: () => null }));
vi.mock("@/modules/opportunity/CareerWorkspace", () => ({ CareerWorkspace: () => null }));

import { OpportunityPage } from "@/modules/opportunity/OpportunityPage";
import { SourcesPage } from "./SourcesPage";

function renderPage(node: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

beforeEach(() => {
  harness.params = new URLSearchParams("tab=sources");
  harness.surface.mockClear();
});

afterEach(() => cleanup());

describe("paylaşılan yüzey", () => {
  it("kariyer sekmesi ile /sources aynı bileşeni kullanır", async () => {
    renderPage(<OpportunityPage />);
    await waitFor(() => expect(harness.surface).toHaveBeenCalled());
    // Sekme varsayılan çerçeveyi kullanır (career).
    expect(harness.surface.mock.calls[0][0]).toEqual({});

    harness.surface.mockClear();
    harness.params = new URLSearchParams("");
    renderPage(<SourcesPage />);
    await waitFor(() => expect(harness.surface).toHaveBeenCalled());
    // Rota sistemi çerçevesini açar; aynı bileşen, farklı vurgu.
    expect(harness.surface.mock.calls[0][0]).toMatchObject({ framing: "system" });
  });

  it("kariyer modülü kaynak yüzeyinin kopyasını taşımaz", () => {
    const opportunityDir = resolve(process.cwd(), "src/modules/opportunity");
    expect(existsSync(resolve(opportunityDir, "SourcesWorkspace.tsx"))).toBe(false);
    expect(existsSync(resolve(opportunityDir, "SourcePicker.tsx"))).toBe(false);
  });
});
