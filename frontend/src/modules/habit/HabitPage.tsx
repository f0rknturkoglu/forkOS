import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Button, Empty, Panel, cx } from "@/core/ui";
import type { Habit, HabitGridEntry } from "@/core/types";
import { useInvalidate, useOnline } from "@/lib/hooks";

function days(count: number) {
  return Array.from({ length: count }, (_, index) => {
    const day = new Date(); day.setDate(day.getDate() - (count - index - 1));
    return day.toISOString().slice(0, 10);
  });
}

export function HabitPage() {
  const [title, setTitle] = useState(""); const online = useOnline(); const invalidate = useInvalidate();
  const { data: habits = [] } = useQuery({ queryKey: ["habits"], queryFn: () => api.get<Habit[]>("/habits") });
  const { data: grid = [] } = useQuery({ queryKey: ["habits-grid"],
    queryFn: () => api.get<HabitGridEntry[]>("/habits/grid?weeks=8") });
  const refresh = () => invalidate("habits", "habits-grid", "activity", "review-preview");
  const create = useMutation({ mutationFn: () => api.post("/habits", { title }),
    onSuccess: () => { setTitle(""); refresh(); } });
  const check = useMutation({ mutationFn: ({ id, done, day }: { id: string; done: boolean; day?: string }) =>
    api.post(`/habits/${id}/check`, { day: day || new Date().toISOString().slice(0, 10), done }), onSuccess: refresh });
  const allDays = days(56); const done = new Set(grid.filter((entry) => entry.done).map((entry) => `${entry.habit_id}:${entry.day}`));
  return <div className="space-y-4 p-6"><header>
    <p className="text-meta text-muted">Rozet yok, ceza yok; yalnızca sakin bir ritim görünümü.</p></header>
    <Panel title="Yeni habit"><form className="flex gap-2" onSubmit={(event) => { event.preventDefault(); if (title.trim()) create.mutate(); }}>
      <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Orn. 20 dk oku"
        className="flex-1 rounded border border-strong bg-canvas px-3 py-2 text-body" />
      <Button type="submit" variant="primary" disabled={!online || !title.trim()}>ekle</Button></form></Panel>
    {habits.length === 0 ? <Panel><Empty>Takip edilen habit yok.</Empty></Panel> : habits.map((habit) => <Panel key={habit.id}
      title={<span className="flex items-center gap-2"><button disabled={!online}
        onClick={() => check.mutate({ id: habit.id, done: !habit.done_today })}
        className={cx("h-4 w-4 rounded border", habit.done_today ? "border-ok-border bg-ok" : "border-strong")} />
        {habit.title}</span>} action={<span className="text-meta text-muted">{habit.streak} gun</span>}>
      <div className="grid grid-flow-col grid-rows-7 gap-1 overflow-x-auto">
        {allDays.map((day) => { const checked = done.has(`${habit.id}:${day}`); return <button key={day}
          title={`${day}${checked ? " · tamam" : ""}`} disabled={!online}
          onClick={() => check.mutate({ id: habit.id, day, done: !checked })}
          className={cx("h-3 w-3 rounded-sm bg-surface-sunken", checked && "bg-ok", day === new Date().toISOString().slice(0, 10) && "ring-1 ring-accent")} />; })}
      </div></Panel>)}
  </div>;
}
