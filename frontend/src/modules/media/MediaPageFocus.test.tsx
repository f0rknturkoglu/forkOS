import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MediaPage, receiveMediaFocus } from "./MediaPage";

type QueryOptions = {
  enabled?: boolean;
  queryFn: () => unknown;
  queryKey: readonly unknown[];
};

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  queries: [] as QueryOptions[],
}));

const otherItem = {
  id: "other-1", title: "Başka kayıt", kind: "book", status: "in_progress",
  progress: 3, total: 10, score: null, notes: null, started_at: null,
  finished_at: null, meta: {}, created_at: "2026-08-20T10:00:00Z",
};
const focusedItem = {
  ...otherItem,
  id: "focus-1",
  title: "Odaklanan kayıt",
};

vi.mock("@/app/router", () => ({
  useHashRoute: () => ({
    path: "/media",
    params: new URLSearchParams("focus=focus-1"),
  }),
}));
vi.mock("@/core/api", () => ({
  api: {
    del: vi.fn(), get: harness.apiGet, patch: vi.fn(), post: vi.fn(),
  },
}));
vi.mock("@/lib/hooks", () => ({
  useInvalidate: () => vi.fn(),
  useOnline: () => true,
}));
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn(() => ({ isPending: false, mutate: vi.fn() })),
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    if (options.queryKey[0] === "media") {
      return { data: { items: [otherItem], total: 1, next_cursor: null } };
    }
    if (options.queryKey[0] === "media-detail") {
      return {
        data: {
          item: focusedItem, units: [], cycles: [], consumptions: [], collections: [],
        },
      };
    }
    if (options.queryKey[0] === "media-stats") {
      return { data: { total: 2, in_progress: 2, completed: 0, planned: 0 } };
    }
    if (options.queryKey[0] === "settings") return { data: {} };
    return { data: undefined, isFetching: false };
  }),
}));

describe("MediaPage hash focus receiver", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.queries.length = 0;
  });

  it("locates a focused item outside the current page and opens its editor", async () => {
    const markup = renderToStaticMarkup(<MediaPage />);
    const detail = harness.queries.find((query) => query.queryKey[0] === "media-detail");

    await detail?.queryFn();
    expect(detail?.queryKey).toEqual(["media-detail", "focus-1"]);
    expect(harness.apiGet).toHaveBeenCalledWith("/media/focus-1");
    expect(markup).toContain('id="media-item-focus-1"');
    expect(markup).toContain("Odaklanan kayıt");
    expect(markup).toContain("İlerleme / toplam");
  });

  it("scrolls and keyboard-focuses the received item row", () => {
    const focus = vi.fn();
    const scrollIntoView = vi.fn();
    const root = {
      getElementById: vi.fn(() => ({
        querySelector: vi.fn(() => ({ focus })),
        scrollIntoView,
      })),
    };

    expect(receiveMediaFocus("focus-1", root)).toBe(true);
    expect(root.getElementById).toHaveBeenCalledWith("media-item-focus-1");
    expect(scrollIntoView).toHaveBeenCalledWith({ block: "center" });
    expect(focus).toHaveBeenCalledOnce();
  });
});
