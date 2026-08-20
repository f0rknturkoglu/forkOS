import { useMemo, useState } from "react";
import { DndContext, type DragEndEvent, useDraggable, useDroppable } from "@dnd-kit/core";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Button, Empty, Panel, cx } from "@/core/ui";
import type { PlanSlot, Todo } from "@/core/types";
import { useInvalidate, useOnline } from "@/lib/hooks";

function isoDay(date: Date) { return date.toISOString().slice(0, 10); }
function monday(value = new Date()) {
  const copy = new Date(value); copy.setHours(12, 0, 0, 0);
  copy.setDate(copy.getDate() - ((copy.getDay() + 6) % 7)); return copy;
}

function DraggableCard({ id, title, muted = false }: { id: string; title: string; muted?: boolean }) {
  const drag = useDraggable({ id });
  return <button ref={drag.setNodeRef} {...drag.listeners} {...drag.attributes}
    style={{ transform: drag.transform ? `translate(${drag.transform.x}px,${drag.transform.y}px)` : undefined }}
    className={cx("w-full cursor-grab rounded border border-neutral-700 bg-neutral-900 p-2 text-left text-xs shadow",
      muted && "border-neutral-800 text-neutral-500", drag.isDragging && "z-20 opacity-70")}>
    {title}
  </button>;
}

function DayColumn({ day, slots }: { day: Date; slots: PlanSlot[] }) {
  const drop = useDroppable({ id: `day:${isoDay(day)}` });
  return <div ref={drop.setNodeRef} className={cx("min-h-72 rounded border border-neutral-800 p-2",
    drop.isOver && "border-sky-700 bg-sky-950/20")}>
    <div className="mb-2 text-xs font-medium"><span>{day.toLocaleDateString("tr-TR", { weekday: "short" })}</span>
      <span className="ml-1 text-neutral-600">{day.getDate()}</span></div>
    <div className="space-y-2">{slots.map((slot) => <DraggableCard key={slot.id}
      id={`slot:${slot.id}`} title={`${slot.start_min != null ? `${String(Math.floor(slot.start_min / 60)).padStart(2, "0")}:${String(slot.start_min % 60).padStart(2, "0")} · ` : ""}${slot.title}`} />)}</div>
  </div>;
}

export function WeeklyPlannerPage() {
  const [week, setWeek] = useState(() => monday());
  const online = useOnline(); const invalidate = useInvalidate();
  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => {
    const day = new Date(week); day.setDate(week.getDate() + i); return day;
  }), [week]);
  const { data: slots = [] } = useQuery({ queryKey: ["plan", isoDay(week)],
    queryFn: () => api.get<PlanSlot[]>(`/plan${qs({ week: isoDay(week) })}`) });
  const { data: todos = [] } = useQuery({ queryKey: ["todos", "planner"],
    queryFn: () => api.get<Todo[]>("/todos?status=open&limit=100") });
  const move = useMutation({ mutationFn: ({ active, target }: { active: string; target: string }) => {
    const day = target.replace("day:", "");
    if (active.startsWith("slot:")) return api.patch(`/plan/${active.replace("slot:", "")}`, { day });
    return api.post("/plan", { entity_id: active.replace("todo:", ""), day });
  }, onSuccess: () => invalidate("plan", "activity") });
  function onDragEnd(event: DragEndEvent) {
    if (!event.over || !online) return;
    move.mutate({ active: String(event.active.id), target: String(event.over.id) });
  }
  function shift(days: number) { const next = new Date(week); next.setDate(next.getDate() + days); setWeek(next); }
  const planned = new Set(slots.map((slot) => slot.entity_id));
  return <DndContext onDragEnd={onDragEnd}>
    <div className="space-y-4 p-6">
      <header className="flex flex-wrap items-center justify-between gap-3"><div>
        <h1 className="text-xl font-semibold">Weekly Planner</h1>
        <p className="text-xs text-neutral-500">Kartlari haftaya surukle; plan slotlari tum entity turlerini destekler.</p>
      </div><div className="flex gap-1"><Button onClick={() => shift(-7)}>←</Button>
        <Button onClick={() => setWeek(monday())}>bu hafta</Button><Button onClick={() => shift(7)}>→</Button></div></header>
      <div className="grid gap-2 overflow-x-auto sm:grid-cols-2 lg:grid-cols-7">
        {days.map((day) => <DayColumn key={isoDay(day)} day={day}
          slots={slots.filter((slot) => slot.day === isoDay(day))} />)}
      </div>
      <Panel title="Planlanmamis gorevler">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {todos.filter((todo) => !planned.has(todo.id)).map((todo) =>
            <DraggableCard key={todo.id} id={`todo:${todo.id}`} title={todo.title} muted />)}
        </div>
        {todos.every((todo) => planned.has(todo.id)) && <Empty>Acik tum gorevler planlandi.</Empty>}
      </Panel>
    </div>
  </DndContext>;
}
