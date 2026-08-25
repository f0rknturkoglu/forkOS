import { invalidateAfter } from "@/core/invalidation";
import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, RefreshCw } from "lucide-react";
import { api } from "@/core/api";
import type { CalendarEvent } from "@/core/types";
import {Button, Chip, Empty, PageFrame, PageHeader, Section, Toolbar, cx} from "@/core/ui";
import {useOnline} from "@/lib/hooks";

type View = "week" | "month";

const DAY_MS = 86_400_000;
const WEEKDAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];

function startOfDay(value: Date): Date {
  const d = new Date(value);
  d.setHours(0, 0, 0, 0);
  return d;
}

/** Haftanin pazartesisi. getDay: 0=pazar, o yuzden +6 %7. */
function monday(value: Date): Date {
  const d = startOfDay(value);
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return d;
}

function sameDay(a: Date, b: Date): boolean {
  return a.toDateString() === b.toDateString();
}

/** Gorunumun kapsadigi ilk gun: hafta = pazartesi, ay = ayin ilk haftasinin pazartesisi. */
function rangeStart(anchor: Date, view: View): Date {
  if (view === "week") return monday(anchor);
  return monday(new Date(anchor.getFullYear(), anchor.getMonth(), 1));
}

/** Ay izgarasi TAM haftalardan olusur; ayin son gununu kapsayacak kadar hafta. */
function rangeDays(anchor: Date, view: View): number {
  if (view === "week") return 7;
  const first = rangeStart(anchor, view);
  const lastOfMonth = startOfDay(new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0));
  const span = Math.round((lastOfMonth.getTime() - first.getTime()) / DAY_MS) + 1;
  return Math.ceil(span / 7) * 7;
}

/** Gun ekleme setDate ile: yaz saati gecislerinde DAY_MS kayiyor. */
function addDays(from: Date, count: number): Date {
  const d = new Date(from);
  d.setDate(d.getDate() + count);
  return d;
}

/** Ust seritteki donem basligi -- "hangi aydayiz" sorusunun tek cevabi. */
function periodLabel(anchor: Date, view: View, days: number): string {
  if (view === "month") {
    return anchor.toLocaleDateString("tr-TR", { month: "long", year: "numeric" });
  }
  const first = rangeStart(anchor, view);
  const last = addDays(first, days - 1);
  const sameMonth = first.getMonth() === last.getMonth();
  const sameYear = first.getFullYear() === last.getFullYear();
  const head = first.toLocaleDateString("tr-TR", {
    day: "numeric",
    month: sameMonth ? undefined : "long",
    year: sameYear ? undefined : "numeric",
  });
  const tail = last.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
  return `${head} – ${tail}`;
}

export function CalendarPage() {
  const [view, setView] = useState<View>("month");
  const [anchor, setAnchor] = useState(() => new Date());
  const online = useOnline();

  const days = rangeDays(anchor, view);
  const start = useMemo(() => rangeStart(anchor, view), [anchor, view]);
  const end = useMemo(() => addDays(start, days), [start, days]);

  const { data: events = [] } = useQuery({
    queryKey: ["calendar-events", start.toISOString(), days],
    queryFn: () =>
      api.get<CalendarEvent[]>(
        `/calendar/events?from=${encodeURIComponent(start.toISOString())}&to=${encodeURIComponent(end.toISOString())}`,
      ),
  });
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
      if (view === "week") return addDays(current, delta * 7);
      return new Date(current.getFullYear(), current.getMonth() + delta, 1);
    });
  }

  const cells = Array.from({ length: days }, (_, i) => addDays(start, i));
  const today = new Date();

  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Planlama" title="Takvim" />
      <p className="text-meta text-muted">
        Google → forkOS salt okunur; yalnızca plan blokları Google'a gönderilir.
      </p>

      <Toolbar>
        <div className="flex items-center gap-1">
          <Button size="sm" onClick={() => step(-1)} title="Önceki">
            <ChevronLeft size={14} />
          </Button>
          <Button size="sm" onClick={() => setAnchor(new Date())}>Bugün</Button>
          <Button size="sm" onClick={() => step(1)} title="Sonraki">
            <ChevronRight size={14} />
          </Button>
        </div>

        {/* Donem basligi: hangi ay/hafta oldugu artik acikca yaziyor. */}
        <h2 className="font-serif text-title text-primary first-letter:uppercase">
          {periodLabel(anchor, view, days)}
        </h2>

        <span className="min-w-2 flex-1" />

        <div className="flex items-center gap-1">
          {(["month", "week"] as View[]).map((value) => (
            <Button key={value} size="sm" variant={view === value ? "primary" : "ghost"}
              onClick={() => setView(value)}>
              {value === "month" ? "Ay" : "Hafta"}
            </Button>
          ))}
        </div>
        <Button size="sm" variant="secondary" onClick={() => sync.mutate()} disabled={!online || sync.isPending}>
          <RefreshCw size={13} className={sync.isPending ? "animate-spin" : undefined} />
          Google'dan çek
        </Button>
      </Toolbar>

      <div className="overflow-x-auto">
        {/* Ay izgarasi dar hucrelerle sigar; hafta gorunumu etkinlik detayi
            tasidigi icin daha genis olmali. */}
        <div className={cx(
          "overflow-hidden rounded-card border border-subtle bg-surface shadow-card",
          view === "month" ? "min-w-[560px]" : "min-w-[760px]",
        )}>
          <div className="grid grid-cols-7 border-b border-subtle bg-surface-sunken">
            {WEEKDAYS.map((label) => (
              <div key={label} className="px-2 py-1.5 text-center label-caps">{label}</div>
            ))}
          </div>

          <div className="grid grid-cols-7">
            {cells.map((day) => {
              const rows = events.filter((event) => sameDay(new Date(event.starts_at), day));
              const isToday = sameDay(day, today);
              // Ay gorunumunde komsu aylarin gunleri soluk kalir.
              const outside = view === "month" && day.getMonth() !== anchor.getMonth();

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
                    <span className={cx(
                      "numeral flex h-6 min-w-6 items-center justify-center rounded-full px-1 text-meta tabular-nums",
                      isToday ? "bg-accent font-medium text-canvas" : outside ? "text-muted" : "text-secondary",
                    )}>
                      {day.getDate()}
                    </span>
                    {/* Ayin ilk gunu: izgarada ay degisimini gorunur kilar. */}
                    {day.getDate() === 1 && (
                      <span className="text-micro uppercase tracking-[0.08em] text-muted">
                        {day.toLocaleDateString("tr-TR", { month: "short" })}
                      </span>
                    )}
                  </div>

                  <div className="space-y-1">
                    {rows.slice(0, view === "week" ? 8 : 3).map((event) => (
                      <article key={`${event.source}-${event.id}`}
                        className="rounded border border-subtle bg-canvas px-1.5 py-1">
                        <div className="flex items-start justify-between gap-1">
                          <span className="min-w-0 flex-1 truncate text-micro leading-4 text-primary">
                            {event.title}
                          </span>
                          {view === "week" && <Chip>{event.source}</Chip>}
                        </div>
                        <p className="text-micro leading-4 text-muted">
                          {event.all_day
                            ? "tüm gün"
                            : new Date(event.starts_at).toLocaleTimeString("tr-TR", {
                                hour: "2-digit", minute: "2-digit",
                              })}
                        </p>
                        {view === "week" && !event.read_only && !event.google_event_id && (
                          <Button size="sm" className="mt-1 h-6 px-2 text-micro"
                            disabled={!online || push.isPending}
                            onClick={() => push.mutate(event.id)}>
                            Google'a gönder
                          </Button>
                        )}
                        {view === "week" && event.url && (
                          <a href={event.url} target="_blank" rel="noreferrer"
                            className="mt-0.5 block text-micro text-accent hover:underline">
                            Aç ↗
                          </a>
                        )}
                      </article>
                    ))}
                    {rows.length > (view === "week" ? 8 : 3) && (
                      <p className="px-1 text-micro text-muted">
                        +{rows.length - (view === "week" ? 8 : 3)} daha
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {events.length === 0 && (
        <Section title="Bu dönem">
          <Empty>Kayıtlı etkinlik yok. Google'dan çekebilir ya da haftalık plandan blok gönderebilirsin.</Empty>
        </Section>
      )}
    </PageFrame>
  );
}
