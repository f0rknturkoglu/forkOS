import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Badge, Button, Empty, PageFrame, PageHeader, Section, Toolbar, cx, relativeTime } from "@/core/ui";
import type { ActivityEvent, SourceHealth } from "@/core/types";
import { Heatmap } from "./Heatmap";
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
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Sistem" title="Etkinlik" />
      <Heatmap />
      <Toolbar>
        <Button variant={onlyAlerts ? "primary" : "ghost"} onClick={() => setOnlyAlerts((v) => !v)}>
          Sadece uyarılar
        </Button>
        <span className="ml-auto text-meta text-muted">{events.length} hareket</span>
      </Toolbar>

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
          <Section key={day} title={day}>
            <ul className="relative ml-1 border-l border-strong">
              {dayEvents.map((event) => {
                const alert = ALERT_VERBS.has(event.verb)
                  || (event.verb === "source_sync.completed" && Number(event.payload.errors ?? 0) > 0);
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
          </Section>
        ))
      )}
    </PageFrame>
  );
}
