import { useMutation, useQuery } from "@tanstack/react-query";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { Empty, Panel, cx } from "@/core/ui";
import type { Habit } from "@/core/types";
import { useInvalidate, useOnline } from "@/lib/hooks";

export function HabitWidget() {
  const online = useOnline(); const invalidate = useInvalidate();
  const { data: habits = [] } = useQuery({ queryKey: ["habits"], queryFn: () => api.get<Habit[]>("/habits") });
  const check = useMutation({ mutationFn: (habit: Habit) => api.post(`/habits/${habit.id}/check`, {
    day: new Date().toISOString().slice(0, 10), done: !habit.done_today }),
    onSuccess: () => invalidate("habits", "habits-grid", "activity") });
  return <Panel title="Habits" action={<button onClick={() => navigate("/habits")}
    className="text-xs text-neutral-500 hover:text-neutral-300">grid →</button>}>
    {habits.length === 0 ? <Empty>Habit yok.</Empty> : <ul className="space-y-2">{habits.map((habit) =>
      <li key={habit.id} className="flex items-center gap-2 text-sm"><button disabled={!online}
        onClick={() => check.mutate(habit)} className={cx("h-4 w-4 rounded border",
          habit.done_today ? "border-emerald-700 bg-emerald-800" : "border-neutral-600")} />
        <span className={habit.done_today ? "text-neutral-500" : ""}>{habit.title}</span>
        <span className="ml-auto text-[10px] text-neutral-600">{habit.streak}</span></li>)}</ul>}
  </Panel>;
}
