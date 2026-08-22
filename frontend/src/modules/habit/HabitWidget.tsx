import { useMutation, useQuery } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { Empty, RowList, Section, cx } from "@/core/ui";
import type { Habit, HabitGridEntry } from "@/core/types";
import { useInvalidate, useOnline } from "@/lib/hooks";
import { HabitStrip, localDay } from "./HabitStrip";

/**
 * Bugun panelindeki aliskanliklar: bugunu isaretle + son iki haftanin ritmi.
 *
 * Serit burada da tiklanabilir -- dun isaretlemeyi unutmussan Aliskanliklar
 * sayfasina gitmen gerekmiyor.
 */
export function HabitWidget() {
  const online = useOnline();
  const invalidate = useInvalidate();

  const { data: habits = [] } = useQuery({
    queryKey: ["habits", false],
    queryFn: () => api.get<Habit[]>("/habits"),
  });
  const { data: grid = [] } = useQuery({
    queryKey: ["habits-grid"],
    queryFn: () => api.get<HabitGridEntry[]>("/habits/grid?weeks=3"),
  });

  const check = useMutation({
    mutationFn: (habit: Habit) =>
      api.post(`/habits/${habit.id}/check`, { day: localDay(), done: !habit.done_today }),
    onSuccess: () => invalidate("habits", "habits-grid", "activity"),
  });

  const doneByHabit = grid.reduce<Record<string, Set<string>>>((acc, entry) => {
    if (entry.done) (acc[entry.habit_id] ??= new Set()).add(entry.day);
    return acc;
  }, {});
  const doneToday = habits.filter((habit) => habit.done_today).length;

  return (
    <Section
      title="Alışkanlıklar"
      hint={habits.length > 0 ? `${doneToday}/${habits.length}` : undefined}
      action={
        <button type="button" onClick={() => navigate("/habits")}
          className="text-meta text-muted hover:text-primary">tümü →</button>
      }
    >
      {habits.length === 0 ? (
        <Empty>Henüz alışkanlık yok.</Empty>
      ) : (
        <RowList as="ul">
          {habits.map((habit) => (
            <li key={habit.id} className="py-2">
              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  disabled={!online}
                  onClick={() => check.mutate(habit)}
                  aria-label={habit.done_today ? "Bugünü geri al" : "Bugünü işaretle"}
                  title={habit.done_today ? "Bugünü geri al" : "Bugünü işaretle"}
                  className={cx(
                    "flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border transition",
                    habit.done_today
                      ? "border-ok bg-ok text-canvas"
                      : "border-strong text-transparent hover:border-accent hover:text-accent",
                  )}
                >
                  <Check size={12} strokeWidth={3} />
                </button>
                <span className={cx("min-w-0 flex-1 truncate text-body",
                  habit.done_today ? "text-muted" : "text-primary")}>
                  {habit.title}
                </span>
                <span className={cx("shrink-0 text-meta tabular-nums",
                  habit.week_done >= habit.target_per_week ? "text-ok" : "text-muted")}>
                  {habit.week_done}/{habit.target_per_week}
                </span>
              </div>
              <div className="mt-1.5 pl-7">
                <HabitStrip habitId={habit.id} done={doneByHabit[habit.id] ?? new Set()}
                  days={14} size="sm" />
              </div>
            </li>
          ))}
        </RowList>
      )}
    </Section>
  );
}
