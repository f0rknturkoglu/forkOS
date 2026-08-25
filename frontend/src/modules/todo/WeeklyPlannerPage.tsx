import { invalidateAfter } from "@/core/invalidation";
import { useMemo, useState } from "react";
import { DndContext, type DragEndEvent, useDraggable, useDroppable } from "@dnd-kit/core";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Button, Empty, PageFrame, PageHeader, Section, Toolbar, cx } from "@/core/ui";
import type { PlanSlot, Todo } from "@/core/types";
import { localDateKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";

const isoDay = localDateKey;
function monday(value = new Date()) {
  const copy = new Date(value);
  copy.setHours(12, 0, 0, 0);
  copy.setDate(copy.getDate() - ((copy.getDay() + 6) % 7));
  return copy;
}

function DraggableCard({ id, title, muted = false }: { id: string; title: string; muted?: boolean }) {
  const drag = useDraggable({ id });
  return (
    <button
      ref={drag.setNodeRef}
      {...drag.listeners}
      {...drag.attributes}
      style={{ transform: drag.transform ? `translate(${drag.transform.x}px,${drag.transform.y}px)` : undefined }}
      className={cx(
        "w-full cursor-grab border-l-2 border-strong bg-surface px-2 py-2 text-left text-meta",
        muted && "border-subtle text-muted",
        drag.isDragging && "z-20 opacity-70",
      )}
    >
      {title}
    </button>
  );
}

function DayColumn({ day, slots }: { day: Date; slots: PlanSlot[] }) {
  const drop = useDroppable({ id: `day:${isoDay(day)}` });
  return (
    <div
      ref={drop.setNodeRef}
      className={cx(
        "min-h-72 border-r border-subtle p-2 last:border-r-0",
        drop.isOver && "border-accent-border bg-accent-surface",
      )}
    >
      <div className="mb-2 text-meta font-medium">
        <span>{day.toLocaleDateString("tr-TR", { weekday: "short" })}</span>
        <span className="ml-1 text-muted">{day.getDate()}</span>
      </div>
      <div className="space-y-2">
        {slots.map((slot) => (
          <DraggableCard
            key={slot.id}
            id={`slot:${slot.id}`}
            title={`${slot.start_min != null ? `${String(Math.floor(slot.start_min / 60)).padStart(2, "0")}:${String(slot.start_min % 60).padStart(2, "0")} · ` : ""}${slot.title}`}
          />
        ))}
      </div>
    </div>
  );
}

export function WeeklyPlannerPage() {
  const [week, setWeek] = useState(() => monday());
  const online = useOnline();
  const days = useMemo(
    () =>
      Array.from({ length: 7 }, (_, i) => {
        const day = new Date(week);
        day.setDate(week.getDate() + i);
        return day;
      }),
    [week],
  );
  const { data: slots = [] } = useQuery({
    queryKey: ["plan", isoDay(week)],
    queryFn: () => api.get<PlanSlot[]>(`/plan${qs({ week: isoDay(week) })}`),
  });
  const { data: todos = [] } = useQuery({
    queryKey: ["todos", "planner"],
    queryFn: () => api.get<Todo[]>("/todos?status=open&limit=100"),
  });
  const move = useMutation({
    mutationFn: ({ active, target }: { active: string; target: string }) => {
      const day = target.replace("day:", "");
      if (active.startsWith("slot:")) return api.patch(`/plan/${active.replace("slot:", "")}`, { day });
      return api.post("/plan", { entity_id: active.replace("todo:", ""), day });
    },
    onSuccess: () => invalidateAfter("plan.write"),
  });
  function onDragEnd(event: DragEndEvent) {
    if (!event.over || !online) return;
    move.mutate({ active: String(event.active.id), target: String(event.over.id) });
  }
  function shift(days: number) {
    const next = new Date(week);
    next.setDate(next.getDate() + days);
    setWeek(next);
  }
  const planned = new Set(slots.map((slot) => slot.entity_id));
  return (
    <DndContext onDragEnd={onDragEnd}>
      <PageFrame className="space-y-5">
        <PageHeader eyebrow="Planlama" title="Haftalık Plan" />
        <p className="text-meta text-muted">
          Görevleri haftaya sürükle; plan blokları bütün kayıt türlerini destekler.
        </p>
        <Toolbar>
          <Button onClick={() => shift(-7)}>← Önceki</Button>
          <Button onClick={() => setWeek(monday())}>Bu hafta</Button>
          <Button onClick={() => shift(7)}>Sonraki →</Button>
        </Toolbar>
        <div className="overflow-x-auto">
          <div className="grid min-w-[760px] grid-cols-7 border-y border-subtle">
            {days.map((day) => (
              <DayColumn key={isoDay(day)} day={day} slots={slots.filter((slot) => slot.day === isoDay(day))} />
            ))}
          </div>
        </div>
        <Section title="Planlanmamış görevler">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {todos
              .filter((todo) => !planned.has(todo.id))
              .map((todo) => (
                <DraggableCard key={todo.id} id={`todo:${todo.id}`} title={todo.title} muted />
              ))}
          </div>
          {todos.every((todo) => planned.has(todo.id)) && <Empty>Açık görevlerin hepsi planlandı.</Empty>}
        </Section>
      </PageFrame>
    </DndContext>
  );
}
