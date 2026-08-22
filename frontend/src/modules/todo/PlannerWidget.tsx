import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Empty, RowList, Section } from "@/core/ui";
import type { PlanSlot } from "@/core/types";
import { navigate } from "@/app/router";

export function PlannerWidget() {
  const today = new Date().toISOString().slice(0, 10);
  const { data: slots = [] } = useQuery({ queryKey: ["plan", "today"],
    queryFn: () => api.get<PlanSlot[]>(`/plan${qs({ week: today })}`) });
  const visible = slots.filter((slot) => slot.day === today);
  return <Section title="Bugünün planı" action={<button onClick={() => navigate("/planner")}
    className="text-meta text-muted hover:text-primary">hafta →</button>}>
    {visible.length === 0 ? <Empty>Bugün için blok yok.</Empty> : <RowList>
      {visible.map((slot) => <div key={slot.id} className="flex gap-2 py-2 text-body">
        <span className="w-12 text-muted">{slot.start_min == null ? "—" :
          `${String(Math.floor(slot.start_min / 60)).padStart(2, "0")}:${String(slot.start_min % 60).padStart(2, "0")}`}</span>
        <span className="truncate">{slot.title}</span></div>)}</RowList>}
  </Section>;
}
