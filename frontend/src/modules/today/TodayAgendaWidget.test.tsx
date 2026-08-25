import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AgendaRow, TodayAgenda } from "@/core/types";
import { localDay, TodayAgendaWidget } from "./TodayAgendaWidget";

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
  checklist: [parent, todoRow, rssRow, mediaRow],
  completed: [],
  suggestions: {
    todos: [{ ...todoRow, id: "suggested-1", source: "suggestion" }],
    rss: [],
    media: [],
  },
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
    return { mutate: vi.fn(), isPending: false };
  }),
  useQuery: vi.fn((options: QueryOptions) => {
    harness.queries.push(options);
    return options.queryKey[0] === "today-agenda"
      ? { data: agenda, isLoading: false, isError: false, refetch: vi.fn() }
      : { data: [], isLoading: false, isError: false, refetch: vi.fn() };
  }),
}));

function mutationNamed(name: string) {
  return harness.mutations.find((mutation) => mutation.mutationKey?.[0] === name);
}

describe("unified Today agenda", () => {
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

    expect(markup).toContain("Günün akışı");
    expect(markup).not.toContain("Bugünün programı");
    expect(markup).not.toContain("Bugünün görevleri");
    expect(markup).not.toContain("Bugünün planı");
    expect(markup.indexOf("Ana görev")).toBeLessThan(markup.indexOf("Alt görev"));
    expect(markup.match(/data-agenda-id="child-1"/g)).toHaveLength(1);
    expect(harness.queries[0].queryKey).toEqual(["today-agenda", localDay()]);
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
});
