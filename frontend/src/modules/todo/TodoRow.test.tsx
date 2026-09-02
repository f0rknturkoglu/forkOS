// @vitest-environment jsdom
/**
 * Faz 9: plan cipi + "bugune tarihle" aksiyonu.
 * Plan (plan_slot) ile son tarih (due_at) ayri kavramlar olarak test edilir.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TodoRow } from "./TodoRow";
import { planLabel } from "./priority";
import { POMODORO_OPEN_EVENT, type PomodoroOpenRequest } from "@/modules/pomodoro/dock";

vi.mock("@/core/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    del: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
  },
  qs: vi.fn(() => ""),
}));
vi.mock("@/core/invalidation", () => ({ invalidateAfter: vi.fn() }));
vi.mock("@/lib/hooks", () => ({ useOnline: () => true }));
vi.mock("@/core/dialog", () => ({
  confirmDialog: () => Promise.resolve(true),
}));

import { api } from "@/core/api";

const apiPatch = vi.mocked(api.patch);

/** Yerel bugun anahtari -- planLabel'in kullandigi gune esit olmali. */
const todayKey = () => new Date().toLocaleDateString("sv-SE");

type TodoRowTestTodo = {
  id: string;
  title: string;
  description: null;
  priority: number;
  status: "open" | "doing" | "done" | "dropped";
  due_at: string | null;
  reminder_at: string | null;
  completed_at: null;
  parent_id: null;
  position: number;
  tags: string[];
  recur: string | null;
  project_id: null;
  project_title: null;
  milestone_id: null;
  milestone_title: null;
  subtask_total: number;
  subtask_done: number;
  planned_day: string | null;
  planned_start_min: number | null;
};

function baseTodo(overrides: Record<string, unknown> = {}): TodoRowTestTodo {
  return {
    id: "t-1",
    title: "Test görevi",
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
    ...overrides,
  };
}

function renderRow(todo: TodoRowTestTodo) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <TodoRow todo={todo} onChange={() => {}} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiPatch.mockReset();
  apiPatch.mockResolvedValue({} as never);
});

describe("rutin kontrolleri (Faz 24)", () => {
  it("rutin gorev 'her gun' + sonraki tarih gosterir ve 'Rutini durdur' sunar", () => {
    const todo = {
      id: "r1",
      title: "Su iç",
      description: null,
      priority: 2,
      status: "open" as const,
      due_at: "2026-08-31T08:00:00Z",
      reminder_at: null,
      completed_at: null,
      parent_id: null,
      position: 0,
      tags: [],
      recur: "daily",
      planned_day: null,
      planned_start_min: null,
      project_id: null,
      project_title: null,
      milestone_id: null,
      milestone_title: null,
      subtask_total: 0,
      subtask_done: 0,
    };
    renderRow(todo);
    expect(screen.getByText("her gün")).toBeTruthy();
    expect(screen.getByTitle(/Rutin — sonraki/)).toBeTruthy();
    expect(screen.getByTitle("Rutini durdur")).toBeTruthy();
  });

  it("rutini durdurma PATCH recur:'' ile olur (gorev silinmez)", async () => {
    const todo = {
      id: "r2",
      title: "Koşu",
      description: null,
      priority: 2,
      status: "open" as const,
      due_at: "2026-08-31T08:00:00Z",
      reminder_at: null,
      completed_at: null,
      parent_id: null,
      position: 0,
      tags: [],
      recur: "weekly",
      planned_day: null,
      planned_start_min: null,
      project_id: null,
      project_title: null,
      milestone_id: null,
      milestone_title: null,
      subtask_total: 0,
      subtask_done: 0,
    };
    renderRow(todo);
    fireEvent.click(screen.getByTitle("Rutini durdur"));
    await waitFor(() => expect(apiPatch).toHaveBeenCalledWith("/todos/r2", { recur: "" }));
  });
});

afterEach(cleanup);

describe("planLabel", () => {
  it("bugun planli ve saat gosterir", () => {
    const label = planLabel(todayKey(), 14 * 60 + 30);
    expect(label?.text).toBe("bugün planlı 14:30");
    expect(label?.tone).toBe("accent");
  });

  it("yarin icin ayri etiket", () => {
    const tomorrow = new Date(Date.now() + 86_400_000).toLocaleDateString("sv-SE");
    const label = planLabel(tomorrow, null);
    expect(label?.text).toBe("yarın planlı");
    expect(label?.tone).toBe("muted");
  });

  it("gecmis plan uyari tonu alir", () => {
    const label = planLabel("2020-01-01", null);
    expect(label?.text).toBe("gecikmiş plan");
    expect(label?.tone).toBe("warn");
  });
});

describe("TodoRow plan bilgisi", () => {
  it("planli gorevde plan cipi gorunur, son tarih yokken due cipi cikmaz", () => {
    renderRow(baseTodo({ planned_day: todayKey(), planned_start_min: 9 * 60 }));
    expect(screen.getByText(/bugün planlı 09:00/)).toBeTruthy();
    // due_at bos: due cipi yok; plan cipi "son tarih degil" aciklamali.
    expect(screen.queryByText(/bugün 09:00/)).toBeNull();
    expect(screen.getByTitle("Plana alındı — son tarih değil")).toBeTruthy();
  });

  it("'bugune tarihle' due_at yazar (PATCH), plana dokunmaz", async () => {
    renderRow(baseTodo());
    const dueButton = screen.getByTitle("Son tarih ver (bugün) — plan değil");
    fireEvent.click(dueButton);

    await waitFor(() => expect(apiPatch).toHaveBeenCalledTimes(1));
    const [url, body] = apiPatch.mock.calls[0] as [string, { due_at: string }];
    expect(url).toBe("/todos/t-1");
    expect(new Date(body.due_at).toISOString().slice(0, 10)).toBe(todayKey());
  });

  it("due_at varsa 'bugune tarihle' gosterilmez", () => {
    renderRow(baseTodo({ due_at: new Date().toISOString() }));
    expect(screen.queryByTitle("Son tarih ver (bugün) — plan değil")).toBeNull();
  });
});

describe("TodoRow kaynak entegrasyonlari", () => {
  it("learning'den gelen gorevin basligini asil konu agacina baglar", () => {
    renderRow(
      baseTodo({
        title: "Git Temelleri",
        learning_topic_id: "topic-42",
        learning_topic_title: "Git Temelleri",
      }),
    );

    const link = screen.getByRole("link", { name: "Git Temelleri" });
    expect(link.getAttribute("href")).toBe("#/learning?focus=topic-42");
    expect(screen.getByText("Öğrenme")).toBeTruthy();
  });

  it("odak aksiyonu sayfa degistirmek yerine global Pomodoro'yu baglamla acar", () => {
    let detail: PomodoroOpenRequest | undefined;
    const listener = (event: Event) => {
      detail = (event as CustomEvent<PomodoroOpenRequest>).detail;
    };
    window.addEventListener(POMODORO_OPEN_EVENT, listener);
    renderRow(baseTodo({ id: "todo-42", title: "Git çalış" }));

    fireEvent.click(screen.getByTitle("Odaklan — pomodoro seçeneklerini aç"));
    expect(detail).toEqual({ context: "todo-42", topic: "Git çalış" });
    window.removeEventListener(POMODORO_OPEN_EVENT, listener);
  });
});
