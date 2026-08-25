import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TodoPage } from "./TodoPage";

type QueryOptions = { queryKey: readonly unknown[]; queryFn: () => unknown };

const harness = vi.hoisted(() => ({
  apiGet: vi.fn(),
  path: "/habits",
  queries: [] as QueryOptions[],
}));

vi.mock("@/app/router", () => ({
  useHashRoute: () => ({ path: harness.path, params: new URLSearchParams() }),
}));
vi.mock("@/core/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/api")>();
  return { ...actual, api: { ...actual.api, get: harness.apiGet } };
});
vi.mock("@/lib/hooks", () => ({
  useInvalidate: () => vi.fn(),
  useOnline: () => true,
}));
vi.mock("@tanstack/react-query", () => ({
  useMutation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    return { data: [], isLoading: false };
  }),
}));

describe("Todo routine filter", () => {
  beforeEach(() => {
    harness.apiGet.mockReset();
    harness.queries.length = 0;
    harness.path = "/habits";
  });

  it("opens the legacy habits route as the routine-filtered Todo page", async () => {
    harness.apiGet.mockResolvedValue([]);
    const markup = renderToStaticMarkup(<TodoPage />);
    const todos = harness.queries.find((query) => query.queryKey[0] === "todos");

    await todos?.queryFn();
    expect(markup).toContain("Görevler");
    expect(markup).toContain("Rutinler");
    expect(markup).not.toContain("Alışkanlıklar");
    expect(todos?.queryKey).toEqual(["todos", "open", "routines", ""]);
    expect(harness.apiGet).toHaveBeenCalledWith("/todos?status=open&limit=300&recur_only=true");
  });
});
