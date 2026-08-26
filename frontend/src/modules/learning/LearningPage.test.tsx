import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { StudyArea, StudyTopic } from "@/core/types";
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
vi.mock("@/app/router", () => ({
  navigate: vi.fn(),
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

const areas = [{ id: "a1", title: "Matematik", color: null, active: true, position: 0 }] as StudyArea[];
const topics = [
  {
    id: "t1",
    title: "Türev",
    area_id: "a1",
    parent_id: null,
    status: "in_progress",
    confidence: null,
    target_min: null,
    position: 0,
    last_studied_at: null,
    children: [],
  },
] as StudyTopic[];

describe("study flow", () => {
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

  it("lists study areas and topics from their queries and hits the right GET endpoints", async () => {
    harness.queryData = { "study-areas": areas, "study-topics": topics };
    const markup = renderToStaticMarkup(<LearningPage />);

    expect(markup).toContain("Matematik");
    expect(markup).toContain("Türev");

    const areasQuery = harness.queries.find((query) => query.queryKey[0] === "study-areas");
    const topicsQuery = harness.queries.find((query) => query.queryKey[0] === "study-topics");
    await areasQuery?.queryFn();
    await topicsQuery?.queryFn();
    expect(harness.apiGet).toHaveBeenCalledWith("/study/areas");
    expect(harness.apiGet).toHaveBeenCalledWith("/study/topics?area_id=");
  });

  it("creates a todo + prepares_for link for a topic and invalidates todo/study/link writes", async () => {
    harness.apiPost.mockResolvedValue({ id: "todo-1" });
    renderToStaticMarkup(<LearningPage />);

    const createTask = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.({ id: "t1", title: "Türev" });
      return harness.apiPost.mock.calls.some(([url]) => url === "/todos");
    });
    expect(createTask).toBeDefined();

    harness.apiPost.mockClear();
    await (createTask?.mutationFn as (topic: StudyTopic) => Promise<void>)({ id: "t1", title: "Türev" } as StudyTopic);
    expect(harness.apiPost).toHaveBeenCalledWith("/todos", {
      title: "Türev",
      description: "çalışma konusu",
    });
    expect(harness.apiPost).toHaveBeenCalledWith("/links", {
      from_id: "todo-1",
      to_id: "t1",
      relation: "prepares_for",
    });

    createTask?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("todo.write", "study.write", "link.write");
  });

  it("adds a new study area and deletes one with the right API calls and study.write invalidation", () => {
    harness.queryData = { "study-areas": areas };
    harness.stateValues = ["", "Yeni alan", "", null];
    renderToStaticMarkup(<LearningPage />);

    const addArea = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.();
      return harness.apiPost.mock.calls.some(([url]) => url === "/study/areas");
    });
    expect(addArea).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/study/areas", { title: "Yeni alan" });
    addArea?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("study.write");

    harness.invalidate.mockClear();
    const removeArea = harness.mutations.find((mutation) => {
      harness.apiDel.mockClear();
      mutation.mutationFn?.("a1");
      return harness.apiDel.mock.calls.some(([url]) => url === "/study/areas/a1");
    });
    expect(removeArea).toBeDefined();
    expect(harness.apiDel).toHaveBeenCalledWith("/study/areas/a1");
    removeArea?.onSuccess?.(undefined, "a1");
    expect(harness.invalidate).toHaveBeenCalledWith("study.write");
  });
});
