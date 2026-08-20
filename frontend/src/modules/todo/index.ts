import { registerModule } from "@/core/registry";
import { navigate } from "@/app/router";
import { api } from "@/core/api";
import { PlannerWidget } from "./PlannerWidget";
import { TodoPage } from "./TodoPage";
import { TodoWidget } from "./TodoWidget";
import { WeeklyPlannerPage } from "./WeeklyPlannerPage";

registerModule({
  id: "todo", title: "Todo",
  routes: [{ path: "/todos", element: TodoPage }, { path: "/planner", element: WeeklyPlannerPage }],
  todayWidgets: [TodoWidget, PlannerWidget],
  commands: [
    { id: "todo.open", label: "Todo'ya git", run: () => navigate("/todos") },
    { id: "planner.open", label: "Weekly Planner'i ac", run: () => navigate("/planner") },
    { id: "todo.quick", label: "Hizli gorev ekle", run: async () => {
      const title = prompt("Gorev")?.trim(); if (!title) return;
      await api.post("/todos", { title }); navigate("/todos");
    } },
  ],
});
