import { ScheduleTasks } from "@/core/ContextualHelp";
import { invalidateAfter } from "@/core/invalidation";
import { useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  KeyboardSensor,
  pointerWithin,
  rectIntersection,
  useSensor,
  useSensors,
  type DragEndEvent,
  useDraggable,
  useDroppable,
} from "@dnd-kit/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarPlus, ChevronLeft, ChevronRight, GripVertical } from "lucide-react";
import { api, qs } from "@/core/api";
import { Button, Empty, IconButton, PageFrame, cx, useToast } from "@/core/ui";
import type { PlanSlot, Todo } from "@/core/types";
import { addAppDays, appWeekStartKey, formatTrDate, keyToUtc, localDateKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { TodoComposer } from "./TodoComposer";
import { PlanViews } from "./PlanViews";
import {
  Workspace,
  WorkspacePaneHeader,
  WorkspaceRailContent,
  WorkspaceRailGroup,
  WorkspaceScrollArea,
} from "@/core/workspace/Workspace";

const isoDay = localDateKey;
/** App haftasinin Pazartesi'si -- UTC-projekte gun (Faz 14). */
function monday(value = new Date()): Date {
  return keyToUtc(appWeekStartKey(value));
}

function DraggableCard({
  id,
  title,
  muted = false,
  selected = false,
  onSelect,
  disabled = false,
}: {
  id: string;
  title: string;
  muted?: boolean;
  selected?: boolean;
  onSelect?: () => void;
  disabled?: boolean;
}) {
  const drag = useDraggable({ id, disabled });
  return (
    <div
      ref={drag.setNodeRef}
      className={cx(
        "flex w-full items-center rounded-control border border-transparent border-l-2 border-l-strong bg-surface text-meta transition-colors",
        muted && "border-subtle text-muted",
        selected && "border-accent-border bg-accent-surface text-primary",
        drag.isDragging && "opacity-30",
      )}
    >
      <button
        type="button"
        disabled={disabled}
        {...drag.listeners}
        {...drag.attributes}
        onClick={onSelect}
        className="flex min-w-0 flex-1 touch-none items-center gap-1.5 cursor-grab px-2 py-2 text-left active:cursor-grabbing"
      >
        <GripVertical size={14} className="shrink-0 text-muted" aria-hidden />
        <span>{title}</span>
      </button>
      {onSelect ? (
        <IconButton
          title={selected ? `${title} seçimini kaldır` : `${title} görevini planlamak için seç`}
          onClick={onSelect}
          disabled={disabled}
          className="mr-1 shrink-0"
        >
          <CalendarPlus size={13} />
        </IconButton>
      ) : null}
    </div>
  );
}

function DayColumn({
  day,
  slots,
  selectedTask,
  onPlace,
  disabled,
}: {
  day: Date;
  slots: PlanSlot[];
  selectedTask?: string;
  onPlace: () => void;
  disabled: boolean;
}) {
  const drop = useDroppable({ id: `day:${isoDay(day)}` });
  return (
    <div
      ref={drop.setNodeRef}
      className={cx(
        "min-h-72 border-r border-subtle p-2 last:border-r-0",
        drop.isOver && "border-accent-border bg-accent-surface",
      )}
    >
      <div className="mb-2 flex items-center gap-1 text-meta font-medium">
        <span className="min-w-0 flex-1 truncate">
          {day.toLocaleDateString("tr-TR", { weekday: "short", timeZone: "UTC" })}
          <span className="ml-1 text-muted">{day.getUTCDate()}</span>
        </span>
        {selectedTask ? (
          <IconButton title={`Seçili görevi ${isoDay(day)} gününe planla`} onClick={onPlace} disabled={disabled}>
            <CalendarPlus size={13} />
          </IconButton>
        ) : null}
      </div>
      <div className="stack-y-2">
        {slots.map((slot) => (
          <DraggableCard
            key={slot.id}
            id={`slot:${slot.id}`}
            disabled={disabled}
            title={`${slot.start_min != null ? `${String(Math.floor(slot.start_min / 60)).padStart(2, "0")}:${String(slot.start_min % 60).padStart(2, "0")} · ` : ""}${slot.title}`}
          />
        ))}
      </div>
    </div>
  );
}

export function WeeklyPlannerPage() {
  const client = useQueryClient();
  const toast = useToast();
  const [dragged, setDragged] = useState<{ id: string; title: string } | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor),
  );
  const [week, setWeek] = useState(() => monday());
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  /**
   * Bu oturumda planlanan gorevler: `plan` sorgusu yanitini getirmeden gorevi
   * "Planlanmamış" listesinden dusurur. Sunucu verisi geldiginde slot zaten
   * `planned` kumesine girer; bu defter yalnizca arada kalan boslugu kapatir.
   * Hafta degisince sifirlanir -- gorunmeyen haftanin yerlesimi backlog'u
   * etkilememeli.
   */
  const [placed, setPlaced] = useState<ReadonlySet<string>>(new Set());
  const online = useOnline();
  const days = useMemo(
    () =>
      Array.from({ length: 7 }, (_, i) => {
        return addAppDays(week, i);
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
  const planKey = ["plan", isoDay(week)];
  const move = useMutation({
    onMutate: async ({ active, target }: { active: string; target: string }) => {
      await client.cancelQueries({ queryKey: planKey });
      const previous = client.getQueryData<PlanSlot[]>(planKey);
      const day = target.replace("day:", "");
      const todo = todos.find((item) => `todo:${item.id}` === active);
      const optimisticId = `pending:${active}`;
      client.setQueryData<PlanSlot[]>(planKey, (current = []) =>
        todo
          ? [
              ...current,
              {
                id: optimisticId,
                entity_id: todo.id,
                entity_type: "todo",
                title: todo.title,
                day,
                start_min: null,
                duration_min: null,
                note: null,
                position: current.length,
              },
            ]
          : current.map((slot) => (`slot:${slot.id}` === active ? { ...slot, day } : slot)),
      );
      return { previous, planKey, optimisticId };
    },
    mutationFn: ({ active, target }: { active: string; target: string }) => {
      const day = target.replace("day:", "");
      if (active.startsWith("slot:")) return api.patch(`/plan/${active.replace("slot:", "")}`, { day });
      return api.post("/plan", { entity_id: active.replace("todo:", ""), day });
    },
    onError: (error: Error, _variables, context) => {
      if (context) client.setQueryData(context.planKey, context.previous ?? []);
      toast.push(error.message || "Görev planlanamadı", { tone: "danger" });
    },
    onSuccess: (data, variables, context) => {
      if (context && data)
        client.setQueryData<PlanSlot[]>(context.planKey, (current = []) =>
          current.map((slot) => (slot.id === context.optimisticId ? (data as PlanSlot) : slot)),
        );
      setSelectedTask(null);
      // Gorev -> gun: kart hemen listeden dussun (kullanici ayni karti iki
      // yerde gormesin); slot -> gun tasimasinin backlog'a etkisi yok.
      if (variables.active.startsWith("todo:")) {
        const id = variables.active.replace("todo:", "");
        setPlaced((current) => new Set(current).add(id));
      }
      invalidateAfter("plan.write");
    },
  });
  function onDragEnd(event: DragEndEvent) {
    setDragged(null);
    if (!event.over || !online || move.isPending || String(event.active.id).startsWith("slot:pending:")) return;
    move.mutate({ active: String(event.active.id), target: String(event.over.id) });
  }
  function showWeek(next: Date) {
    setPlaced(new Set());
    setSelectedTask(null);
    setWeek(next);
  }
  const planned = new Set(slots.map((slot) => slot.entity_id));
  const unplanned = todos.filter((todo) => !planned.has(todo.id) && !placed.has(todo.id));
  const selectedTitle = unplanned.find((todo) => todo.id === selectedTask)?.title;
  const weekLabel = `${formatTrDate(days[0], { day: "numeric", month: "short", timeZone: "UTC" })} – ${formatTrDate(days[6], { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })}`;
  return (
    <DndContext
      sensors={sensors}
      collisionDetection={(args) => {
        const hit = pointerWithin(args);
        return hit.length ? hit : rectIntersection(args);
      }}
      onDragStart={({ active }) => {
        if (!online || move.isPending) return;
        const title =
          todos.find((todo) => `todo:${todo.id}` === active.id)?.title ??
          slots.find((slot) => `slot:${slot.id}` === active.id)?.title;
        if (title) setDragged({ id: String(active.id), title });
      }}
      onDragCancel={() => setDragged(null)}
      onDragEnd={onDragEnd}
    >
      <PageFrame className="py-3">
        <Workspace
          railAt="lg"
          rail={
            <WorkspaceRailContent className="max-h-56 lg:max-h-workspace-body">
              <WorkspaceRailGroup label="Planlanmamış" hint={unplanned.length}>
                {unplanned.length ? (
                  unplanned.map((todo) => (
                    <DraggableCard
                      key={todo.id}
                      id={`todo:${todo.id}`}
                      title={todo.title}
                      muted
                      disabled={!online || move.isPending}
                      selected={todo.id === selectedTask}
                      onSelect={() => setSelectedTask((current) => (current === todo.id ? null : todo.id))}
                    />
                  ))
                ) : (
                  <p className="px-2 py-3 text-meta text-muted">Açık görevlerin hepsi planlandı.</p>
                )}
              </WorkspaceRailGroup>
            </WorkspaceRailContent>
          }
        >
          <WorkspacePaneHeader
            eyebrow="Haftalık plan"
            title={weekLabel}
            hint={`${slots.length} blok`}
            action={
              <span className="flex items-center gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={move.isPending}
                  onClick={() => showWeek(addAppDays(week, -7))}
                  title="Önceki hafta"
                >
                  <ChevronLeft size={14} />
                </Button>
                <Button size="sm" disabled={move.isPending} onClick={() => showWeek(monday())}>
                  Bu hafta
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={move.isPending}
                  onClick={() => showWeek(addAppDays(week, 7))}
                  title="Sonraki hafta"
                >
                  <ChevronRight size={14} />
                </Button>
              </span>
            }
          >
            {selectedTitle && <p className="text-meta text-secondary">{selectedTitle}</p>}
          </WorkspacePaneHeader>
          {selectedTask && selectedTitle && (
            <div className="px-3 py-2">
              <ScheduleTasks
                tasks={[{ id: selectedTask, title: selectedTitle }]}
                label="Seçili görev için değişikliği incele"
              />
            </div>
          )}
          <PlanViews view="week" />
          <div className="border-b border-subtle bg-surface-sunken p-3">
            <TodoComposer key={isoDay(week)} defaultPlanDay={isoDay(week)} />
          </div>
          <WorkspaceScrollArea className="overflow-x-auto">
            <div className="grid min-w-calendar-week grid-cols-7">
              {days.map((day) => (
                <DayColumn
                  key={isoDay(day)}
                  day={day}
                  slots={slots.filter((slot) => slot.day === isoDay(day))}
                  disabled={!online || move.isPending}
                  selectedTask={selectedTask ?? undefined}
                  onPlace={() =>
                    selectedTask && move.mutate({ active: `todo:${selectedTask}`, target: `day:${isoDay(day)}` })
                  }
                />
              ))}
            </div>
          </WorkspaceScrollArea>
        </Workspace>
      </PageFrame>
      <DragOverlay dropAnimation={null}>
        {dragged && (
          <div className="flex cursor-grabbing items-center gap-2 rounded-control border border-accent-border bg-surface px-3 py-2 text-meta shadow-card">
            <GripVertical size={14} className="text-muted" />
            {dragged.title}
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
