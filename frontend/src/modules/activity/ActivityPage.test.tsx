// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ActivityPage } from "./ActivityPage";

type QueryOptions = { queryKey: readonly unknown[] };

const activityEvents = [
  {
    id: 2,
    entity_id: "entity-2",
    entity_type: "todo",
    verb: "todo.completed",
    payload: { title: "Bugünün işi" },
    occurred_at: "2026-08-25T10:00:00.000Z",
  },
  {
    id: 1,
    entity_id: "entity-1",
    entity_type: "todo",
    verb: "todo.created",
    payload: { title: "Dünün işi" },
    occurred_at: "2026-08-24T10:00:00.000Z",
  },
];

const problemSource = {
  source: "Haberler",
  status: "error" as const,
  items_found: 0,
  error: "Bağlantı zaman aşımına uğradı",
  started_at: "2026-08-25T08:00:00.000Z",
  finished_at: null,
};

vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn((options: QueryOptions) => (
    options.queryKey[0] === "activity"
      ? { data: activityEvents, isLoading: false }
      : { data: [problemSource], isLoading: false }
  )),
}));

vi.mock("./Heatmap", () => ({
  Heatmap: () => <p>Emek haritası</p>,
}));

afterEach(cleanup);

describe("ActivityPage", () => {
  it("keeps the newest day open while history and source health are collapsed", () => {
    const { container } = render(<ActivityPage />);

    expect(screen.queryByText("Emek haritası")).toBeNull();
    const days = [...container.querySelectorAll("details[data-activity-day]")];
    expect(days).toHaveLength(2);
    expect(days[0].hasAttribute("open")).toBe(true);
    expect(days[1].hasAttribute("open")).toBe(false);
    expect(container.querySelector("details[data-source-health]")?.hasAttribute("open")).toBe(false);
  });

  it("expands and collapses every visible day with the contextual control", () => {
    const { container } = render(<ActivityPage />);
    const days = [...container.querySelectorAll("details[data-activity-day]")];

    fireEvent.click(screen.getByRole("button", { name: "Tümünü genişlet" }));
    expect(days.every((day) => day.hasAttribute("open"))).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "Tümünü daralt" }));
    expect(days.every((day) => !day.hasAttribute("open"))).toBe(true);
  });
});
