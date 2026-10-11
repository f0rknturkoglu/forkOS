// @vitest-environment jsdom

import { renderToStaticMarkup } from "react-dom/server";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AgendaRow, TodayAgenda, Todo } from "@/core/types";
import { appLocalToUtc, localDateKey, tomorrowKey } from "@/lib/date";
import { hydrateEntityRegistry } from "@/core/entityRegistry";
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
  progress_label: null,
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
      progress_label: null,
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
const routineRow: AgendaRow = {
  ...todoRow,
  source: "routine",
  id: "routine-today",
  title: "Bugünün rutini",
  recur: "daily",
};
const plannedTodoRow: AgendaRow = {
  ...todoRow,
  id: "planned-todo-1",
  slot_id: "slot-planned-todo",
  title: "Planlı görev",
  source: "planned",
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
  checklist: [parent, todoRow, plannedTodoRow, routineRow, rssRow],
  completed: [{ ...todoRow, id: "completed-1", title: "Biten görev", completed: true, action: null }],
  suggestions: {
    flashcards: [],
    todos: [
      { ...todoRow, id: "suggested-1", title: "Birinci öneri", source: "suggestion" },
      { ...todoRow, id: "suggested-2", title: "İkinci öneri", source: "suggestion" },
    ],
    rss: [{ ...rssRow, id: "suggested-rss-1", title: "Üçüncü öneri", source: "suggestion" }],
    study: [
      {
        ...todoRow,
        kind: "study",
        id: "study-1",
        title: "Tekrar edilecek konu",
        source: "suggestion",
        read_only: true,
        action: null,
      },
    ],
    career: [],
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

  it("uses the existing owners for completion, removal and planning", async () => {
    renderToStaticMarkup(<TodayAgendaWidget />);

    const complete = mutationNamed("today-complete");
    expect(complete).toBeDefined();
    await complete?.mutationFn?.(todoRow as never);
    expect(harness.apiPost).toHaveBeenCalledWith("/todos/todo-1/complete");
    await complete?.mutationFn?.(rssRow as never);
    expect(harness.apiPost).toHaveBeenCalledWith("/rss/items/rss-1/read");

    const remove = mutationNamed("today-remove");
    await remove?.mutationFn?.(rssRow as never);
    expect(harness.apiDel).toHaveBeenCalledWith("/plan/slot-rss");

    // Otomatik mod kaldirildi (§20): ayar ucu UI'dan cagrilmaz.
    expect(mutationNamed("today-auto")).toBeUndefined();
    expect(mutationNamed("today-schedule")).toBeUndefined();

    complete?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("todo.write", "plan.write", "rss.write", "calendar.write");
  });

  it("shows no automatic suggestion surface", () => {
    const markup = renderToStaticMarkup(<TodayAgendaWidget />);

    expect(markup).not.toContain("Öneriler");
    expect(markup).not.toContain("Devam edenler");
    expect(markup).not.toContain("oto ");
    expect(markup).not.toContain("Birinci öneri");
    expect(markup).not.toContain("Tekrar edilecek konu");
  });

  it("keeps completed rows collapsed until asked", () => {
    render(<TodayAgendaWidget />);

    const completedToggle = screen.getByRole("button", { name: /Tamamlananlar/ });
    expect(completedToggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByText("Biten görev")).toBeNull();

    fireEvent.click(completedToggle);
    expect(completedToggle.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("Biten görev")).toBeTruthy();
  });

  it("uses entity navigation targets for interview rows and labels tomorrow", () => {
    const originalTimed = agenda.timed;
    hydrateEntityRegistry([
      {
        type: "opportunity",
        label: "Fırsat",
        label_plural: "Fırsatlar",
        route: "/opportunities?focus={id}",
        icon: "Target",
        searchable: true,
        linkable: true,
      },
    ]);
    agenda.timed = [
      ...originalTimed,
      {
        ...todoRow,
        kind: "interview",
        id: "interview-row",
        entity_id: "opportunity-target",
        entity_type: "opportunity",
        title: "Görüşme satırı",
        action: null,
        read_only: true,
        starts_at: appLocalToUtc(tomorrowKey(), 9, 0),
      },
    ];
    try {
      const markup = renderToStaticMarkup(<TodayAgendaWidget />);
      expect(markup).toContain('href="#/opportunities?focus=opportunity-target"');
      expect(markup).not.toContain("focus=interview-row");
      expect(markup).toContain("Yarın 09:00");
    } finally {
      agenda.timed = originalTimed;
      hydrateEntityRegistry([]);
    }
  });

  it("exposes a completion action on an actionable todo row", async () => {
    const { container } = render(<TodayAgendaWidget />);
    const todo = container.querySelector('[data-agenda-id="todo-1"]');

    expect(todo).not.toBeNull();
    fireEvent.click(within(todo as HTMLElement).getByRole("button", { name: "Tamamla" }));

    await waitFor(() => expect(harness.apiPost).toHaveBeenCalledWith("/todos/todo-1/complete"));
  });

  it("creates a todo through the canonical createTask path with plan_day=today", async () => {
    render(<TodayAgendaWidget />);

    const input = screen.getByPlaceholderText("Bugüne hızlı görev ekle... (Enter ile kaydet)");
    const submitBtn = screen.getByRole("button", { name: "Ekle" });

    fireEvent.change(input, { target: { value: "Yeni acil görev" } });
    fireEvent.click(submitBtn);

    const createMutation = mutationNamed("today-create-todo");
    expect(createMutation).toBeDefined();
    await createMutation?.mutationFn?.("Yeni acil görev" as never);
    expect(harness.apiPost).toHaveBeenCalledWith("/todos", {
      title: "Yeni acil görev",
      plan_day: localDateKey(new Date()),
      priority: 2,
    });

    createMutation?.onSuccess?.();
    expect(harness.invalidate).toHaveBeenCalledWith("todo.write", "plan.write");
  });

  it("deletes a todo directly from the agenda row", async () => {
    const { container } = render(<TodayAgendaWidget />);
    const todo = container.querySelector('[data-agenda-id="todo-1"]');

    expect(todo).not.toBeNull();
    const deleteBtn = within(todo as HTMLElement).getByRole("button", { name: "Görevi sil" });
    fireEvent.click(deleteBtn);

    const deleteMutation = mutationNamed("today-delete-todo");
    expect(deleteMutation).toBeDefined();
    await deleteMutation?.mutationFn?.("todo-1" as never);
    expect(harness.apiDel).toHaveBeenCalledWith("/todos/todo-1");
  });

  it("removes a planned todo from today without deleting the todo", async () => {
    const { container } = render(<TodayAgendaWidget />);
    const todo = container.querySelector('[data-agenda-id="planned-todo-1"]');

    expect(todo).not.toBeNull();
    fireEvent.click(within(todo as HTMLElement).getByRole("button", { name: "Bugünden çıkar" }));

    await waitFor(() => expect(harness.apiDel).toHaveBeenCalledWith("/plan/slot-planned-todo"));
    expect(harness.apiDel).not.toHaveBeenCalledWith("/todos/planned-todo-1");
  });

  it("renders unified day rhythm summary banner", () => {
    const markup = renderToStaticMarkup(<TodayAgendaWidget />);

    expect(markup).toContain("planlı");
    expect(markup).toContain("geciken");
  });
});
