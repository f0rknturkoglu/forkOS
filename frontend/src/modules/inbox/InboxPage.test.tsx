import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Bookmark } from "@/core/types";
import { InboxPage } from "./InboxPage";

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
vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: { children?: unknown }) => children,
  DragOverlay: ({ children }: { children?: unknown }) => children ?? null,
  KeyboardSensor: class KeyboardSensor {},
  PointerSensor: class PointerSensor {},
  useDraggable: () => ({ attributes: {}, listeners: {}, setNodeRef: () => {}, isDragging: false }),
  useDroppable: () => ({ setNodeRef: () => {}, isOver: false }),
  useSensor: (sensor: unknown) => sensor,
  useSensors: (...sensors: unknown[]) => sensors,
}));

const inboxBookmarks = [
  {
    id: "b1",
    title: "İncelenecek yazı",
    url: "https://example.com/yazi",
    source: "manual",
    saved_at: "2026-01-01T10:00:00.000Z",
    tags: ["faz"],
    selection: null,
    collection: "inbox",
  },
] as Bookmark[];

describe("inbox flow", () => {
  beforeEach(() => {
    vi.stubGlobal("crypto", { randomUUID: () => "uuid-1" });
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

  afterEach(() => vi.unstubAllGlobals());

  it("lists inbox bookmarks and target collection counts from their queries", async () => {
    harness.queryData = {
      bookmarks: inboxBookmarks,
      "bookmark-stats": { collections: [{ collection: "read_later", count: 3 }] },
    };
    const markup = renderToStaticMarkup(<InboxPage />);

    expect(markup).toContain("İncelenecek yazı");
    expect(markup).toContain("#faz");
    expect(markup).toContain("Bekleyenler");
    expect(markup).toContain("Sürükle, hedefe tıkla veya sayı tuşlarını kullan.");
    expect(markup).toContain("3"); // read_later hedef sayaci

    const listQuery = harness.queries.find((query) => query.queryKey[0] === "bookmarks");
    await listQuery?.queryFn();
    expect(harness.apiGet).toHaveBeenCalledWith("/bookmarks?collection=inbox&limit=200");
  });

  it("moves a bookmark to another collection and invalidates bookmark.write", () => {
    harness.queryData = { bookmarks: inboxBookmarks };
    renderToStaticMarkup(<InboxPage />);

    const move = harness.mutations.find((mutation) => {
      harness.apiPatch.mockClear();
      mutation.mutationFn?.({ id: "b1", collection: "read_later" });
      return harness.apiPatch.mock.calls.some(([url]) => url === "/bookmarks/b1/collection?collection=read_later");
    });
    expect(move).toBeDefined();
    expect(harness.apiPatch).toHaveBeenCalledWith("/bookmarks/b1/collection?collection=read_later");
    move?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("bookmark.write");
  });

  it("captures a new bookmark into the inbox and removes one with bookmark.write invalidation", () => {
    harness.queryData = { bookmarks: inboxBookmarks };
    harness.stateValues = [null, null, "https://example.com/yeni", "Yeni makale"];
    renderToStaticMarkup(<InboxPage />);

    const capture = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.({ id: "x", collection: "inbox" });
      return harness.apiPost.mock.calls.some(([url]) => url === "/capture");
    });
    expect(capture).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/capture", {
      url: "https://example.com/yeni",
      title: "Yeni makale",
      collection: "inbox",
      source: "manual",
      client_uuid: "uuid-1",
    });
    capture?.onSuccess?.({ id: "b2", duplicate: false });
    expect(harness.invalidate).toHaveBeenCalledWith("bookmark.write");

    harness.invalidate.mockClear();
    const remove = harness.mutations.find((mutation) => {
      harness.apiDel.mockClear();
      mutation.mutationFn?.({ id: "b1", collection: "read_later" });
      return harness.apiDel.mock.calls.some(([url]) => url === "/bookmarks/b1");
    });
    expect(remove).toBeDefined();
    expect(harness.apiDel).toHaveBeenCalledWith("/bookmarks/b1");
    remove?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("bookmark.write");
  });
});
