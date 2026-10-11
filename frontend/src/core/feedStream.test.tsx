// @vitest-environment jsdom
import { QueryClient, QueryClientProvider, onlineManager, focusManager } from "@tanstack/react-query";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { experienceFixture } from "./onboarding/testFixtures";
import { useFeedStream, type FeedFilter } from "./feedStream";
let paths: string[] = [];
let settings = experienceFixture();
let broken = "";
const clients: QueryClient[] = [];
function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  clients.push(client);
  return {
    client,
    Wrapper: ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  };
}
beforeEach(() => {
  paths = [];
  settings = experienceFixture();
  broken = "";
  onlineManager.setOnline(true);
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const path = new URL(String(input), "http://localhost").pathname;
      paths.push(path);
      const body = path === "/api/system/experience" ? settings : path === "/api/rss/stats" ? { unread: 7 } : [];
      return new Response(JSON.stringify(body), {
        status: path === broken ? 503 : 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
});
afterEach(() => {
  cleanup();
  clients.splice(0).forEach((c) => c.clear());
  vi.useRealTimers();
  vi.unstubAllGlobals();
  onlineManager.setOnline(true);
});
it.each(["rss", "reddit", "hn", "gh", "all"] as FeedFilter[])("only selected source requests: %s", async (filter) => {
  const { Wrapper } = setup();
  const { result } = renderHook(() => useFeedStream(filter), { wrapper: Wrapper });
  const expected =
    filter === "rss"
      ? ["/api/rss/items", "/api/rss/stats"]
      : filter === "reddit"
        ? ["/api/settings", "/api/news/reddit"]
        : filter === "hn"
          ? ["/api/news/hacker-news"]
          : filter === "gh"
            ? ["/api/news/github-trending"]
            : [
                "/api/settings",
                "/api/rss/items",
                "/api/rss/stats",
                "/api/news/reddit",
                "/api/news/hacker-news",
                "/api/news/github-trending",
              ];
  await waitFor(() =>
    expect([...paths].sort()).toEqual(
      [...new Set(["/api/system/experience", ...expected.filter((p) => p !== "/api/settings")])].sort(),
    ),
  );
  await waitFor(() => expect(result.current.loading).toBe(false));
});
it("reuses cache on switching and simultaneous Home/Feed observers", async () => {
  const { Wrapper } = setup();
  const { rerender } = renderHook(
    ({ filter }) => {
      useFeedStream(filter);
      return useFeedStream(filter);
    },
    { wrapper: Wrapper, initialProps: { filter: "all" as FeedFilter } },
  );
  await waitFor(() => expect(paths).toHaveLength(6));
  rerender({ filter: "hn" });
  rerender({ filter: "rss" });
  rerender({ filter: "all" });
  await act(async () => {});
  expect(paths).toHaveLength(6);
});
it("disabled Reddit never fetches, including cached results", async () => {
  settings = experienceFixture(["hn", "gh"]);
  const { client, Wrapper } = setup();
  client.setQueryData(
    ["settings", "feed", "reddit", ["programming"]],
    [{ id: "old", title: "Old", url: "https://example.com", comments_url: "https://reddit.com", subreddit: "x" }],
  );
  const { result } = renderHook(() => useFeedStream("all"), { wrapper: Wrapper });
  await waitFor(() => expect(paths).toHaveLength(5));
  expect(paths).not.toContain("/api/news/reddit");
  expect(result.current.items.some((i) => i.origin === "reddit")).toBe(false);
});
it("inactive sources do not poll", async () => {
  vi.useFakeTimers();
  focusManager.setFocused(true);
  const { Wrapper } = setup();
  renderHook(() => useFeedStream("hn"), { wrapper: Wrapper });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(100);
  });
  expect(paths).toHaveLength(2);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(16 * 60_000);
  });
  expect(paths).toEqual(["/api/system/experience", "/api/news/hacker-news"]);
});
it("offline keeps cached data without requests", async () => {
  onlineManager.setOnline(false);
  const { client, Wrapper } = setup();
  client.setQueryData(["settings", "experience"], experienceFixture());
  client.setQueryData(
    ["settings", "feed", "hn"],
    [{ objectID: "1", title: "Cached", url: null, points: 1, created_at: new Date().toISOString() }],
  );
  const { result } = renderHook(() => useFeedStream("hn"), { wrapper: Wrapper });
  await act(async () => {});
  expect(paths).toEqual([]);
  expect(result.current.items[0].title).toBe("Cached");
});
it("one failed source does not prevent other requests", async () => {
  broken = "/api/news/hacker-news";
  const { Wrapper } = setup();
  const { result } = renderHook(() => useFeedStream("all"), { wrapper: Wrapper });
  await waitFor(() => expect(result.current.failures.map((s) => s.origin)).toEqual(["hn"]), { timeout: 4000 });
  expect(paths).toContain("/api/rss/items");
});
