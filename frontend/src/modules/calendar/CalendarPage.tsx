import { invalidateAfter } from "@/core/invalidation";
import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, RefreshCw } from "lucide-react";
import { api } from "@/core/api";
import type { CalendarEvent } from "@/core/types";
import { Button, Chip, Empty, PageFrame, cx } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import {
  addAppDays,
  appDayUtc,
  appWeekStartKey,
  formatTrDate,
  formatTrDateTime,
  keyToUtc,
  localDateKey,
} from "@/lib/date";
import { useOnline } from "@/lib/hooks";

type View = "week" | "month";

const DAY_MS = 86_400_000;
const WEEKDAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];

function startOfDay(value: Date): Date {
  // App gununun UTC-projekte temsili (Faz 14) -- tarayici tz'den bagimsiz.
  return appDayUtc(value);
}

/** Haftanin pazartesisi. getDay: 0=pazar, o yuzden +6 %7. */
function monday(value: Date): Date {
  return keyToUtc(appWeekStartKey(value));
}

function sameDay(a: Date, b: Date): boolean {
  return localDateKey(a) === localDateKey(b);
}

/** Gorunumun kapsadigi ilk gun: hafta = pazartesi, ay = ayin ilk haftasinin pazartesisi. */
function rangeStart(anchor: Date, view: View): Date {
  if (view === "week") return monday(anchor);
  return monday(new Date(Date.UTC(anchor.getUTCFullYear(), anchor.getUTCMonth(), 1)));
}

/** Ay izgarasi TAM haftalardan olusur; ayin son gununu kapsayacak kadar hafta. */
function rangeDays(anchor: Date, view: View): number {
  if (view === "week") return 7;
  const first = rangeStart(anchor, view);
  const lastOfMonth = startOfDay(new Date(Date.UTC(anchor.getUTCFullYear(), anchor.getUTCMonth() + 1, 0)));
  const span = Math.round((lastOfMonth.getTime() - first.getTime()) / DAY_MS) + 1;
  return Math.ceil(span / 7) * 7;
}

/** Gun ekleme setDate ile: yaz saati gecislerinde DAY_MS kayiyor. */

/** Ust seritteki donem basligi -- "hangi aydayiz" sorusunun tek cevabi. */
function periodLabel(anchor: Date, view: View, days: number): string {
  if (view === "month") {
    return formatTrDate(anchor, { month: "long", year: "numeric", timeZone: "UTC" });
  }
  const first = rangeStart(anchor, view);
  const last = addAppDays(first, days - 1);
  const sameMonth = first.getUTCMonth() === last.getUTCMonth();
  const sameYear = first.getUTCFullYear() === last.getUTCFullYear();
  const head = formatTrDate(first, {
    timeZone: "UTC",
    day: "numeric",
    month: sameMonth ? undefined : "long",
    year: sameYear ? undefined : "numeric",
  });
  const tail = formatTrDate(last, {
    timeZone: "UTC",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  return `${head} – ${tail}`;
}

export function CalendarPage() {
  const [view, setView] = useState<View>("month");
  const [anchor, setAnchor] = useState(() => appDayUtc(new Date()));
  const online = useOnline();

  const days = rangeDays(anchor, view);
  const start = useMemo(() => rangeStart(anchor, view), [anchor, view]);
  const end = useMemo(() => addAppDays(start, days), [start, days]);

  const { data: events = [] } = useQuery({
    queryKey: ["calendar-events", start.toISOString(), days],
    queryFn: () =>
      api.get<CalendarEvent[]>(
        `/calendar/events?from=${encodeURIComponent(start.toISOString())}&to=${encodeURIComponent(end.toISOString())}`,
      ),
  });
  // Gun basina etkinlik haritasi: hucere basina filter yerine tek gecis.
  const eventsByDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const event of events) {
      const key = localDateKey(new Date(event.starts_at));
      const list = map.get(key);
      if (list) list.push(event);
      else map.set(key, [event]);
    }
    return map;
  }, [events]);
  const sync = useMutation({
    mutationFn: () => api.post("/calendar/sync"),
    onSuccess: () => invalidateAfter("calendar.write"),
  });
  const push = useMutation({
    mutationFn: (id: string) => api.post(`/plan/${id}/push`),
    onSuccess: () => invalidateAfter("calendar.write"),
  });

  function step(delta: number) {
    setAnchor((current) => {
      if (view === "week") return addAppDays(current, delta * 7);
      return new Date(Date.UTC(current.getUTCFullYear(), current.getUTCMonth() + delta, 1));
    });
  }

  const cells = Array.from({ length: days }, (_, i) => addAppDays(start, i));
  const today = appDayUtc(new Date());

  return (
    <PageFrame className="py-3">
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Takvim"
          title={<span className="first-letter:uppercase">{periodLabel(anchor, view, days)}</span>}
          hint={`${events.length} etkinlik`}
          action={
            <Button size="sm" variant="secondary" onClick={() => sync.mutate()} disabled={!online || sync.isPending}>
              <RefreshCw size={13} className={sync.isPending ? "animate-spin" : undefined} />
              Google'dan çek
            </Button>
          }
        >
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1">
              <Button size="sm" variant="ghost" onClick={() => step(-1)} title="Önceki dönem">
                <ChevronLeft size={14} />
              </Button>
              <Button size="sm" onClick={() => setAnchor(appDayUtc(new Date()))}>
                Bugün
              </Button>
              <Button size="sm" variant="ghost" onClick={() => step(1)} title="Sonraki dönem">
                <ChevronRight size={14} />
              </Button>
            </div>
            <span className="min-w-2 flex-1" />
            <div className="inline-flex rounded-control bg-surface-sunken p-0.5">
              {(["month", "week"] as View[]).map((value) => (
                <Button
                  key={value}
                  size="sm"
                  variant="ghost"
                  className={cx("border-0", view === value && "bg-surface shadow-raised")}
                  onClick={() => setView(value)}
                >
                  {value === "month" ? "Ay" : "Hafta"}
                </Button>
              ))}
            </div>
            <span className="text-meta text-muted">Google salt okunur · yalnız plan blokları gönderilir</span>
          </div>
        </WorkspacePaneHeader>

        <WorkspaceScrollArea className="overflow-x-auto p-3">
          {/* Ay izgarasi dar hucrelerle sigar; hafta gorunumu etkinlik detayi
              tasidigi icin daha genis olmali. */}
          <div
            className={cx(
              "overflow-hidden rounded-control border border-subtle bg-surface",
              view === "month" ? "min-w-calendar-month" : "min-w-calendar-week",
            )}
          >
            <div className="grid grid-cols-7 border-b border-subtle bg-surface-sunken">
              {WEEKDAYS.map((label) => (
                <div key={label} className="px-2 py-1.5 text-center label-caps">
                  {label}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-7">
              {cells.map((day) => {
                const rows = eventsByDay.get(localDateKey(day)) ?? [];
                const isToday = sameDay(day, today);
                // Ay gorunumunde komsu aylarin gunleri soluk kalir.
                const outside = view === "month" && day.getUTCMonth() !== anchor.getUTCMonth();

                return (
                  <div
                    key={day.toISOString()}
                    className={cx(
                      "min-h-28 border-b border-r border-subtle p-1.5 last:border-r-0",
                      view === "week" && "min-h-64",
                      outside && "bg-surface-sunken/40",
                    )}
                  >
                    <div className="mb-1 flex items-center gap-1.5">
                      <span
                        className={cx(
                          "numeral flex h-6 min-w-6 items-center justify-center rounded-full px-1 text-meta tabular-nums",
                          isToday ? "bg-accent font-medium text-canvas" : outside ? "text-muted" : "text-secondary",
                        )}
                      >
                        {day.getUTCDate()}
                      </span>
                      {/* Ayin ilk gunu: izgarada ay degisimini gorunur kilar. */}
                      {day.getUTCDate() === 1 && (
                        <span className="text-micro uppercase tracking-[0.08em] text-muted">
                          {formatTrDate(day, { month: "short", timeZone: "UTC" })}
                        </span>
                      )}
                    </div>

                    <div className="space-y-1">
                      {rows.slice(0, view === "week" ? 8 : 3).map((event) => (
                        <article
                          key={`${event.source}-${event.id}`}
                          className="rounded border border-subtle bg-canvas px-1.5 py-1"
                        >
                          <div className="flex items-start justify-between gap-1">
                            <span className="min-w-0 flex-1 truncate text-micro leading-4 text-primary">
                              {event.title}
                            </span>
                            {view === "week" && <Chip>{event.source}</Chip>}
                          </div>
                          <p className="text-micro leading-4 text-muted">
                            {event.all_day
                              ? "tüm gün"
                              : formatTrDateTime(event.starts_at, { hour: "2-digit", minute: "2-digit" })}
                          </p>
                          {view === "week" && !event.read_only && !event.google_event_id && (
                            <Button
                              size="sm"
                              className="mt-1 h-6 px-2 text-micro"
                              disabled={!online || push.isPending}
                              onClick={() => push.mutate(event.id)}
                            >
                              Google'a gönder
                            </Button>
                          )}
                          {view === "week" && event.url && (
                            <a
                              href={event.url}
                              target="_blank"
                              rel="noreferrer"
                              className="mt-0.5 block text-micro text-accent hover:underline"
                            >
                              Aç ↗
                            </a>
                          )}
                        </article>
                      ))}
                      {rows.length > (view === "week" ? 8 : 3) && (
                        <p className="px-1 text-micro text-muted">+{rows.length - (view === "week" ? 8 : 3)} daha</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {events.length === 0 && (
            <div className="py-10">
              <Empty variant="page" title="Bu dönem boş">
                Google'dan çekebilir ya da haftalık plandan blok gönderebilirsin.
              </Empty>
            </div>
          )}
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
