import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { CalendarEvent } from "@/core/types";
import { Badge, RowList, Section } from "@/core/ui";

export const TODAY_CALENDAR_KEY = ["calendar-events", "today"] as const;

export function TodayScheduleWidget() {
  const start = new Date(); start.setHours(0,0,0,0); const end = new Date(start.getTime() + 86400000);
  const { data = [] } = useQuery({ queryKey: TODAY_CALENDAR_KEY, queryFn: () => api.get<CalendarEvent[]>(`/calendar/events?from=${encodeURIComponent(start.toISOString())}&to=${encodeURIComponent(end.toISOString())}`) });
  return <Section title="Bugünün programı">{data.length === 0 ? <span className="text-meta text-muted">Bugün boş.</span> : <RowList>{data.slice(0, 7).map(e => <div key={`${e.source}-${e.id}`} className="flex items-center justify-between gap-2 py-2 text-meta"><span className="truncate">{e.all_day ? "Tüm gün" : new Date(e.starts_at).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })} · {e.title}</span><Badge>{e.source}</Badge></div>)}</RowList>}</Section>;
}
