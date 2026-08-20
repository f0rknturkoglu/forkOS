import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Panel } from "@/core/ui";
import type { Deadline, Notification } from "@/core/types";

export function DeadlineWidget() {
  const { data = [] } = useQuery({ queryKey: ["deadlines"], queryFn: () => api.get<Deadline[]>("/deadlines") });
  return <Panel title="Yaklaşan son tarihler"><div className="space-y-2">{data.slice(0, 5).map(x => <a key={x.entity_id} href={x.module === "opportunity" ? "#/opportunities" : "#/todos"} className="flex justify-between text-xs"><span>{x.title}</span><span className="text-amber-400">{new Date(x.due_at).toLocaleDateString("tr-TR")}</span></a>)}{!data.length && <p className="text-xs text-neutral-600">Yaklaşan son tarih yok.</p>}</div></Panel>;
}

export function NotificationWidget() {
  const { data = [] } = useQuery({ queryKey: ["notifications"], queryFn: () => api.get<Notification[]>("/notifications") });
  return <Panel title={`Bildirimler · ${data.filter(x => !x.read_at).length}`}><div className="space-y-2">{data.slice(0, 4).map(x => <div key={x.id} className="text-xs"><p>{x.title}</p>{x.body && <p className="text-neutral-600">{x.body}</p>}</div>)}</div></Panel>;
}
