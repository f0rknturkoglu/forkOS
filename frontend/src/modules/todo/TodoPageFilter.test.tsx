// @vitest-environment jsdom
/**
 * Faz 9: ?planned=today URL filtresi -- bugune (veya yarina) planlanmis
 * gorevler listelenir; plan_slot'u olmayanlar gizlenir.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TodoPage } from "./TodoPage";

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
vi.mock("@/app/router", () => ({
  navigate: vi.fn(),
  useHashRoute: () => ({ path: "/todos", params: new URLSearchParams("planned=today") }),
}));

import { api } from "@/core/api";

const apiGet = vi.mocked(api.get);

const todayKey = () => new Date().toLocaleDateString("sv-SE");
const tomorrowKey = () => new Date(Date.now() + 86_400_000).toLocaleDateString("sv-SE");

function makeTodo(id: string, plannedDay: string | null) {
  return {
    id,
    title: `Görev ${id}`,
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
    planned_day: plannedDay,
    planned_start_min: null,
  };
}

beforeEach(() => {
  apiGet.mockReset();
  apiGet.mockImplementation(async (path: string) => {
    if (path === "/todos") {
      return [
        makeTodo("a", todayKey()),
        makeTodo("b", tomorrowKey()),
        makeTodo("c", null),
        makeTodo("d", "2020-01-01"),
      ];
    }
    if (path === "/tags") return [];
    return {};
  });
});
afterEach(cleanup);

describe("TodoPage ?planned=today", () => {
  it("bugun ve yarin planli gorevleri gosterir, plansizlari gizler", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <TodoPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Görev a")).toBeTruthy();
    expect(screen.getByText("Görev b")).toBeTruthy();
    expect(screen.queryByText("Görev c")).toBeNull();
    // Gecmis plan (backend donmese de) filtreye girmez.
    expect(screen.queryByText("Görev d")).toBeNull();
  });
});
