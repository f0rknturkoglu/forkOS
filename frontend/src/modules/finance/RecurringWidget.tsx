import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { RecurringPayment } from "@/core/types";
import { Panel } from "@/core/ui";
export function RecurringWidget() { const { data = [] } = useQuery({ queryKey: ["recurring-widget"], queryFn: () => api.get<RecurringPayment[]>("/recurring-payments") }); return <Panel title="Yaklaşan ödemeler"><div className="space-y-2 text-xs">{data.filter(x => x.active).slice(0,5).map(x => <div key={x.id} className="flex justify-between"><span>{x.title}</span><span>{x.next_due_at ?? "—"}</span></div>)}{!data.length && <span className="text-neutral-500">Ödeme yok.</span>}</div></Panel>; }
