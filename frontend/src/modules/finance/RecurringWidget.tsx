import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import type { RecurringPayment } from "@/core/types";
import { RowList, Section } from "@/core/ui";
export function RecurringWidget() { const { data = [] } = useQuery({ queryKey: ["recurring-widget"], queryFn: () => api.get<RecurringPayment[]>("/recurring-payments") }); const active = data.filter(x => x.active).slice(0, 5); return <Section title="Yaklaşan ödemeler">{active.length === 0 ? <span className="text-meta text-muted">Ödeme yok.</span> : <RowList>{active.map(x => <div key={x.id} className="flex justify-between gap-3 py-2 text-meta"><span className="truncate">{x.title}</span><span className="shrink-0 text-muted">{x.next_due_at ?? "—"}</span></div>)}</RowList>}</Section>; }
