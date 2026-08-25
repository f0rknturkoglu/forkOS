import { invalidateAfter } from "@/core/invalidation";
import { useState, type ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  CalendarClock,
  Check,
  ChevronRight,
  Circle,
  CreditCard,
  ExternalLink,
  Plus,
  RotateCw,
  Target,
  Trash2,
} from "lucide-react";
import { api } from "@/core/api";
import type { AgendaRow, FeedItem, TodayAgenda, Todo } from "@/core/types";
import {
  Button,
  Chip,
  Empty,
  IconButton,
  Input,
  RowList,
  Section,
  SectionHeader,
  Select,
  Spinner,
  cx,
  useToast,
} from "@/core/ui";
import { useOnline } from "@/lib/hooks";

const RECUR_LABELS: Record<NonNullable<AgendaRow["recur"]>, string> = {
  daily: "her gün",
  weekdays: "hafta içi",
  weekly: "her hafta",
  monthly: "her ay",
};

export function localDay(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function startMinute(value: string): number | null {
  if (!value) return null;
  const [hour, minute] = value.split(":").map(Number);
  if (!Number.isInteger(hour) || !Number.isInteger(minute)) return null;
  return hour * 60 + minute;
}

function clockLabel(value: string | null | undefined): string | null {
  if (!value) return null;
  return new Date(value).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
}

function pickerRow(item: Todo | FeedItem, kind: "todo" | "rss"): AgendaRow {
  const todo = kind === "todo" ? (item as Todo) : null;
  const rss = kind === "rss" ? (item as FeedItem) : null;
  return {
    kind,
    source: "suggestion",
    id: item.id,
    slot_id: null,
    title: item.title,
    completed: false,
    action: kind === "todo" ? "complete_todo" : "mark_rss_read",
    read_only: false,
    context_only: false,
    starts_at: null,
    duration_min: null,
    parent_id: todo?.parent_id ?? null,
    project_title: todo?.project_title ?? null,
    feed_title: rss?.feed_title ?? null,
    url: rss?.url ?? null,
    media_kind: null,
    media_status: null,
    progress_label: null,
    cover_url: null,
    recur: (todo?.recur as AgendaRow["recur"]) ?? null,
    children: [],
  };
}

export function TodayAgendaWidget() {
  const day = localDay();
  const online = useOnline();
  const toast = useToast();
  const [adding, setAdding] = useState(false);
  const [selected, setSelected] = useState("");
  const [start, setStart] = useState("");
  const [duration, setDuration] = useState("");

  const agendaQuery = useQuery({
    queryKey: ["today-agenda", day],
    queryFn: () => api.get<TodayAgenda>(`/today/agenda?day=${day}`),
  });
  const agenda = agendaQuery.data;

  const todosQuery = useQuery({
    queryKey: ["todos", "today-picker"],
    queryFn: () => api.get<Todo[]>("/todos?status=open&limit=300"),
    enabled: adding,
  });
  const rssQuery = useQuery({
    queryKey: ["items", "today-picker"],
    queryFn: () => api.get<FeedItem[]>("/rss/items?unread_only=true&limit=100"),
    enabled: adding,
  });

  const refreshed = () => invalidateAfter("todo.write", "plan.write", "rss.write", "media.write", "calendar.write");
  const failed = () => toast.push("İşlem tamamlanamadı. Satır korunuyor; tekrar deneyebilirsin.", { tone: "danger" });

  const complete = useMutation({
    mutationKey: ["today-complete"],
    mutationFn: (row: AgendaRow) => {
      if (row.action === "complete_todo") return api.post(`/todos/${row.id}/complete`);
      if (row.action === "mark_rss_read") return api.post(`/rss/items/${row.id}/read`);
      throw new Error("Bu satır tamamlanamaz");
    },
    onSuccess: refreshed,
    onError: failed,
  });
  const schedule = useMutation({
    mutationKey: ["today-schedule"],
    mutationFn: ({
      row,
      day: targetDay,
      start: targetStart,
      duration: targetDuration,
    }: {
      row: AgendaRow;
      day: string;
      start: string;
      duration: string;
    }) => {
      const minute = startMinute(targetStart);
      const minutes = targetDuration ? Number(targetDuration) : null;
      return api.post("/plan", {
        entity_id: row.id,
        day: targetDay,
        ...(minute == null ? {} : { start_min: minute }),
        ...(!minutes || minutes < 1 ? {} : { duration_min: minutes }),
      });
    },
    onSuccess: () => {
      setSelected("");
      setStart("");
      setDuration("");
      setAdding(false);
      refreshed();
    },
    onError: failed,
  });
  const remove = useMutation({
    mutationKey: ["today-remove"],
    mutationFn: (row: AgendaRow) => api.del(`/plan/${row.slot_id}`),
    onSuccess: refreshed,
    onError: failed,
  });
  const toggleAuto = useMutation({
    mutationKey: ["today-auto"],
    mutationFn: (enabled: boolean) => api.put("/settings/today.auto_suggestions", { value: enabled }),
    onSuccess: refreshed,
    onError: failed,
  });

  const todoOptions = (todosQuery.data ?? []).map((item) => pickerRow(item, "todo"));
  const rssOptions = (rssQuery.data ?? []).map((item) => pickerRow(item, "rss"));
  const options = [...todoOptions, ...rssOptions];
  const selectedRow = options.find((row) => `${row.kind}:${row.id}` === selected);
  const suggestions = agenda ? [...agenda.suggestions.todos, ...agenda.suggestions.rss] : [];
  const busy = complete.isPending || schedule.isPending || remove.isPending || toggleAuto.isPending;

  return (
    <Section
      title="Günün akışı"
      hint={agenda ? `${agenda.timed.length + agenda.checklist.length} sırada` : undefined}
      bodyClassName="space-y-4"
      action={
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-pressed={agenda?.auto_suggestions ?? true}
            disabled={!online || busy || !agenda}
            onClick={() => agenda && toggleAuto.mutate(!agenda.auto_suggestions)}
            className={cx(
              "rounded-full border px-2 py-0.5 text-micro transition",
              agenda?.auto_suggestions ? "border-ok-border bg-ok-surface text-ok" : "border-subtle text-muted",
            )}
          >
            oto {agenda?.auto_suggestions ? "açık" : "kapalı"}
          </button>
          <button
            type="button"
            onClick={() => setAdding((value) => !value)}
            disabled={!online}
            className="flex items-center gap-1 text-meta text-accent hover:underline disabled:opacity-40"
          >
            <Plus size={13} /> {adding ? "kapat" : "ekle"}
          </button>
        </div>
      }
    >
      {!online && (
        <p className="border-b border-subtle pb-3 text-meta text-warn">
          Çevrimdışısın; akış okunabilir ama değişiklikler bağlantı gelene kadar kapalı.
        </p>
      )}

      {adding && (
        <div className="grid gap-2 border-b border-subtle pb-4 sm:grid-cols-[minmax(0,1fr)_92px_92px_auto]">
          <Select value={selected} onChange={setSelected} ariaLabel="Bugüne eklenecek öğe" className="min-w-0">
            <option value="">Görev veya RSS seç…</option>
            {todoOptions.length > 0 && (
              <optgroup label="Görevler">
                {todoOptions.map((row) => (
                  <option key={`todo:${row.id}`} value={`todo:${row.id}`}>
                    {row.title}
                  </option>
                ))}
              </optgroup>
            )}
            {rssOptions.length > 0 && (
              <optgroup label="RSS yazıları">
                {rssOptions.map((row) => (
                  <option key={`rss:${row.id}`} value={`rss:${row.id}`}>
                    {row.title}
                  </option>
                ))}
              </optgroup>
            )}
          </Select>
          <Input type="time" value={start} onChange={setStart} ariaLabel="Başlangıç saati" />
          <Input type="number" value={duration} onChange={setDuration} placeholder="dakika" ariaLabel="Süre (dakika)" />
          <Button
            size="sm"
            variant="primary"
            disabled={!online || !selectedRow || schedule.isPending}
            onClick={() => selectedRow && schedule.mutate({ row: selectedRow, day, start, duration })}
          >
            Bugüne ekle
          </Button>
        </div>
      )}

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
          Günün akışı alınamadı.
        </Empty>
      ) : (
        <>
          <AgendaGroup
            label="Saatli"
            rows={agenda.timed}
            online={online}
            complete={(row) => complete.mutate(row)}
            remove={(row) => remove.mutate(row)}
          />
          <AgendaGroup
            label="Yapılacaklar"
            rows={agenda.checklist}
            online={online}
            complete={(row) => complete.mutate(row)}
            remove={(row) => remove.mutate(row)}
          />

          {suggestions.length > 0 && agenda.auto_suggestions && (
            <div>
              <SectionHeader label="Öneriler" hint="planına yazılmadı" />
              <RowList>
                {suggestions.map((row) => (
                  <AgendaLine
                    key={`${row.kind}:${row.id}`}
                    row={row}
                    online={online}
                    complete={() => {}}
                    remove={() => {}}
                    suggestionAction={
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={!online || schedule.isPending}
                        onClick={() => schedule.mutate({ row, day, start: "", duration: "" })}
                      >
                        Bugüne ekle
                      </Button>
                    }
                  />
                ))}
              </RowList>
            </div>
          )}

          {agenda.completed.length > 0 && (
            <div className="opacity-70">
              <SectionHeader label="Tamamlananlar" hint={`${agenda.completed.length}`} />
              <RowList>
                {agenda.completed.map((row) => (
                  <AgendaLine
                    key={`${row.kind}:${row.id}`}
                    row={row}
                    online={online}
                    complete={() => {}}
                    remove={(item) => remove.mutate(item)}
                  />
                ))}
              </RowList>
            </div>
          )}

          {agenda.timed.length === 0 &&
            agenda.checklist.length === 0 &&
            suggestions.length === 0 &&
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
}: {
  label: string;
  rows: AgendaRow[];
  online: boolean;
  complete: (row: AgendaRow) => void;
  remove: (row: AgendaRow) => void;
}) {
  if (rows.length === 0) return null;
  return (
    <div>
      <SectionHeader label={label} hint={`${rows.length}`} />
      <RowList>
        {rows.map((row) => (
          <AgendaLine key={`${row.kind}:${row.id}`} row={row} online={online} complete={complete} remove={remove} />
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
  suggestionAction,
  nested = false,
}: {
  row: AgendaRow;
  online: boolean;
  complete: (row: AgendaRow) => void;
  remove: (row: AgendaRow) => void;
  suggestionAction?: ReactNode;
  nested?: boolean;
}) {
  const time = clockLabel(row.starts_at);
  const meta = row.kind === "media" ? row.progress_label : (row.project_title ?? row.feed_title);
  const interactive = Boolean(
    (row.action === "complete_todo" || row.action === "mark_rss_read") && !row.context_only && !row.completed,
  );
  return (
    <div data-agenda-id={row.id} className={cx("py-2", nested && "ml-5 border-l border-subtle pl-3")}>
      <div className="flex min-w-0 items-start gap-2">
        {row.context_only ? (
          <ChevronRight size={15} className="mt-0.5 shrink-0 text-muted" />
        ) : row.completed ? (
          <Check size={15} className="mt-0.5 shrink-0 text-ok" />
        ) : row.action === "log_media" ? (
          <a
            href={`#/media?focus=${row.id}`}
            title="İlerleme kaydet"
            aria-label={`${row.title} ilerleme kaydet`}
            className="mt-0.5 shrink-0 text-muted transition hover:text-accent"
          >
            <Circle size={15} />
          </a>
        ) : row.kind === "opportunity" ? (
          <Target size={15} className="mt-0.5 shrink-0 text-muted" />
        ) : row.kind === "payment" ? (
          <CreditCard size={15} className="mt-0.5 shrink-0 text-muted" />
        ) : row.kind === "study" ? (
          <BookOpen size={15} className="mt-0.5 shrink-0 text-muted" />
        ) : (
          <CalendarClock size={15} className="mt-0.5 shrink-0 text-muted" />
        )}

        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-baseline gap-2">
            {time && <span className="numeral shrink-0 text-meta text-accent">{time}</span>}
            <span
              className={cx(
                "min-w-0 truncate text-body text-primary",
                row.completed && "line-through text-muted",
                row.context_only && "font-medium text-secondary",
              )}
            >
              {row.title}
            </span>
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
        {suggestionAction}
        {row.slot_id && (
          <IconButton title="Bugünden çıkar" disabled={!online} onClick={() => remove(row)}>
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
          nested
        />
      ))}
    </div>
  );
}
