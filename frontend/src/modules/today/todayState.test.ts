import { describe, expect, it } from "vitest";
import { deriveTodayState } from "./todayState";

describe("deriveTodayState", () => {
  it("both Today surfaces share phase, due-state and calendar conflict derivation", () => {
    const state = deriveTodayState({
      day: "2026-08-30",
      now: new Date("2026-08-30T06:00:00Z"), // Istanbul 09:00, Sunday
      slots: [
        { id: "slot-1", entity_id: "todo-1", entity_type: "todo", day: "2026-08-30", start_min: 600, duration_min: 30 },
      ],
      todos: [
        { id: "todo-1", status: "open", due_at: "2026-08-29T09:00:00Z" },
        { id: "done", status: "done", due_at: "2026-08-28T09:00:00Z" },
      ],
      agenda: {
        day: "2026-08-30",
        auto_suggestions: true,
        timed: [
          {
            id: "calendar-1",
            kind: "calendar",
            source: "calendar",
            title: "Toplantı",
            starts_at: "2026-08-30T07:15:00Z",
            duration_min: 30,
            completed: false,
            read_only: true,
            context_only: false,
            children: [],
          },
        ],
        checklist: [],
        completed: [],
        suggestions: { todos: [], rss: [], media: [], flashcards: [], study: [], career: [] },
      },
      reviewEvents: [],
      weeklyReviews: [],
    } as never);

    expect(state.phase).toBe("morning");
    expect(state.plannedTodos).toHaveLength(1);
    expect(state.overdue).toBe(2);
    expect(state.weeklyReviewDue).toBe(true);
    expect(state.conflictCount).toBe(1);
  });
});
