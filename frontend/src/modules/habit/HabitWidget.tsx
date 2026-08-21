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
  return <Panel title="Alışkanlıklar" action={<button onClick={() => navigate("/habits")}
    className="text-meta text-muted hover:text-primary">takvim →</button>}>
    {habits.length === 0 ? <Empty>Henüz alışkanlık yok.</Empty> : <ul className="space-y-2">{habits.map((habit) =>
      <li key={habit.id} className="flex items-center gap-2 text-body"><button disabled={!online}
        onClick={() => check.mutate(habit)} className={cx("h-4 w-4 rounded border",
          habit.done_today ? "border-ok-border bg-ok" : "border-strong")} />
        <span className={habit.done_today ? "text-muted" : ""}>{habit.title}</span>
        <span className="ml-auto text-[10.5px] text-muted">{habit.streak}</span></li>)}</ul>}
  </Panel>;
}
