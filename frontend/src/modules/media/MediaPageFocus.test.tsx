// @vitest-environment jsdom

import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MediaPage, receiveMediaFocus } from "./MediaPage";

type QueryOptions = {
  enabled?: boolean;
  queryFn: () => unknown;
  queryKey: readonly unknown[];
};

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  navigate: vi.fn(),
  queries: [] as QueryOptions[],
}));

vi.mock("@/app/router", () => ({
  navigate: harness.navigate,
  useHashRoute: () => ({
    path: "/media",
    params: new URLSearchParams("focus=focus/1"),
  }),
}));
vi.mock("@/core/api", () => ({
  api: { del: vi.fn(), get: harness.apiGet, patch: vi.fn(), post: vi.fn() },
}));
vi.mock("@/lib/hooks", () => ({
  useDebounced: (value: string) => value,
  useInvalidate: () => vi.fn(),
  useOnline: () => true,
}));
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn(() => ({ isPending: false, mutate: vi.fn() })),
  useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    if (options.queryKey[0] === "media") return { data: { items: [], total: 0, next_cursor: null } };
    if (options.queryKey[0] === "media-stats") return { data: { total: 0, in_progress: 0, completed: 0, planned: 0 } };
    if (options.queryKey[0] === "media-providers") return { data: [] };
    return { data: undefined, isFetching: false };
  }),
}));

describe("MediaPage hash focus receiver", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.navigate.mockReset();
    harness.queries.length = 0;
  });

  afterEach(cleanup);

  it("routes an entity focus value to the encoded detail page without fetching it as a title or inline detail", async () => {
    render(<MediaPage />);

    await waitFor(() => expect(harness.navigate).toHaveBeenCalledWith("/media/focus%2F1"));
    expect(harness.queries.some((query) => query.queryKey[0] === "media-detail")).toBe(false);
    expect(harness.apiGet).not.toHaveBeenCalledWith(expect.stringContaining("focus%2F1"));
  });

  it("scrolls and keyboard-focuses a received legacy item row", () => {
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

  it("returns false when a legacy focused row is not mounted", () => {
    expect(receiveMediaFocus("missing", { getElementById: () => null })).toBe(false);
  });
});
