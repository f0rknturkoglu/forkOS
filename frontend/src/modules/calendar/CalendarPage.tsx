import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { CalendarEvent } from "@/core/types";
import { Badge, Button, Empty, Panel } from "@/core/ui";
import { useInvalidate } from "@/lib/hooks";

function monday(value: Date) { const d = new Date(value); d.setHours(0,0,0,0); d.setDate(d.getDate() - ((d.getDay() + 6) % 7)); return d; }
export function CalendarPage() {
  const [week, setWeek] = useState(() => monday(new Date())); const invalidate = useInvalidate();
  const end = useMemo(() => new Date(week.getTime() + 7 * 86400000), [week]);
  const path = `/calendar/events?from=${encodeURIComponent(week.toISOString())}&to=${encodeURIComponent(end.toISOString())}`;
  const { data: events = [] } = useQuery({ queryKey: ["calendar-events", week.toISOString()], queryFn: () => api.get<CalendarEvent[]>(path) });
  const sync = useMutation({ mutationFn: () => api.post("/calendar/sync"), onSuccess: () => invalidate("calendar-events", "activity") });
  const push = useMutation({ mutationFn: (id: string) => api.post(`/plan/${id}/push`), onSuccess: () => invalidate("calendar-events", "plan", "activity") });
  const days = Array.from({ length: 7 }, (_, i) => new Date(week.getTime() + i * 86400000));
  return <div className="space-y-4 p-6"><header className="flex items-center justify-between"><div><h1 className="text-xl font-semibold">Calendar</h1><p className="text-xs text-neutral-500">Google → forkOS salt okunur; yalnızca plan slot’ları Google’a gönderilir.</p></div><div className="flex gap-2"><Button onClick={() => setWeek(new Date(week.getTime() - 7 * 86400000))}>←</Button><Button onClick={() => setWeek(monday(new Date()))}>bugün</Button><Button onClick={() => setWeek(new Date(week.getTime() + 7 * 86400000))}>→</Button><Button variant="primary" onClick={() => sync.mutate()} disabled={sync.isPending}>Google’dan çek</Button></div></header>
    <div className="grid gap-3 lg:grid-cols-7">{days.map(day => { const rows = events.filter(e => new Date(e.starts_at).toDateString() === day.toDateString()); return <Panel key={day.toISOString()} title={<span>{day.toLocaleDateString("tr-TR", { weekday: "short", day: "numeric" })}</span>}><div className="space-y-2">{rows.map(event => <article key={`${event.source}-${event.id}`} className={`rounded border p-2 ${event.source === "google" ? "border-violet-900 bg-violet-950/20" : "border-sky-900 bg-sky-950/20"}`}><div className="flex items-start justify-between gap-1"><span className="text-xs font-medium">{event.title}</span><Badge>{event.source}</Badge></div><p className="mt-1 text-[11px] text-neutral-500">{event.all_day ? "tüm gün" : new Date(event.starts_at).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}</p>{!event.read_only && !event.google_event_id && <Button onClick={() => push.mutate(event.id)}>Google’a gönder</Button>}{event.url && <a href={event.url} target="_blank" className="mt-1 block text-[11px] text-sky-400">aç ↗</a>}</article>)}{rows.length === 0 && <span className="text-[11px] text-neutral-700">boş</span>}</div></Panel>; })}</div>{events.length === 0 && <Empty>Bu hafta etkinlik yok.</Empty>}</div>;
}
