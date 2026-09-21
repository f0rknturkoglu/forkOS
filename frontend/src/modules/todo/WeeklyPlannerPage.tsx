import { invalidateAfter } from "@/core/invalidation";
import { useMemo, useState } from "react";
import { DndContext, type DragEndEvent, useDraggable, useDroppable } from "@dnd-kit/core";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CalendarPlus, ChevronLeft, ChevronRight, ListTodo } from "lucide-react";
import { api, qs } from "@/core/api";
import { Button, Empty, IconButton, PageFrame, cx } from "@/core/ui";
import type { PlanSlot, Todo } from "@/core/types";
import { addAppDays, appWeekStartKey, formatTrDate, keyToUtc, localDateKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
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
}: {
  id: string;
  title: string;
  muted?: boolean;
  selected?: boolean;
  onSelect?: () => void;
}) {
  const drag = useDraggable({ id });
  return (
    <div
      ref={drag.setNodeRef}
      style={{ transform: drag.transform ? `translate(${drag.transform.x}px,${drag.transform.y}px)` : undefined }}
      className={cx(
        "flex w-full items-center rounded-control border border-transparent border-l-2 border-l-strong bg-surface text-meta transition",
        muted && "border-subtle text-muted",
        selected && "border-accent-border bg-accent-surface text-primary",
        drag.isDragging && "z-popover opacity-70",
      )}
    >
      <button
        type="button"
        {...drag.listeners}
        {...drag.attributes}
        onClick={onSelect}
        className="min-w-0 flex-1 cursor-grab px-2 py-2 text-left"
      >
        {title}
      </button>
      {onSelect ? (
        <IconButton
          title={selected ? `${title} seçimini kaldır` : `${title} görevini planlamak için seç`}
          onClick={onSelect}
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
}: {
  day: Date;
  slots: PlanSlot[];
  selectedTask?: string;
  onPlace: () => void;
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
          <IconButton title={`Seçili görevi ${isoDay(day)} gününe planla`} onClick={onPlace}>
            <CalendarPlus size={13} />
          </IconButton>
        ) : null}
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
  const move = useMutation({
    mutationFn: ({ active, target }: { active: string; target: string }) => {
      const day = target.replace("day:", "");
      if (active.startsWith("slot:")) return api.patch(`/plan/${active.replace("slot:", "")}`, { day });
      return api.post("/plan", { entity_id: active.replace("todo:", ""), day });
    },
    onSuccess: (_data, variables) => {
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
    if (!event.over || !online) return;
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
    <DndContext onDragEnd={onDragEnd}>
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
                      selected={todo.id === selectedTask}
                      onSelect={() => setSelectedTask((current) => (current === todo.id ? null : todo.id))}
                    />
                  ))
                ) : (
                  <p className="px-2 py-3 text-meta text-muted">Açık görevlerin hepsi planlandı.</p>
                )}
              </WorkspaceRailGroup>
              <p className="px-2 text-meta text-muted">
                Sürükle veya bir görev seçip gün başlığındaki planla düğmesini kullan.
              </p>
            </WorkspaceRailContent>
          }
        >
          <WorkspacePaneHeader
            eyebrow="Haftalık plan"
            title={weekLabel}
            hint={`${slots.length} blok`}
            action={
              <span className="flex items-center gap-1">
                <Button size="sm" variant="ghost" onClick={() => showWeek(addAppDays(week, -7))} title="Önceki hafta">
                  <ChevronLeft size={14} />
                </Button>
                <Button size="sm" onClick={() => showWeek(monday())}>
                  Bu hafta
                </Button>
                <Button size="sm" variant="ghost" onClick={() => showWeek(addAppDays(week, 7))} title="Sonraki hafta">
                  <ChevronRight size={14} />
                </Button>
              </span>
            }
          >
            <p className="flex items-center gap-2 text-meta text-muted">
              <ListTodo size={13} />
              {selectedTitle
                ? `“${selectedTitle}” seçildi — bir güne ekle.`
                : "Görevleri günlere sürükleyerek yerleştir."}
            </p>
          </WorkspacePaneHeader>
          <WorkspaceScrollArea className="overflow-x-auto">
            <div className="grid min-w-calendar-week grid-cols-7">
              {days.map((day) => (
                <DayColumn
                  key={isoDay(day)}
                  day={day}
                  slots={slots.filter((slot) => slot.day === isoDay(day))}
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
    </DndContext>
  );
}
