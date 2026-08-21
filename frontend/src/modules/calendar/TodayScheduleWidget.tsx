import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { CalendarEvent } from "@/core/types";
import { Badge, Panel } from "@/core/ui";

export function TodayScheduleWidget() {
  const start = new Date(); start.setHours(0,0,0,0); const end = new Date(start.getTime() + 86400000);
  const { data = [] } = useQuery({ queryKey: ["calendar-today"], queryFn: () => api.get<CalendarEvent[]>(`/calendar/events?from=${encodeURIComponent(start.toISOString())}&to=${encodeURIComponent(end.toISOString())}`) });
  return <Panel title="Bugünün programı"><div className="space-y-2">{data.slice(0, 7).map(e => <div key={`${e.source}-${e.id}`} className="flex items-center justify-between gap-2 text-meta"><span className="truncate">{e.all_day ? "Tüm gün" : new Date(e.starts_at).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })} · {e.title}</span><Badge>{e.source}</Badge></div>)}{data.length === 0 && <span className="text-meta text-muted">Bugün boş.</span>}</div></Panel>;
}
