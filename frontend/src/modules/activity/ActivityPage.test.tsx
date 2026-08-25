// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ActivityEvent } from "@/core/types";
import { ActivityPage } from "./ActivityPage";

type QueryOptions = { queryKey: readonly unknown[] };

let activityEvents: ActivityEvent[] = [
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
  useQuery: vi.fn((options: QueryOptions) =>
    options.queryKey[0] === "activity"
      ? { data: activityEvents, isLoading: false }
      : { data: [problemSource], isLoading: false },
  ),
}));

vi.mock("./Heatmap", () => ({
  Heatmap: () => <p>Emek haritası</p>,
}));

afterEach(cleanup);

function event(overrides: Partial<ActivityEvent> = {}): ActivityEvent {
  return {
    id: 99,
    entity_id: "entity-99",
    entity_type: "todo",
    verb: "todo.created",
    payload: { title: "Yeni iş" },
    occurred_at: "2026-08-25T10:00:00.000Z",
    ...overrides,
  };
}

afterEach(() => {
  activityEvents = [
    event({
      id: 2,
      entity_id: "entity-2",
      verb: "todo.completed",
      payload: { title: "Bugünün işi" },
      occurred_at: "2026-08-25T10:00:00.000Z",
    }),
    event({
      id: 1,
      entity_id: "entity-1",
      verb: "todo.created",
      payload: { title: "Dünün işi" },
      occurred_at: "2026-08-24T10:00:00.000Z",
    }),
  ];
});

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

  it("keeps a failed source sync when filtering to alerts", () => {
    activityEvents = [
      event({
        id: 3,
        verb: "source_sync.completed",
        payload: { errors: 2 },
        occurred_at: "2026-08-25T11:00:00.000Z",
      }),
      event({ id: 4, payload: { title: "Normal hareket" } }),
    ];

    render(<ActivityPage />);
    fireEvent.click(screen.getByRole("button", { name: "Sadece uyarılar" }));

    expect(screen.getByText("Kaynak senkronizasyonu tamamlandı")).toBeTruthy();
    expect(screen.queryByText("Görev oluşturuldu — Normal hareket")).toBeNull();
  });

  it("keeps matching month and day from different years in separate disclosures", () => {
    activityEvents = [
      event({ id: 5, occurred_at: "2026-08-25T10:00:00.000Z" }),
      event({ id: 6, occurred_at: "2015-08-25T10:00:00.000Z" }),
    ];

    const { container } = render(<ActivityPage />);

    expect(container.querySelectorAll("details[data-activity-day]")).toHaveLength(2);
  });

  it("clears stale open days across alert filter transitions and opens the newest visible day", () => {
    activityEvents = [
      event({ id: 7, payload: { title: "Yeni normal" }, occurred_at: "2026-08-25T10:00:00.000Z" }),
      event({
        id: 8,
        verb: "source.stalled",
        payload: { title: "Eski uyarı" },
        occurred_at: "2026-08-24T10:00:00.000Z",
      }),
    ];

    const { container } = render(<ActivityPage />);
    fireEvent.click(screen.getByRole("button", { name: "Sadece uyarılar" }));
    let days = [...container.querySelectorAll("details[data-activity-day]")];
    expect(days).toHaveLength(1);
    expect(days[0].hasAttribute("open")).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "Sadece uyarılar" }));
    days = [...container.querySelectorAll("details[data-activity-day]")];
    expect(days).toHaveLength(2);
    expect(days[0].hasAttribute("open")).toBe(false);
    expect(days[1].hasAttribute("open")).toBe(true);
  });

  it("updates an individual day from its native disclosure toggle", () => {
    const { container } = render(<ActivityPage />);
    const days = [...container.querySelectorAll("details[data-activity-day]")];

    (days[1] as HTMLDetailsElement).open = true;
    days[1].dispatchEvent(new Event("toggle", { bubbles: true }));

    expect(days[1].hasAttribute("open")).toBe(true);
  });
});
