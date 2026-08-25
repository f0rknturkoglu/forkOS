import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LearningPage } from "./LearningPage";

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

const courses = [
  {
    id: "c1",
    title: "React Temelleri",
    platform: "Udemy",
    url: null,
    status: "active",
    progress_pct: 40,
    started_at: null,
    completed_at: null,
    notes: null,
  },
];
const books = [
  {
    id: "b1",
    title: "Yazılım Testi",
    author: "K. Beck",
    status: "reading",
    total_pages: 250,
    current_page: 80,
    started_at: null,
    finished_at: null,
    rating: null,
    notes: null,
  },
];

describe("learning flow", () => {
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

  it("lists courses, books and the learning queue from their queries", async () => {
    harness.queryData = {
      courses,
      books,
      "learning-queue": [{ id: "bm1", title: "Bir makale", url: "https://example.com/x" }],
    };
    harness.stateValues = ["courses", ""];
    const markup = renderToStaticMarkup(<LearningPage />);

    expect(markup).toContain("React Temelleri");
    expect(markup).toContain("Udemy");

    harness.stateCursor = 0;
    harness.stateValues = ["books", ""];
    const booksMarkup = renderToStaticMarkup(<LearningPage />);
    expect(booksMarkup).toContain("Yazılım Testi");
    expect(booksMarkup).toContain("K. Beck");

    const coursesQuery = harness.queries.find((query) => query.queryKey[0] === "courses");
    const booksQuery = harness.queries.find((query) => query.queryKey[0] === "books");
    const queueQuery = harness.queries.find((query) => query.queryKey[0] === "learning-queue");
    await coursesQuery?.queryFn();
    await booksQuery?.queryFn();
    await queueQuery?.queryFn();
    expect(harness.apiGet).toHaveBeenCalledWith("/courses");
    expect(harness.apiGet).toHaveBeenCalledWith("/books");
    expect(harness.apiGet).toHaveBeenCalledWith("/learning/queue");
  });

  it("creates a course or book in the active tab and invalidates learning.write", () => {
    harness.stateValues = ["books", "  Yazılım Testi  "];
    renderToStaticMarkup(<LearningPage />);

    const create = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.();
      return harness.apiPost.mock.calls.some(([url]) => url === "/books");
    });
    expect(create).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/books", { title: "  Yazılım Testi  " });
    create?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("learning.write");
  });

  it("patches course progress to done at 100% and deletes entries via the right endpoints", () => {
    harness.stateValues = ["courses", ""];
    renderToStaticMarkup(<LearningPage />);

    const patchCourse = harness.mutations.find((mutation) => {
      harness.apiPatch.mockClear();
      mutation.mutationFn?.({ id: "c1", progress_pct: 100 });
      return harness.apiPatch.mock.calls.some(([url]) => url === "/courses/c1");
    });
    expect(patchCourse).toBeDefined();
    expect(harness.apiPatch).toHaveBeenCalledWith("/courses/c1", {
      progress_pct: 100,
      status: "done",
    });
    patchCourse?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("learning.write");

    harness.invalidate.mockClear();
    const remove = harness.mutations.find((mutation) => {
      harness.apiDel.mockClear();
      mutation.mutationFn?.({ id: "b1", kind: "books" });
      return harness.apiDel.mock.calls.some(([url]) => url === "/books/b1");
    });
    expect(remove).toBeDefined();
    expect(harness.apiDel).toHaveBeenCalledWith("/books/b1");
    remove?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("learning.write");
  });
});
