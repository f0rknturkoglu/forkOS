import { navigate } from "@/app/router";
import { Tabs } from "@/core/ui";

/** Üç uyumlu rota, tek görev çalışma alanının yerel görünümleri. */
export function PlanViews({ view }: { view: "tasks" | "week" | "routines" }) {
  return (
    <div className="border-b border-subtle px-3 py-2">
      <Tabs
        value={view}
        onChange={(view) => {
          navigate(view === "week" ? "/planner" : view === "routines" ? "/habits" : "/todos");
        }}
        ariaLabel="Plan görünümü"
        items={[
          { id: "tasks", label: "Görevler" },
          { id: "week", label: "Bu Hafta" },
          { id: "routines", label: "Rutinler" },
        ]}
      />
    </div>
  );
}
