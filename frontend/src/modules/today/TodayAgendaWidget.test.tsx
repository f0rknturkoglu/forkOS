// @vitest-environment jsdom

import { renderToStaticMarkup } from "react-dom/server";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AgendaRow, TodayAgenda, Todo } from "@/core/types";
import { localDateKey } from "@/lib/date";
import { TodayAgendaWidget } from "./TodayAgendaWidget";

type MutationOptions = {
  mutationKey?: readonly unknown[];
  mutationFn?: (variables: never) => Promise<unknown> | unknown;
  onSuccess?: () => void;
};
type QueryOptions = { queryKey: readonly unknown[] };

const parent: AgendaRow = {
  kind: "todo",
  source: "due",
  id: "parent-1",
  slot_id: null,
  title: "Ana görev",
  completed: false,
  action: null,
  read_only: false,
  context_only: true,
  starts_at: null,
  duration_min: null,
  parent_id: null,
  project_title: "forkOS",
  feed_title: null,
  url: null,
  recur: null,
  media_kind: null,
  media_status: null,
  progress_label: null,
  cover_url: null,
  children: [
    {
      kind: "todo",
      source: "due",
      id: "child-1",
      slot_id: null,
      title: "Alt görev",
      completed: false,
      action: "complete_todo",
      read_only: false,
      context_only: false,
      starts_at: null,
      duration_min: null,
      parent_id: "parent-1",
      project_title: "forkOS",
      feed_title: null,
      url: null,
      recur: null,
      children: [],
      media_kind: null,
      media_status: null,
      progress_label: null,
      cover_url: null,
    },
  ],
};

const todoRow: AgendaRow = {
  ...parent,
  id: "todo-1",
  title: "Görevi tamamla",
  context_only: false,
  action: "complete_todo",
  children: [],
};
const rssRow: AgendaRow = {
  ...todoRow,
  kind: "rss",
  source: "planned",
  id: "rss-1",
  slot_id: "slot-rss",
  title: "Yazıyı oku",
  action: "mark_rss_read",
  feed_title: "Yerel akış",
  project_title: null,
};
const mediaRow: AgendaRow = {
  ...todoRow,
  kind: "media",
  source: "planned",
  id: "media-1",
  slot_id: "slot-media",
  title: "Dune",
  action: "log_media",
  media_kind: "book",
  media_status: "in_progress",
  progress_label: "120 / 400 sayfa",
  cover_url: "/api/media/assets/dune.webp",
  project_title: null,
};
const routineRow: AgendaRow = {
  ...todoRow,
  source: "routine",
  id: "routine-today",
  title: "Bugünün rutini",
  recur: "daily",
};

const agenda: TodayAgenda = {
  day: "2026-08-23",
  auto_suggestions: true,
  timed: [
    {
      ...todoRow,
      kind: "calendar",
      source: "calendar",
      id: "cal-1",
      title: "Toplantı",
      action: null,
      read_only: true,
      starts_at: "2026-08-23T09:30:00+03:00",
    },
  ],
  checklist: [parent, todoRow, routineRow, rssRow, mediaRow],
  completed: [{ ...todoRow, id: "completed-1", title: "Biten görev", completed: true, action: null }],
  suggestions: {
    flashcards: [],
    todos: [
      { ...todoRow, id: "suggested-1", title: "Birinci öneri", source: "suggestion" },
      { ...todoRow, id: "suggested-2", title: "İkinci öneri", source: "suggestion" },
    ],
    rss: [{ ...rssRow, id: "suggested-rss-1", title: "Üçüncü öneri", source: "suggestion" }],
    media: [],
  },
};

const openTodo: Todo = {
  id: "open-1",
  title: "Tarihsiz açık görev",
  description: null,
  priority: 2,
  status: "open",
  due_at: null,
  reminder_at: null,
  completed_at: null,
  parent_id: null,
  position: 0,
  tags: [],
  recur: null,
  project_id: null,
  project_title: null,
  milestone_id: null,
  milestone_title: null,
  subtask_total: 0,
  subtask_done: 0,
  planned_day: null,
  planned_start_min: null,
};

const futureRoutine: Todo = {
  ...openTodo,
  id: "routine-future",
  title: "Yarının rutini",
  recur: "daily",
  due_at: "2026-08-24T09:00:00Z",
};

const harness = vi.hoisted(() => ({
  apiDel: vi.fn(),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  invalidate: vi.fn(),
  mutations: [] as MutationOptions[],
  queries: [] as QueryOptions[],
}));

vi.mock("@/core/api", () => ({
  api: { del: harness.apiDel, get: harness.apiGet, post: harness.apiPost, put: harness.apiPut },
  qs: vi.fn(() => ""),
}));
vi.mock("@/lib/hooks", () => ({
  useOnline: () => true,
}));
vi.mock("@/core/invalidation", () => ({
  invalidateAfter: (...events: string[]) => harness.invalidate(...events),
}));
vi.mock("@tanstack/react-query", () => ({
  QueryClient: class {
    invalidateQueries() {}
  },
  MutationCache: class {},
  useMutation: vi.fn((options: MutationOptions) => {
    harness.mutations.push(options);
    return {
      mutate: vi.fn((variables: never) => options.mutationFn?.(variables)),
      isPending: false,
    };
  }),
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    if (options.queryKey[0] === "today-agenda") {
      return { data: agenda, isLoading: false, isError: false, refetch: vi.fn() };
    }
    if (options.queryKey[0] === "todos") {
      return {
        data: [openTodo, futureRoutine, { ...openTodo, id: "todo-1", title: "Görevi tamamla" }],
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      };
    }
    return { data: [], isLoading: false, isError: false, refetch: vi.fn() };
  }),
}));

function mutationNamed(name: string) {
  return harness.mutations.find((mutation) => mutation.mutationKey?.[0] === name);
}

describe("unified Today agenda", () => {
  afterEach(cleanup);

  beforeEach(() => {
    harness.apiDel.mockReset();
    harness.apiGet.mockReset();
    harness.apiPost.mockReset();
    harness.apiPut.mockReset();
    harness.invalidate.mockReset();
    harness.mutations.length = 0;
    harness.queries.length = 0;
  });

  it("shows one hierarchy-aware flow and registers the local-day agenda query", () => {
    const markup = renderToStaticMarkup(<TodayAgendaWidget />);

    expect(markup).toContain("Bugünün planı");
    expect(markup).not.toContain("Bugünün programı");
    expect(markup).not.toContain("Bugünün görevleri");
    expect(markup.indexOf("Ana görev")).toBeLessThan(markup.indexOf("Alt görev"));
    expect(markup.match(/data-agenda-id="child-1"/g)).toHaveLength(1);
    expect(markup).toContain("Açık görevler");
    expect(markup).toContain("Tarihsiz açık görev");
    expect(markup).toContain("Rutinler");
    expect(markup).toContain("Bugünün rutini");
    expect(markup).not.toContain("Yarının rutini");
    expect(markup.match(/data-agenda-id="todo-1"/g)).toHaveLength(1);
    expect(markup).toContain('href="#/todos?focus=open-1"');
    expect(harness.queries[0].queryKey).toEqual(["today-agenda", localDateKey(new Date())]);
  });

  it("uses the existing owners for completion, planning, removal and settings", async () => {
    renderToStaticMarkup(<TodayAgendaWidget />);

    const complete = mutationNamed("today-complete");
    expect(complete).toBeDefined();
    await complete?.mutationFn?.(todoRow as never);
    expect(harness.apiPost).toHaveBeenCalledWith("/todos/todo-1/complete");
    await complete?.mutationFn?.(rssRow as never);
    expect(harness.apiPost).toHaveBeenCalledWith("/rss/items/rss-1/read");

    const schedule = mutationNamed("today-schedule");
    await schedule?.mutationFn?.({
      row: { ...todoRow, id: "suggested-1" },
      day: agenda.day,
      start: "10:15",
      duration: "45",
    } as never);
    expect(schedule).toBeDefined();
    expect(harness.apiPost).toHaveBeenCalledWith("/plan", {
      entity_id: "suggested-1",
      day: agenda.day,
      start_min: 615,
      duration_min: 45,
    });
    const remove = mutationNamed("today-remove");
    await remove?.mutationFn?.(rssRow as never);
    expect(harness.apiDel).toHaveBeenCalledWith("/plan/slot-rss");
    const toggleAuto = mutationNamed("today-auto");
    await toggleAuto?.mutationFn?.(false as never);
    expect(harness.apiPut).toHaveBeenCalledWith("/settings/today.auto_suggestions", { value: false });

    complete?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith(
      "todo.write",
      "plan.write",
      "rss.write",
      "media.write",
      "calendar.write",
    );
  });

  it("links planned media to its logging target without treating it as a todo", () => {
    const markup = renderToStaticMarkup(<TodayAgendaWidget />);

    expect(markup).toContain('href="#/media?focus=media-1"');
    expect(markup).toContain("120 / 400 sayfa");
    expect(markup).not.toContain("Dune tamamla");
  });

  it("does not duplicate open todos in suggestions and keeps completed rows collapsed", () => {
    render(<TodayAgendaWidget />);

    expect(screen.queryByText("Birinci öneri")).toBeNull();
    expect(screen.queryByText("İkinci öneri")).toBeNull();
    expect(screen.getByText("Üçüncü öneri")).toBeTruthy();

    const completedToggle = screen.getByRole("button", { name: /Tamamlananlar/ });
    expect(completedToggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByText("Biten görev")).toBeNull();

    fireEvent.click(completedToggle);
    expect(completedToggle.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("Biten görev")).toBeTruthy();
  });

  it("exposes a completion action on an actionable todo row", async () => {
    const { container } = render(<TodayAgendaWidget />);
    const todo = container.querySelector('[data-agenda-id="todo-1"]');

    expect(todo).not.toBeNull();
    fireEvent.click(within(todo as HTMLElement).getByRole("button", { name: "Tamamla" }));

    await waitFor(() => expect(harness.apiPost).toHaveBeenCalledWith("/todos/todo-1/complete"));
  });
});
