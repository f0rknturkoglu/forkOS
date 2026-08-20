import { useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Empty, Panel } from "@/core/ui";
import type { PlanSlot } from "@/core/types";
import { navigate } from "@/app/router";

export function PlannerWidget() {
  const today = new Date().toISOString().slice(0, 10);
  const { data: slots = [] } = useQuery({ queryKey: ["plan", "today"],
    queryFn: () => api.get<PlanSlot[]>(`/plan${qs({ week: today })}`) });
  const visible = slots.filter((slot) => slot.day === today);
  return <Panel title="Bugunun plani" action={<button onClick={() => navigate("/planner")}
    className="text-xs text-neutral-500 hover:text-neutral-300">hafta →</button>}>
    {visible.length === 0 ? <Empty>Bugun icin blok yok.</Empty> : <ul className="space-y-2">
      {visible.map((slot) => <li key={slot.id} className="flex gap-2 text-sm">
        <span className="w-12 text-neutral-500">{slot.start_min == null ? "—" :
          `${String(Math.floor(slot.start_min / 60)).padStart(2, "0")}:${String(slot.start_min % 60).padStart(2, "0")}`}</span>
        <span className="truncate">{slot.title}</span></li>)}</ul>}
  </Panel>;
}
