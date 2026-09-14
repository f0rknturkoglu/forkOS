import { appTimeParts, appWeekStartKey, isSameAppDay, keyToUtc, localDateKey } from "@/lib/date";
import type { ActivityEvent, PlanSlot, TodayAgenda, Todo } from "@/core/types";

type TodayPhase = "morning" | "afternoon" | "evening";

interface TodayStateInput {
  day: string;
  now: Date;
  slots: PlanSlot[];
  todos: Todo[];
  agenda?: TodayAgenda;
  reviewEvents: ActivityEvent[];
  weeklyReviews: { period_start: string }[];
}

/** Both Today widgets render the same operational state from shared inputs. */
export function deriveTodayState({ day, now, slots, todos, agenda, reviewEvents, weeklyReviews }: TodayStateInput) {
  const { hour } = appTimeParts(now);
  const phase: TodayPhase = hour >= 18 || hour < 4 ? "evening" : hour < 12 ? "morning" : "afternoon";
  const todaySlots = slots
    .filter((slot) => slot.day === day)
    .sort((a, b) => (a.start_min ?? 999) - (b.start_min ?? 999));
  const openTodoIds = new Set(
    todos.filter((todo) => todo.status === "open" || todo.status === "doing").map((todo) => todo.id),
  );
  const plannedTodos = todaySlots.filter((slot) => slot.entity_type === "todo" && openTodoIds.has(slot.entity_id));
  const overdue = todos.filter((todo) => todo.due_at && localDateKey(new Date(todo.due_at)) < day).length;
  const reviewDone = reviewEvents.some((event) => isSameAppDay(new Date(event.occurred_at), now));
  const weekStart = appWeekStartKey(now);
  const weekDay = keyToUtc(day).getUTCDay();
  const weeklyReviewDue =
    (weekDay === 0 || weekDay === 1) && !weeklyReviews.some((review) => review.period_start === weekStart);
  const calendarRows = (agenda?.timed ?? []).filter(
    (row) => row.kind === "calendar" && row.starts_at && localDateKey(new Date(row.starts_at)) === day,
  );
  const conflictCount = plannedTodos.reduce((count, slot) => {
    if (slot.start_min == null) return count;
    const slotEnd = slot.start_min + (slot.duration_min ?? 30);
    return (
      count +
      calendarRows.filter((row) => {
        const parts = appTimeParts(new Date(row.starts_at!));
        const eventStart = parts.hour * 60 + parts.minute;
        const eventEnd = eventStart + (row.duration_min ?? 30);
        return slot.start_min! < eventEnd && eventStart < slotEnd;
      }).length
    );
  }, 0);

  return {
    phase,
    phaseLabel: phase === "morning" ? "Sabah" : phase === "afternoon" ? "Gün içinde" : "Akşam",
    todaySlots,
    plannedTodos,
    overdue,
    reviewDone,
    weeklyReviewDue,
    conflictCount,
  };
}
