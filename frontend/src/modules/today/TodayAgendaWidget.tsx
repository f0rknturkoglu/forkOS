import { ScheduleTasks } from "@/core/ContextualHelp";
import { useState, type FormEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CalendarClock,
  CalendarX,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  ExternalLink,
  Moon,
  Plus,
  RotateCw,
  Sun,
  Sunrise,
  Sunset,
  Target,
  Trash2,
} from "lucide-react";
import { navigate } from "@/app/router";
import { api, qs } from "@/core/api";
import { entityRoute } from "@/core/entityRegistry";
import { invalidateAfter } from "@/core/invalidation";
import { createTask, invalidateTaskWrite } from "@/core/tasks";
import type { ActivityEvent, AgendaRow, PlanSlot, TodayAgenda, Todo } from "@/core/types";
import {
  Button,
  Chip,
  Empty,
  IconButton,
  Input,
  RowList,
  Section,
  SectionHeader,
  Spinner,
  cx,
  useToast,
} from "@/core/ui";
import { appTimeParts, formatAppDate, localDateKey, todayKey, tomorrowKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { deriveTodayState } from "./todayState";

const RECUR_LABELS: Record<NonNullable<AgendaRow["recur"]>, string> = {
  daily: "her gün",
  weekdays: "hafta içi",
  weekly: "her hafta",
  monthly: "her ay",
};

function clockLabel(value: string | null | undefined): string | null {
  if (!value) return null;
  const { hour, minute } = appTimeParts(new Date(value));
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function timeLabel(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  const clock = clockLabel(value);
  const rowDay = localDateKey(date);
  if (rowDay === todayKey()) return clock;
  if (rowDay === tomorrowKey()) return `Yarın ${clock}`;
  return `${formatAppDate(date, { day: "numeric", month: "short" })} ${clock}`;
}

function pickerRow(item: Todo, kind: "todo"): AgendaRow {
  return {
    kind,
    source: "suggestion",
    id: item.id,
    slot_id: null,
    title: item.title,
    completed: false,
    action: "complete_todo",
    read_only: false,
    context_only: false,
    starts_at: null,
    duration_min: null,
    parent_id: item.parent_id ?? null,
    project_title: item.project_title ?? null,
    feed_title: null,
    url: null,
    progress_label: null,
    recur: (item.recur as AgendaRow["recur"]) ?? null,
    children: [],
  };
}

function rowIds(rows: AgendaRow[]): Set<string> {
  const ids = new Set<string>();
  const visit = (row: AgendaRow) => {
    ids.add(row.id);
    row.children.forEach(visit);
  };
  rows.forEach(visit);
  return ids;
}

function unplannedTodoRows(todos: Todo[], agenda: TodayAgenda): AgendaRow[] {
  const agendaIds = rowIds([...agenda.timed, ...agenda.checklist, ...agenda.completed]);
  const rows = todos
    .filter((todo) => (todo.status === "open" || todo.status === "doing") && !todo.recur && !agendaIds.has(todo.id))
    .map((todo) => pickerRow(todo, "todo"));
  const byId = new Map(rows.map((row) => [row.id, row]));
  const roots: AgendaRow[] = [];
  rows.forEach((row) => {
    const parent = row.parent_id ? byId.get(row.parent_id) : undefined;
    if (parent) parent.children.push(row);
    else roots.push(row);
  });
  return roots;
}

function hasRoutine(row: AgendaRow): boolean {
  return Boolean(row.recur) || row.children.some(hasRoutine);
}

export function TodayAgendaWidget() {
  const day = todayKey();
  const tomorrow = tomorrowKey();
  const now = new Date();

  const online = useOnline();
  const toast = useToast();

  const [draft, setDraft] = useState("");
  const [completedOpen, setCompletedOpen] = useState(false);

  const agendaQuery = useQuery({
    queryKey: ["today-agenda", day],
    queryFn: () => api.get<TodayAgenda>(`/today/agenda?day=${day}`),
  });
  const agenda = agendaQuery.data;

  const todosQuery = useQuery({
    queryKey: ["todos", "today-open"],
    queryFn: () => api.get<Todo[]>("/todos?limit=300"),
  });
  const todos = todosQuery.data ?? [];

  const slotsQuery = useQuery({
    queryKey: ["plan", day],
    queryFn: () => api.get<PlanSlot[]>(`/plan${qs({ week: day })}`),
  });
  const slots = slotsQuery.data ?? [];

  const reviewEventsQuery = useQuery({
    queryKey: ["activity", "review-check"],
    queryFn: () => api.get<ActivityEvent[]>("/activity?limit=40&verbs=review.completed"),
  });
  const reviewEvents = reviewEventsQuery.data ?? [];

  const weeklyReviewsQuery = useQuery({
    queryKey: ["reviews", "weekly"],
    queryFn: () => api.get<{ period_start: string }[]>("/reviews?kind=weekly&limit=5"),
  });
  const weeklyReviews = weeklyReviewsQuery.data ?? [];

  const refreshed = () => invalidateAfter("todo.write", "plan.write", "rss.write", "calendar.write");
  const failed = () => toast.push("İşlem tamamlanamadı. Satır korunuyor; tekrar deneyebilirsin.", { tone: "danger" });

  const createTodo = useMutation({
    mutationKey: ["today-create-todo"],
    // KANONIK yol (Faz 17): satir ici ekleme de `createTask`'tan gecer, boylece
    // plan_day/due_at sozlesmesi ve invalidation tek yerde kalir. Gun bu
    // widget'in gunudur ("Bugunun plani"), bu yuzden acikca verilir.
    mutationFn: (title: string) => createTask({ title, plan_day: day, priority: 2 }),
    onSuccess: () => {
      setDraft("");
      invalidateTaskWrite();
      toast.push("Görev bugünün planına eklendi.", { tone: "ok" });
    },
    onError: failed,
  });

  const complete = useMutation({
    mutationKey: ["today-complete"],
    mutationFn: (row: AgendaRow) => {
      if (row.action === "complete_todo" || row.kind === "todo") return api.post(`/todos/${row.id}/complete`);
      if (row.action === "mark_rss_read") return api.post(`/rss/items/${row.id}/read`);
      throw new Error("Bu satır tamamlanamaz");
    },
    onSuccess: refreshed,
    onError: failed,
  });

  const deleteTodo = useMutation({
    mutationKey: ["today-delete-todo"],
    mutationFn: (todoId: string) => api.del(`/todos/${todoId}`),
    onSuccess: () => {
      refreshed();
      toast.push("Görev silindi.", { tone: "ok" });
    },
    onError: failed,
  });

  const remove = useMutation({
    mutationKey: ["today-remove"],
    mutationFn: (row: AgendaRow) => api.del(`/plan/${row.slot_id}`),
    onSuccess: refreshed,
    onError: failed,
  });

  const carryOver = useMutation({
    mutationKey: ["today-carry-over"],
    mutationFn: () => api.post<{ moved: number }>("/plan/carry-over", { day, target: tomorrow }),
    onSuccess: (result) => {
      invalidateAfter("plan.write");
      toast.push(`${result.moved} görev yarına taşındı.`, { tone: "ok" });
    },
    onError: () => toast.push("Taşıma başarısız — hiçbir slot değişmedi.", { tone: "danger" }),
  });

  const { phase, phaseLabel, plannedTodos, overdue, reviewDone, weeklyReviewDue, conflictCount } = deriveTodayState({
    day,
    now,
    slots,
    todos,
    agenda,
    reviewEvents,
    weeklyReviews,
  });

  const openTodos = agenda ? unplannedTodoRows(todos, agenda) : [];
  const routineRows = agenda ? [...agenda.timed, ...agenda.checklist].filter(hasRoutine) : [];
  const timedRows = agenda ? agenda.timed.filter((row) => !hasRoutine(row)) : [];
  const checklistRows = agenda ? agenda.checklist.filter((row) => !hasRoutine(row)) : [];

  const phaseIcon = phase === "morning" ? Sunrise : phase === "evening" ? Sunset : Sun;
  const PhaseIcon = phaseIcon;

  const handleQuickAdd = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || !online || createTodo.isPending) return;
    createTodo.mutate(trimmed);
  };

  return (
    <Section
      title="Bugünün planı"
      hint={agenda ? `${agenda.timed.length + agenda.checklist.length + openTodos.length} öğe` : undefined}
      bodyClassName="stack-y-4"
    >
      {!online && (
        <p className="border-b border-subtle pb-3 text-meta text-warn">
          Çevrimdışısın; akış okunabilir ama değişiklikler bağlantı gelene kadar kapalı.
        </p>
      )}

      {openTodos.length > 0 && (
        <div className="flex justify-end">
          <ScheduleTasks
            tasks={openTodos.slice(0, 10).map((todo) => ({ id: todo.id, title: todo.title }))}
            label="Görevlerin planını düzenle"
          />
        </div>
      )}
      {/* Tek Satırlık Hızlı Görev Ekleme Formu */}
      <form onSubmit={handleQuickAdd} className="flex items-center gap-2">
        <Input
          value={draft}
          onChange={setDraft}
          placeholder="Bugüne hızlı görev ekle... (Enter ile kaydet)"
          ariaLabel="Bugüne görev ekle"
          disabled={!online || createTodo.isPending}
          className="flex-1"
        />
        <Button size="sm" variant="primary" type="submit" disabled={!online || !draft.trim() || createTodo.isPending}>
          <Plus size={14} /> Ekle
        </Button>
      </form>

      {agendaQuery.isLoading ? (
        <Spinner />
      ) : agendaQuery.isError || !agenda ? (
        <Empty
          action={
            <Button size="sm" onClick={() => agendaQuery.refetch()}>
              Yeniden dene
            </Button>
          }
        >
          Bugünün planı alınamadı.
        </Empty>
      ) : (
        <>
          <AgendaGroup
            label="Saatli"
            rows={timedRows}
            online={online}
            complete={(row) => complete.mutate(row)}
            remove={(row) => remove.mutate(row)}
            deleteTodo={(id) => deleteTodo.mutate(id)}
          />
          <AgendaGroup
            label="Rutinler"
            rows={routineRows}
            online={online}
            complete={(row) => complete.mutate(row)}
            remove={(row) => remove.mutate(row)}
            deleteTodo={(id) => deleteTodo.mutate(id)}
          />
          <AgendaGroup
            label="Yapılacaklar"
            rows={checklistRows}
            online={online}
            complete={(row) => complete.mutate(row)}
            remove={(row) => remove.mutate(row)}
            deleteTodo={(id) => deleteTodo.mutate(id)}
          />
          <AgendaGroup
            label="Açık görevler"
            rows={openTodos}
            online={online}
            complete={(row) => complete.mutate(row)}
            remove={(row) => remove.mutate(row)}
            deleteTodo={(id) => deleteTodo.mutate(id)}
          />

          {/* Gün Özeti ve Ritim Durumu */}
          <div className="rounded-card border border-subtle bg-surface-hover/30 p-3 stack-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2 text-meta text-muted">
              <div className="flex items-center gap-1.5">
                <PhaseIcon size={14} className="shrink-0 text-icon" />
                <span className="font-semibold text-primary">{phaseLabel}</span>
                <span>·</span>
                <span>
                  Bugün <strong className="font-medium text-primary">{plannedTodos.length}</strong> planlı
                </span>
                <span>·</span>
                <span className={overdue > 0 ? "font-medium text-warn" : ""}>
                  <strong className="font-medium">{overdue}</strong> geciken
                </span>
              </div>

              {phase === "evening" && plannedTodos.length > 0 && (
                <Button size="sm" disabled={!online || carryOver.isPending} onClick={() => carryOver.mutate()}>
                  {carryOver.isPending ? "Taşınıyor…" : "Yarına taşı"}
                </Button>
              )}
            </div>

            {conflictCount > 0 && (
              <p className="flex items-center gap-1.5 text-meta text-warn">
                <AlertTriangle size={13} /> {conflictCount} takvim çakışması
              </p>
            )}

            {phase === "evening" && (
              <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-subtle">
                {reviewDone ? (
                  <span className="flex items-center gap-1 text-meta text-ok">
                    <CheckCircle2 size={13} /> Günü değerlendirdin
                  </span>
                ) : (
                  <>
                    <span className="flex items-center gap-1 text-meta text-muted">
                      <Moon size={13} className="shrink-0" /> Gün sonu değerlendirmesi bekliyor
                    </span>
                    <Button size="sm" variant="secondary" disabled={!online} onClick={() => navigate("/review/daily")}>
                      <ArrowRight size={13} /> Değerlendirmeye git
                    </Button>
                  </>
                )}
              </div>
            )}

            {weeklyReviewDue && (
              <div className="pt-1 border-t border-subtle">
                <Button size="sm" variant="secondary" disabled={!online} onClick={() => navigate("/review/weekly")}>
                  <ArrowRight size={13} /> Haftalık değerlendirme bekliyor
                </Button>
              </div>
            )}
          </div>

          {agenda.completed.length > 0 && (
            <div className="opacity-70">
              <button
                type="button"
                aria-expanded={completedOpen}
                aria-controls="today-completed-list"
                onClick={() => setCompletedOpen((value) => !value)}
                className="flex w-full items-center justify-between rounded-control px-1 py-1 text-left transition hover:bg-surface-hover"
              >
                <span className="text-meta font-semibold uppercase tracking-wide text-muted">
                  Tamamlananlar · {agenda.completed.length}
                </span>
                <ChevronDown
                  size={14}
                  className={cx("text-muted transition-transform", completedOpen && "rotate-180")}
                />
              </button>
              {completedOpen && (
                <div id="today-completed-list">
                  <RowList>
                    {agenda.completed.map((row) => (
                      <AgendaLine
                        key={`${row.kind}:${row.id}`}
                        row={row}
                        online={online}
                        complete={() => {}}
                        remove={(item) => remove.mutate(item)}
                        deleteTodo={(id) => deleteTodo.mutate(id)}
                      />
                    ))}
                  </RowList>
                </div>
              )}
            </div>
          )}

          {agenda.timed.length === 0 &&
            agenda.checklist.length === 0 &&
            openTodos.length === 0 &&
            agenda.completed.length === 0 && <Empty>Bugün için henüz bir şey yok.</Empty>}
        </>
      )}
    </Section>
  );
}

function AgendaGroup({
  label,
  rows,
  online,
  complete,
  remove,
  deleteTodo,
}: {
  label: string;
  rows: AgendaRow[];
  online: boolean;
  complete: (row: AgendaRow) => void;
  remove: (row: AgendaRow) => void;
  deleteTodo: (id: string) => void;
}) {
  if (rows.length === 0) return null;
  return (
    <div>
      <SectionHeader label={label} hint={`${rows.length}`} />
      <RowList>
        {rows.map((row) => (
          <AgendaLine
            key={`${row.kind}:${row.id}`}
            row={row}
            online={online}
            complete={complete}
            remove={remove}
            deleteTodo={deleteTodo}
          />
        ))}
      </RowList>
    </div>
  );
}

function AgendaLine({
  row,
  online,
  complete,
  remove,
  deleteTodo,
  nested = false,
}: {
  row: AgendaRow;
  online: boolean;
  complete: (row: AgendaRow) => void;
  remove: (row: AgendaRow) => void;
  deleteTodo: (id: string) => void;
  nested?: boolean;
}) {
  const time = timeLabel(row.starts_at);
  const meta = row.progress_label ?? row.project_title ?? row.feed_title;
  const interactive = Boolean(
    (row.action === "complete_todo" || row.kind === "todo" || row.action === "mark_rss_read") &&
    !row.context_only &&
    !row.completed,
  );
  return (
    <div data-agenda-id={row.id} className={cx("py-2", nested && "ml-5 border-l border-subtle pl-3")}>
      <div className="flex min-w-0 items-start gap-2">
        {row.context_only ? (
          <ChevronRight size={15} className="mt-0.5 shrink-0 text-muted" />
        ) : row.completed ? (
          <Check size={15} className="mt-0.5 shrink-0 text-ok" />
        ) : row.kind === "opportunity" ? (
          <Target size={15} className="mt-0.5 shrink-0 text-muted" />
        ) : row.kind === "study" ? (
          <BookOpen size={15} className="mt-0.5 shrink-0 text-muted" />
        ) : (
          <CalendarClock size={15} className="mt-0.5 shrink-0 text-muted" />
        )}

        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-baseline gap-2">
            {time && <span className="numeral shrink-0 text-meta text-accent">{time}</span>}
            {(() => {
              const href =
                row.kind === "todo"
                  ? `#/todos?focus=${encodeURIComponent(row.id)}`
                  : row.entity_type
                    ? `#${entityRoute(row.entity_type, row.entity_id ?? row.id).replace(/^#/, "")}`
                    : null;
              const classes = [
                "min-w-0 truncate text-body text-primary",
                row.completed && "line-through text-muted",
                row.context_only && "font-medium text-secondary",
              ];
              return href ? (
                <a href={href} className={cx(...classes, "transition hover:text-accent hover:underline")}>
                  {row.title}
                </a>
              ) : (
                <span className={cx(...classes)}>{row.title}</span>
              );
            })()}
            {row.duration_min && <span className="shrink-0 text-meta text-muted">{row.duration_min} dk</span>}
          </div>
          {(meta || row.recur) && (
            <div className="mt-0.5 flex items-center gap-1.5 text-meta text-muted">
              {meta && <span className="truncate">{meta}</span>}
              {row.recur && (
                <Chip tone="accent">
                  <RotateCw size={9} className="mr-1 inline" />
                  {RECUR_LABELS[row.recur]}
                </Chip>
              )}
            </div>
          )}
        </div>

        {row.url && (
          <a
            href={row.url}
            target="_blank"
            rel="noreferrer"
            title="Bağlantıyı aç"
            className="mt-0.5 shrink-0 text-muted hover:text-accent"
          >
            <ExternalLink size={14} />
          </a>
        )}
        {interactive && (
          <IconButton title="Tamamla" disabled={!online} onClick={() => complete(row)}>
            <Check size={14} />
          </IconButton>
        )}
        {row.slot_id && (
          <IconButton title="Bugünden çıkar" disabled={!online} onClick={() => remove(row)}>
            <CalendarX size={14} />
          </IconButton>
        )}
        {row.kind === "todo" && (
          <IconButton title="Görevi sil" disabled={!online} onClick={() => deleteTodo(row.id)}>
            <Trash2 size={14} />
          </IconButton>
        )}
      </div>

      {row.children.map((child) => (
        <AgendaLine
          key={`${child.kind}:${child.id}`}
          row={child}
          online={online}
          complete={complete}
          remove={remove}
          deleteTodo={deleteTodo}
          nested
        />
      ))}
    </div>
  );
}
