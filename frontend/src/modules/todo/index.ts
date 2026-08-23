import { ListChecks } from "lucide-react";
import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { invalidate } from "@/core/queryClient";
import { TodoPage } from "./TodoPage";
import { WeeklyPlannerPage } from "./WeeklyPlannerPage";

registerModule({
  id: "todo", title: "Görevler", icon: ListChecks, group: "do",
  routes: [
    { path: "/todos", element: TodoPage },
    { path: "/habits", element: TodoPage, title: "Rutin görevler" },
    { path: "/planner", element: WeeklyPlannerPage },
  ],
  commands: [
    { id: "todo.open", label: "Görevleri aç", run: () => navigate("/todos") },
    { id: "todo.routines", label: "Rutin görevleri aç", run: () => navigate("/habits") },
    { id: "planner.open", label: "Haftalık planı aç", run: () => navigate("/planner") },
    { id: "todo.quick", label: "Hızlı görev ekle",
      ask: { label: "Görev başlığı", placeholder: "Ne yapılacak?" },
      run: async (title) => {
        if (!title?.trim()) return;
        await api.post("/todos", { title: title.trim() });
        invalidate("todos", "activity");
        navigate("/todos");
      } },
  ],
});
