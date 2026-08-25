import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CalendarPage } from "./CalendarPage";

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

describe("calendar flow", () => {
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

  it("places events from the calendar query onto the grid", async () => {
    harness.queryData = {
      "calendar-events": [
        {
          id: "ev1",
          source: "plan",
          title: "Proje teslimi",
          starts_at: new Date().toISOString(),
          ends_at: null,
          all_day: false,
          location: null,
          url: null,
          note: null,
          read_only: false,
          google_event_id: null,
        },
      ],
    };
    const markup = renderToStaticMarkup(<CalendarPage />);

    expect(markup).toContain("Proje teslimi");

    const eventsQuery = harness.queries.find((query) => query.queryKey[0] === "calendar-events");
    await eventsQuery?.queryFn();
    expect(harness.apiGet).toHaveBeenCalledWith(expect.stringMatching(/^\/calendar\/events\?from=.+&to=.+/));
  });

  it("pulls from google and invalidates calendar.write", () => {
    renderToStaticMarkup(<CalendarPage />);

    const sync = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.();
      return harness.apiPost.mock.calls.some(([url]) => url === "/calendar/sync");
    });
    expect(sync).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/calendar/sync");
    sync?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("calendar.write");
  });

  it("pushes a plan block to google and invalidates calendar.write", () => {
    renderToStaticMarkup(<CalendarPage />);

    const push = harness.mutations.find((mutation) => {
      harness.apiPost.mockClear();
      mutation.mutationFn?.("ev1");
      return harness.apiPost.mock.calls.some(([url]) => url === "/plan/ev1/push");
    });
    expect(push).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/plan/ev1/push");
    push?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("calendar.write");
  });
});
