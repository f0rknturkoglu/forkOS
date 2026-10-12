import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Bookmark } from "@/core/types";
import { BookmarksPage } from "./BookmarksPage";

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
  useDebounced: (value: string) => value,
  useOnline: () => true,
}));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@/app/router", () => ({
  useHashRoute: () => ({ params: new URLSearchParams() }),
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

const bookmarks = [
  {
    id: "b1",
    title: "Önemli makale",
    url: "https://example.com/yazi",
    source: "manual",
    saved_at: "2026-01-01T10:00:00.000Z",
    tags: ["react"],
    selection: null,
    collection: "inbox",
    read_status: "unread",
    favorite: false,
    note: null,
    queue_kind: null,
  },
] as Bookmark[];

describe("bookmarks flow", () => {
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

  it("lists bookmarks with tags and fetches the library query", async () => {
    harness.queryData = { bookmarks };
    const markup = renderToStaticMarkup(<BookmarksPage />);

    expect(markup).toContain("Önemli makale");
    expect(markup).toContain("#react");
    expect(markup).toContain("Koleksiyonlar");
    expect(markup).toContain("Okuma durumu");

    const library = harness.queries.find((query) => query.queryKey[0] === "bookmarks");
    await library?.queryFn();
    expect(harness.apiGet).toHaveBeenCalledWith("/bookmarks?limit=100");
  });

  it("patches a bookmark (favorite) and deletes it with bookmark.write invalidation", () => {
    harness.queryData = { bookmarks };
    renderToStaticMarkup(<BookmarksPage />);

    const patch = harness.mutations.find((mutation) => {
      harness.apiPatch.mockClear();
      try {
        mutation.mutationFn?.({ favorite: true });
      } catch {
        return false;
      }
      return harness.apiPatch.mock.calls.some(([url]) => url === "/bookmarks/b1");
    });
    expect(patch).toBeDefined();
    expect(harness.apiPatch).toHaveBeenCalledWith("/bookmarks/b1", { favorite: true });
    patch?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("bookmark.write");

    harness.invalidate.mockClear();
    const remove = harness.mutations.find((mutation) => {
      harness.apiDel.mockClear();
      try {
        mutation.mutationFn?.();
      } catch {
        return false;
      }
      return harness.apiDel.mock.calls.some(([url]) => url === "/bookmarks/b1");
    });
    expect(remove).toBeDefined();
    expect(harness.apiDel).toHaveBeenCalledWith("/bookmarks/b1");
    remove?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("bookmark.write");
  });

  it("keeps the toolbar free of saved views and RSS shortcuts", async () => {
    harness.queryData = {
      bookmarks,
      views: [
        {
          id: "v1",
          name: "Okunmamış",
          module: "bookmarks",
          filter: { read_status: "unread" },
          sort: null,
          pinned: false,
          position: 1,
        },
      ],
    };
    const markup = renderToStaticMarkup(<BookmarksPage />);
    expect(markup).not.toContain("Görünümler");
    expect(markup).not.toContain(">RSS<");
    // Existing saved-view deep links remain consumable without a toolbar button.
    expect(harness.queries.some((query) => query.queryKey[0] === "views")).toBe(true);
  });

  it("renders grid and list toggle buttons, and import/export action buttons", () => {
    harness.queryData = { bookmarks };
    const markup = renderToStaticMarkup(<BookmarksPage />);

    expect(markup).toContain("Kart Izgarasi (Grid)");
    expect(markup).toContain("Kompakt Liste (List)");
    expect(markup).toContain("Ice Aktar");
    expect(markup).toContain("Disa Aktar");
  });
});
