import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Badge, Button, Empty, cx, relativeTime } from "@/core/ui";
import type { ActivityEvent, SourceHealth } from "@/core/types";
import { ALERT_VERBS, describe } from "./verbs";

function dayKey(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", {
    weekday: "long", day: "numeric", month: "long",
  });
}

export function ActivityPage() {
  const [onlyAlerts, setOnlyAlerts] = useState(false);

  const { data = [], isLoading } = useQuery({
    queryKey: ["activity"],
    queryFn: () => api.get<ActivityEvent[]>(`/activity${qs({ limit: 200 })}`),
  });

  const { data: health = [] } = useQuery({
    queryKey: ["sources", "health"],
    queryFn: () => api.get<SourceHealth[]>("/sources/health"),
  });

  const events = onlyAlerts ? data.filter((e) => ALERT_VERBS.has(e.verb)) : data;
  const days = events.reduce<Record<string, ActivityEvent[]>>((acc, event) => {
    (acc[dayKey(event.occurred_at)] ??= []).push(event);
    return acc;
  }, {});

  const problems = health.filter((s) => s.status !== "ok");

  return (
    <div className="p-6">
      <header className="mb-4 flex items-center justify-between">
        <Button variant={onlyAlerts ? "primary" : "ghost"} onClick={() => setOnlyAlerts((v) => !v)}>
          sadece uyarilar
        </Button>
      </header>

      {problems.length > 0 && (
        <div className="mb-4 rounded border border-warn-border bg-warn-surface p-3">
          <div className="mb-2 text-meta font-medium text-warn">Kaynak sagligi</div>
          <ul className="space-y-1 text-meta text-warn">
            {problems.map((source) => (
              <li key={source.source}>
                <span className="font-mono">{source.source}</span> · {source.status}
                {source.error && ` · ${source.error.slice(0, 120)}`}
              </li>
            ))}
          </ul>
        </div>
      )}

      {isLoading ? (
        <p className="text-body text-muted">Yükleniyor…</p>
      ) : events.length === 0 ? (
        <Empty>Henüz kayıt yok.</Empty>
      ) : (
        Object.entries(days).map(([day, dayEvents]) => (
          <section key={day} className="mb-6">
            <h2 className="mb-2 text-meta uppercase tracking-wide text-muted">{day}</h2>
            <ul className="space-y-1 border-l border-subtle pl-4">
              {dayEvents.map((event) => (
                <li key={event.id} className="relative py-1 text-body">
                  <span
                    className={cx(
                      "absolute -left-[21px] top-2.5 h-1.5 w-1.5 rounded-full",
                      ALERT_VERBS.has(event.verb) ? "bg-warn" : "bg-strong",
                    )}
                  />
                  <span
                    className={cx(
                      ALERT_VERBS.has(event.verb) ? "text-warn" : "text-secondary",
                    )}
                  >
                    {describe(event.verb, event.payload)}
                  </span>
                  <span className="ml-2 text-meta text-muted">
                    {relativeTime(event.occurred_at)}
                  </span>
                  {event.entity_type && (
                    <span className="ml-2">
                      <Badge>{event.entity_type}</Badge>
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </div>
  );
}
