import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ClipboardCheck } from "lucide-react";
import { api, qs } from "@/core/api";
import { SourceHealthAccordion } from "@/core/SourceHealthAccordion";
import { Button, Chip, Empty, PageFrame, PageHeader, Section, Toolbar, cx, relativeTime } from "@/core/ui";
import { formatTrDate, localDateKey } from "@/lib/date";
import { typeLabel } from "@/core/entityRegistry";
import type { ActivityEvent, SourceHealth } from "@/core/types";

/** Geçmiş değerlendirmeler -- GET /reviews ucu. Etiket döneme gore. */
interface ReviewOut {
  id: string;
  kind: "daily" | "weekly";
  period_start: string;
  period_end: string;
  note: string | null;
}

function reviewLabel(start: string, end: string): string {
  const s = new Date(start + "T00:00:00");
  const e = new Date(end + "T00:00:00");
  const month = (d: Date) => formatTrDate(d, { day: "numeric", month: "short" });
  if (s.toDateString() === e.toDateString()) return month(s);
  return `${month(s)} – ${month(e)}`;
}
import { ALERT_VERBS, describe } from "@/core/verbs";

function dayLabel(iso: string): string {
  return formatTrDate(iso, { weekday: "long", day: "numeric", month: "long" });
}

function isAlert(event: ActivityEvent): boolean {
  return (
    ALERT_VERBS.has(event.verb) || (event.verb === "source_sync.completed" && Number(event.payload.errors ?? 0) > 0)
  );
}

export function ActivityPage() {
  const [onlyAlerts, setOnlyAlerts] = useState(false);
  const [healthOpen, setHealthOpen] = useState(false);
  const [openDays, setOpenDays] = useState<Set<string>>(new Set());

  const { data = [], isLoading } = useQuery({
    queryKey: ["activity"],
    queryFn: () => api.get<ActivityEvent[]>(`/activity${qs({ limit: 200 })}`),
  });

  const { data: health = [] } = useQuery({
    queryKey: ["sources", "health"],
    queryFn: () => api.get<SourceHealth[]>("/sources/health"),
  });
  const { data: reviews = [] } = useQuery({
    queryKey: ["reviews"],
    queryFn: () => api.get<ReviewOut[]>("/reviews?limit=10"),
  });

  const events = useMemo(() => (onlyAlerts ? data.filter(isAlert) : data), [data, onlyAlerts]);
  const dayEntries = useMemo(() => {
    const entries = new Map<string, { key: string; label: string; events: ActivityEvent[] }>();
    for (const event of events) {
      // Gruplama app gunune gore (Faz 14) -- backend heatmap'i ile ayni gun.
      const key = localDateKey(new Date(event.occurred_at));
      const entry = entries.get(key) ?? { key, label: dayLabel(event.occurred_at), events: [] };
      entry.events.push(event);
      entries.set(key, entry);
    }
    return [...entries.values()];
  }, [events]);
  const dayKeys = useMemo(() => dayEntries.map(({ key }) => key), [dayEntries]);
  const allDaysOpen = dayKeys.length > 0 && dayKeys.every((day) => openDays.has(day));

  const problems = health.filter((s) => s.status !== "ok");

  useEffect(() => {
    setOpenDays((current) => {
      const visibleDays = new Set(dayKeys);
      const next = new Set([...current].filter((day) => visibleDays.has(day)));
      if (dayKeys.length > 0 && !dayKeys.some((day) => next.has(day))) {
        next.add(dayKeys[0]);
      }
      return next.size === current.size && [...next].every((day) => current.has(day)) ? current : next;
    });
  }, [dayKeys]);

  function setDayOpen(day: string, open: boolean) {
    setOpenDays((current) => {
      const next = new Set(current);
      if (open) next.add(day);
      else next.delete(day);
      return next;
    });
  }

  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Sistem" title="Etkinlik" />
      <Toolbar>
        <Button variant={onlyAlerts ? "primary" : "ghost"} onClick={() => setOnlyAlerts((v) => !v)}>
          Sadece uyarılar
        </Button>
        {dayKeys.length > 0 && (
          <Button variant="ghost" onClick={() => setOpenDays(new Set(allDaysOpen ? [] : dayKeys))}>
            {allDaysOpen ? "Tümünü daralt" : "Tümünü genişlet"}
          </Button>
        )}
        <span className="ml-auto text-meta text-muted">{events.length} hareket</span>
      </Toolbar>

      {problems.length > 0 && (
        <SourceHealthAccordion sources={problems} open={healthOpen} onOpenChange={setHealthOpen} />
      )}

      {reviews.length > 0 && (
        <Section title="Değerlendirmeler">
          <ul className="space-y-1">
            {reviews.map((review) => (
              <li key={review.id}>
                <a
                  href={`#/review/${review.kind}`}
                  className="flex items-center gap-2.5 rounded-control border border-subtle bg-surface px-3 py-2 text-body text-secondary transition hover:border-strong hover:text-primary"
                >
                  <ClipboardCheck size={14} className="shrink-0 text-muted" />
                  <span className="label-caps text-secondary">{review.kind === "weekly" ? "Haftalık" : "Günlük"}</span>
                  <span className="min-w-0 flex-1 truncate text-meta text-muted">
                    {reviewLabel(review.period_start, review.period_end)}
                  </span>
                  {review.note && <span className="truncate text-meta">{review.note}</span>}
                </a>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {isLoading ? (
        <p className="text-body text-muted">Yükleniyor…</p>
      ) : events.length === 0 ? (
        <Empty>Henüz kayıt yok.</Empty>
      ) : (
        dayEntries.map(({ key, label, events: dayEvents }) => {
          const alertCount = dayEvents.filter(isAlert).length;
          const open = openDays.has(key);
          return (
            <details
              key={key}
              data-activity-day
              open={open}
              onToggle={(event) => setDayOpen(key, event.currentTarget.open)}
              className="overflow-hidden rounded-card border border-subtle bg-surface shadow-card"
            >
              <summary className="flex cursor-pointer list-none items-center gap-3 px-3.5 py-2 marker:content-none">
                <ChevronDown className={cx("transition-transform", open && "rotate-180")} size={15} />
                <span className="label-caps text-secondary">{label}</span>
                <span className="ml-auto text-meta text-muted">{dayEvents.length} hareket</span>
                {alertCount > 0 && <Chip tone="warn">{alertCount} uyarı</Chip>}
              </summary>
              <div className="border-t border-subtle px-3.5 py-3">
                <ul className="relative ml-1 border-l border-strong">
                  {dayEvents.map((event) => {
                    const alert = isAlert(event);
                    return (
                      <li key={event.id} className="relative min-h-10 py-2 pl-5 text-body">
                        <span className="absolute -left-[5px] top-[15px]" aria-hidden>
                          <span
                            className={cx(
                              "block h-2.5 w-2.5 rounded-full ring-[3px] ring-canvas",
                              alert ? "bg-warn" : "bg-strong",
                            )}
                          />
                        </span>
                        <div className="min-w-0">
                          <span className={cx(alert ? "text-warn" : "text-secondary")}>
                            {describe(event.verb, event.payload)}
                          </span>
                          <span className="ml-2 text-meta text-muted">{relativeTime(event.occurred_at)}</span>
                          {event.entity_type && (
                            <span className="ml-2">
                              <Chip>{typeLabel(event.entity_type)}</Chip>
                            </span>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </details>
          );
        })
      )}
    </PageFrame>
  );
}
