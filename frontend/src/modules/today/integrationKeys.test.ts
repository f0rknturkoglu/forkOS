import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RecurringWidget } from "@/modules/finance/RecurringWidget";
import { RssPage } from "@/modules/rss/RssPage";
import { TodayAgendaWidget } from "./TodayAgendaWidget";

type QueryOptions = { queryKey: readonly unknown[] };
type MutationOptions = {
  mutationFn?: (variables?: { id: string; collection: string }) => unknown;
  onSuccess?: (bookmark: { id: string; title: string }) => void;
};

const harness = vi.hoisted(() => ({
  apiPost: vi.fn(),
  apiDel: vi.fn(),
  invalidate: vi.fn(),
  queries: [] as QueryOptions[],
  mutations: [] as MutationOptions[],
}));

vi.mock("@/core/api", () => ({
  api: { del: harness.apiDel, get: vi.fn(), post: harness.apiPost },
  qs: vi.fn(() => ""),
}));
vi.mock("@/lib/hooks", () => ({
  useInvalidate: () => harness.invalidate,
  useOnline: () => true,
}));
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn((options: MutationOptions) => {
    harness.mutations.push(options);
    return { mutate: vi.fn(), isPending: false };
  }),
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    return options.queryKey[0] === "today-agenda"
      ? { data: undefined, isLoading: false, isError: true, refetch: vi.fn() }
      : { data: [] };
  }),
}));

describe("cross-page query integration", () => {
  beforeEach(() => {
    harness.apiDel.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.queries.length = 0;
    harness.mutations.length = 0;
  });

  it("registers Today widget queries under their detail-page prefixes", () => {
    renderToStaticMarkup(createElement(TodayAgendaWidget));
    renderToStaticMarkup(createElement(RecurringWidget));

    expect(harness.queries.map((query) => query.queryKey)).toContainEqual(
      ["today-agenda", expect.any(String)],
    );
    expect(harness.queries.map((query) => query.queryKey)).toContainEqual(["recurring", "widget"]);
  });

  it("runs the RSS save success callback with every linked refresh prefix", () => {
    renderToStaticMarkup(createElement(RssPage));

    const save = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.({ id: "rss-1", collection: "read_later" });
      return harness.apiPost.mock.calls.some(([url]) => url === "/rss/items/rss-1/save");
    });

    expect(save).toBeDefined();
    harness.apiPost.mockClear();
    save?.onSuccess?.({ id: "bookmark-1", title: "Kaydedilen yazı" });

    expect(harness.invalidate).toHaveBeenCalledWith(
      "rss-item", "items", "feeds", "rss-stats", "bookmarks", "bookmark-stats", "activity",
    );
  });
});
