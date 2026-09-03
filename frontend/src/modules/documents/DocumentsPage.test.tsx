import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DocumentsPage } from "./DocumentsPage";

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
  invalidate: vi.fn(),
  mutations: [] as MutationOptions[],
  queries: [] as QueryOptions[],
  queryData: {} as Record<string, unknown>,
  stateCursor: 0,
  stateValues: [] as unknown[],
}));

vi.mock("@/app/router", () => ({
  useHashRoute: () => ({ path: "/documents", params: new URLSearchParams() }),
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
  api: { del: harness.apiDel, get: harness.apiGet, patch: harness.apiPatch, post: harness.apiPost },
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
    // Alt anahtarlı query'ler ("documents" / "documents/usages") ayrı dolsun.
    const key = options.queryKey.map(String).join("/");
    return { data: key in harness.queryData ? harness.queryData[key] : undefined, isLoading: false };
  }),
}));

describe("documents flow", () => {
  beforeEach(() => {
    harness.apiDel.mockReset();
    harness.apiGet.mockReset();
    harness.apiPatch.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.mutations.length = 0;
    harness.queries.length = 0;
    harness.queryData = {};
    harness.stateCursor = 0;
    harness.stateValues = [];
  });

  it("lists documents, shows google connection and fetches the scoped endpoints", async () => {
    harness.queryData = {
      "google-status": { connected: true, expires_at: null, scopes: null },
      documents: [
        {
          id: "d1",
          title: "CV 2026",
          drive_file_id: "file-1",
          mime: "application/pdf",
          category: "cv",
          web_view_link: null,
          size_bytes: 2048,
          drive_modified_at: null,
          synced_at: "2026-08-01T00:00:00.000Z",
        },
      ],
      "documents/usages": [],
    };
    const markup = renderToStaticMarkup(<DocumentsPage />);

    expect(markup).toContain("CV 2026");
    expect(markup).toContain("Google bağlı");

    const documentsQuery = harness.queries.find((query) => query.queryKey[0] === "documents");
    const statusQuery = harness.queries.find((query) => query.queryKey[0] === "google-status");
    const usagesQuery = harness.queries.find(
      (query) => query.queryKey[0] === "documents" && query.queryKey[1] === "usages",
    );
    expect(usagesQuery).toBeDefined();
    await documentsQuery?.queryFn();
    await statusQuery?.queryFn();
    await usagesQuery?.queryFn();
    expect(harness.apiGet).toHaveBeenCalledWith("/documents");
    expect(harness.apiGet).toHaveBeenCalledWith("/auth/google/status");
    expect(harness.apiGet).toHaveBeenCalledWith("/documents/usages");
    expect(harness.apiGet).not.toHaveBeenCalledWith(expect.stringContaining("opportunities?limit"));
  });

  it("renders usage badges from /documents/usages: dedupes cv+requirement and caps at 3", async () => {
    harness.queryData = {
      "google-status": { connected: true, expires_at: null, scopes: null },
      documents: [
        {
          id: "d1",
          title: "CV 2026",
          drive_file_id: "file-1",
          mime: "application/pdf",
          category: "cv",
          web_view_link: null,
          size_bytes: 2048,
          drive_modified_at: null,
          synced_at: "2026-08-01T00:00:00.000Z",
        },
        {
          id: "d2",
          title: "Talepname",
          drive_file_id: "file-2",
          mime: "text/plain",
          category: "other",
          web_view_link: null,
          size_bytes: 512,
          drive_modified_at: null,
          synced_at: "2026-08-01T00:00:00.000Z",
        },
      ],
      // d1: o1 hem cv hem requirement (rozet tek olmalı) + o2, o3, o4 → 4 eşsiz fırsat.
      // d2: hiç kullanılmıyor → rozet yok.
      "documents/usages": [
        {
          document_id: "d1",
          usages: [
            { opportunity_id: "o1", title: "Alfa A.Ş.", status: "applied", kind: "job", relation: "cv" },
            {
              opportunity_id: "o1",
              title: "Alfa A.Ş.",
              status: "applied",
              kind: "job",
              relation: "requirement",
            },
            { opportunity_id: "o2", title: "Beta Yazılım", status: "interviewing", kind: "job", relation: "cv" },
            { opportunity_id: "o3", title: "Gamma Labs", status: "applied", kind: "job", relation: "requirement" },
            { opportunity_id: "o4", title: "Delta Teknoloji", status: "discovered", kind: "job", relation: "cv" },
          ],
        },
      ],
    };
    const markup = renderToStaticMarkup(<DocumentsPage />);

    // Aynı fırsatın cv+requirement bağı tek rozete iner: "Alfa A.Ş." yalnızca
    // o1'e ait TEK anchor'da görünür (anchor title'ı + chip metni = 2 geçiş).
    expect(markup.match(/Alfa A\.Ş\./g)).toHaveLength(2);
    expect(markup.match(/href="#\/opportunities\?focus=o1"/g)).toHaveLength(1);
    expect(markup).toContain("Beta Yazılım");
    expect(markup).toContain("Gamma Labs");
    // İlk 3 eşsiz fırsat link olarak çizilir, 4.'sü "+1" rozetine dönüşür.
    expect(markup).not.toContain("Delta Teknoloji");
    expect(markup).toContain("+1");
    const focusLinks = markup.match(/href="#\/opportunities\?focus=/g);
    expect(focusLinks).toHaveLength(3);
  });

  it("syncs a drive folder with the selected category and invalidates document.write", () => {
    harness.apiPost.mockResolvedValue({ synced: 2 });
    harness.stateValues = ["folder-1", "cv", null];
    renderToStaticMarkup(<DocumentsPage />);

    const sync = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.();
      return harness.apiPost.mock.calls.some(([url]) => url === "/documents/sync");
    });
    expect(sync).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/documents/sync", {
      folder_id: "folder-1",
      category: "cv",
    });
    sync?.onSuccess?.({ synced: 2 });
    expect(harness.invalidate).toHaveBeenCalledWith("document.write");
  });
});
