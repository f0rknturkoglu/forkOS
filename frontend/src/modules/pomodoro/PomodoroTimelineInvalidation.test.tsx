import { createElement } from "react";
import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FocusMode } from "./FocusMode";
import { PomodoroPage } from "./PomodoroPage";
import { PomodoroWidget } from "./PomodoroWidget";

type MutationOptions = {
  mutationFn?: (value?: unknown) => unknown;
  onSuccess?: () => void;
};
type QueryOptions = { queryKey: readonly unknown[] };

const harness = vi.hoisted(() => ({
  apiDel: vi.fn(),
  apiPost: vi.fn(),
  invalidate: vi.fn(),
  mutations: [] as MutationOptions[],
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
      return [harness.stateValues[index], (value: unknown) => { harness.stateValues[index] = value; }];
    },
  };
});
vi.mock("@/core/api", () => ({
  api: { del: harness.apiDel, get: vi.fn(), post: harness.apiPost },
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
    const key = options.queryKey[0];
    if (key === "pomodoro-active") return { data: activeSession };
    if (key === "pomodoro-stats") return { data: { interrupted: 0, minutes: 0, sessions: 0 } };
    if (key === "todos") return { data: [contextTodo] };
    return { data: [] };
  }),
}));

const activeSession = {
  id: "pomo-1", context_title: "Proje görevi", kind: "focus", paused_at: null,
  paused_s: 0, planned_min: 50, started_at: "2026-01-01T10:00:00.000Z", topic: "Odak",
};
const contextTodo = { id: "todo-1", title: "Proje görevi" };
const refreshEvent = "pomodoro.write";

function findPostMutation(url: string, value?: unknown) {
  return harness.mutations.find((mutation) => {
    harness.apiPost.mockClear();
    mutation.mutationFn?.(value);
    return harness.apiPost.mock.calls.some(([actualUrl]) => actualUrl === url);
  });
}

function render(component: () => ReactElement, stateValues: unknown[]) {
  harness.stateCursor = 0;
  harness.stateValues = stateValues;
  renderToStaticMarkup(createElement(component));
}

describe("pomodoro project timeline refresh", () => {
  beforeEach(() => {
    vi.stubGlobal("window", { clearInterval: vi.fn(), location: { hash: "" }, setInterval: vi.fn() });
    harness.apiDel.mockReset();
    harness.apiPost.mockReset();
    harness.invalidate.mockReset();
    harness.mutations.length = 0;
  });

  afterEach(() => vi.unstubAllGlobals());

  it("refreshes the project timeline after page stops and contextual manual entries", () => {
    render(PomodoroPage, [Date.now(), false, 50, "", "", true, "2026-01-01T09:00", 50, "Manuel", "todo-1"]);

    const stop = findPostMutation("/pomodoro/pomo-1/stop", false);
    expect(stop).toBeDefined();
    stop?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith(refreshEvent);

    harness.invalidate.mockClear();
    const manual = findPostMutation("/pomodoro");
    expect(manual).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/pomodoro", expect.objectContaining({ context_entity_id: "todo-1" }));
    manual?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith(refreshEvent);
  });

  it("refreshes the project timeline after widget and focus-mode stops, but not pause", () => {
    render(PomodoroWidget, [Date.now(), false, false]);
    const widgetStop = findPostMutation("/pomodoro/pomo-1/stop", true);
    expect(widgetStop).toBeDefined();
    widgetStop?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith(refreshEvent);

    harness.invalidate.mockClear();
    harness.mutations.length = 0;
    render(() => createElement(FocusMode, { onClose: vi.fn() }), [Date.now()]);
    const focusStop = findPostMutation("/pomodoro/pomo-1/stop", false);
    expect(focusStop).toBeDefined();
    focusStop?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith(refreshEvent);

    harness.invalidate.mockClear();
    const pause = findPostMutation("/pomodoro/pomo-1/pause");
    expect(pause).toBeDefined();
    pause?.onSuccess?.();
    // Duraklatma da bir pomodoro yazmasidir; harita pomodoro.write'i tazeler.
    expect(harness.invalidate).toHaveBeenCalledWith(refreshEvent);
  });
});
