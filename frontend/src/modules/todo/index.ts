import { invalidateAfter } from "@/core/invalidation";
import { lazy } from "react";
import { ListChecks } from "lucide-react";
import { OverdueTodosWidget } from "./OverdueTodosWidget";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { invalidate } from "@/core/queryClient";

const TodoPage = lazy(() => import("./TodoPage").then((module) => ({ default: module.TodoPage })));
const WeeklyPlannerPage = lazy(() =>
  import("./WeeklyPlannerPage").then((module) => ({ default: module.WeeklyPlannerPage })),
);

registerModule({
  id: "todo",
  title: "Görevler",
  icon: ListChecks,
  group: "do",
  routes: [
    { path: "/todos", element: TodoPage },
    { path: "/habits", element: TodoPage, title: "Rutin görevler" },
    { path: "/planner", element: WeeklyPlannerPage },
  ],
  todayWidgets: [{ component: OverdueTodosWidget, slot: "right", order: 15 }],
  commands: [
    { id: "todo.open", label: "Görevleri aç", run: () => navigate("/todos") },
    { id: "todo.routines", label: "Rutin görevleri aç", run: () => navigate("/habits") },
    { id: "planner.open", label: "Haftalık planı aç", run: () => navigate("/planner") },
    {
      id: "todo.quick",
      label: "Hızlı görev ekle",
      ask: { label: "Görev başlığı", placeholder: "Ne yapılacak?" },
      run: async (title) => {
        if (!title?.trim()) return;
        await api.post("/todos", { title: title.trim() });
        invalidateAfter("todo.write");
        navigate("/todos");
      },
    },
  ],
});
