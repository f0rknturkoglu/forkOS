import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";
import { api, qs } from "@/core/api";
import { SourceHealthAccordion } from "@/core/SourceHealthAccordion";
import { Badge, Button, Empty, PageFrame, PageHeader, Toolbar, cx, relativeTime } from "@/core/ui";
import type { ActivityEvent, SourceHealth } from "@/core/types";
import { ALERT_VERBS, describe } from "./verbs";

function localDayKey(iso: string): string {
  const date = new Date(iso);
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function dayLabel(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", {
    weekday: "long", day: "numeric", month: "long",
  });
}

function isAlert(event: ActivityEvent): boolean {
  return ALERT_VERBS.has(event.verb)
    || (event.verb === "source_sync.completed" && Number(event.payload.errors ?? 0) > 0);
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

  const events = useMemo(
    () => (onlyAlerts ? data.filter(isAlert) : data),
    [data, onlyAlerts],
  );
  const dayEntries = useMemo(() => {
    const entries = new Map<string, { key: string; label: string; events: ActivityEvent[] }>();
    for (const event of events) {
      const key = localDayKey(event.occurred_at);
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
      return next.size === current.size && [...next].every((day) => current.has(day))
        ? current
        : next;
    });
  }, [dayKeys]);

  function setDayOpen(day: string, open: boolean) {
    setOpenDays((current) => {
      const next = new Set(current);
      if (open) next.add(day); else next.delete(day);
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
                {alertCount > 0 && <Badge tone="warn">{alertCount} uyarı</Badge>}
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
                          <span className="ml-2 text-meta text-muted">
                            {relativeTime(event.occurred_at)}
                          </span>
                          {event.entity_type && (
                            <span className="ml-2"><Badge>{event.entity_type}</Badge></span>
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
