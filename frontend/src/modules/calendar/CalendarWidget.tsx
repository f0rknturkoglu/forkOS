import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Empty, RowList, Section, cx, relativeTime } from "@/core/ui";
import type { CalendarEvent } from "@/core/types";
import { formatTrDateTime } from "@/lib/date";

/** Sonraki 3 gunun takvim olaylari (agenda bugunu gosterir; bu ileriye bakis). */
export function CalendarWidget() {
  const now = new Date();
  const from = now.toISOString();
  const to = new Date(now.getTime() + 3 * 86_400_000).toISOString();
  const { data = [] } = useQuery({
    queryKey: ["calendar-events", from, to],
    queryFn: () => api.get<CalendarEvent[]>(`/calendar/events${qs({ from, to })}`),
  });
  return (
    <Section title="Yaklaşan etkinlikler">
      {data.length === 0 ? (
        <Empty>Sonraki 3 günde etkinlik yok.</Empty>
      ) : (
        <RowList>
          {data.slice(0, 5).map((event) => (
            <div key={event.id} className="flex items-baseline justify-between gap-2 py-2 text-meta">
              <span className="truncate text-body text-primary">{event.title}</span>
              <span className={cx("shrink-0", event.all_day ? "text-muted" : "text-accent")}>
                {event.all_day
                  ? relativeTime(event.starts_at)
                  : formatTrDateTime(event.starts_at, { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          ))}
        </RowList>
      )}
    </Section>
  );
}
